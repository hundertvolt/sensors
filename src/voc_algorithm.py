# SPDX-FileCopyrightText: Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com), author yangfeng
# SPDX-License-Identifier: MIT
# Ported from DFRobot's Python translation, not Sensirion's C - provenance: THIRD_PARTY_LICENSES.md.

"""Sensirion's VOC Index algorithm (fixed-point Q16.16), a literal port of DFRobot's Python translation of the archived
Sensirion/embedded-sgp C source; its successor is Sensirion/gas-index-algorithm (name map and differences:
SPECIFICATION.md Part F.4). Every method returns a value; the state codec answers False for what struct refuses.
"""

import struct

from micropython import const

_VOCALGORITHM_SAMPLING_INTERVAL = const(1)
_VOCALGORITHM_INITIAL_BLACKOUT = const(45)
_VOCALGORITHM_VOC_INDEX_GAIN = const(230)
_VOCALGORITHM_SRAW_STD_INITIAL = const(50)
_VOCALGORITHM_SRAW_STD_BONUS = const(220)
_VOCALGORITHM_TAU_MEAN_VARIANCE_HOURS = const(12)
_VOCALGORITHM_TAU_INITIAL_MEAN = const(20)
_VOCALGORITHM_INITI_DURATION_MEAN = const(2700)
_VOCALGORITHM_INITI_TRANSITION_MEAN = const(0.01)
_VOCALGORITHM_TAU_INITIAL_VARIANCE = const(2500)
_VOCALGORITHM_INITI_DURATION_VARIANCE = const(5220)
_VOCALGORITHM_INITI_TRANSITION_VARIANCE = const(0.01)
_VOCALGORITHM_GATING_THRESHOLD = const(340)
_VOCALGORITHM_GATING_THRESHOLD_INITIAL = const(510)
_VOCALGORITHM_GATING_THRESHOLD_TRANSITION = const(0.09)
_VOCALGORITHM_GATING_MAX_DURATION_MINUTES = const(180)
_VOCALGORITHM_GATING_MAX_RATIO = const(0.3)
_VOCALGORITHM_SIGMOID_L = const(500)
_VOCALGORITHM_SIGMOID_K = const(-0.0065)
_VOCALGORITHM_SIGMOID_X0 = const(213)
_VOCALGORITHM_VOC_INDEX_OFFSET_DEFAULT = const(100)
_VOCALGORITHM_LP_TAU_FAST = const(20)
_VOCALGORITHM_LP_TAU_SLOW = const(500)
_VOCALGORITHM_LP_ALPHA = const(-0.2)
_VOCALGORITHM_PERSISTENCE_UPTIME_GAMMA = const(10800)
_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING = const(64)
_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = const(32767)
_FIX16_MAXIMUM = const(0x7FFFFFFF)
# INT32_MIN, as the C fix16_t reads 0x80000000
_FIX16_MINIMUM = const(-0x80000000)
_FIX16_OVERFLOW = const(-0x80000000)
_FIX16_ONE = const(0x00010000)
_FIX16_FRACTION_MAX = const(65535)  # 16-bit remainder check in _fix16_sqrt()

# vocalgorithm_process()'s own sraw guard/clamp bounds - bare literals in the C reference, named here
_SRAW_VALID_MAX = const(65000)
_SRAW_CLAMP_MIN = const(20001)
_SRAW_CLAMP_MAX = const(52767)

_VOC_PARAMS_MEMSIZE = const(256)  # 32 * 8 bytes


def _int32(value: int) -> int:
    # C's fix16_t is int32: every helper takes and returns it wrapped (Sensirion embedded-sgp's C source).
    if _FIX16_MINIMUM <= value <= _FIX16_MAXIMUM:
        return value
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


class DFRobot_vocalgorithmParams:
    # Field names/order trace the C reference 1:1 (see module docstring); __init__ and reset()
    # deliberately share one body (reset() is the source of truth, __init__ just calls it).
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.mvoc_index_offset = 0
        self.mtau_mean_variance_hours = 0
        self.mgating_max_duration_minutes = 0
        self.msraw_std_initial = 0
        self.muptime = 0
        self.msraw = 0
        self.mvoc_index = 0
        self.m_mean_variance_estimator_gating_max_duration_minutes = 0
        self.m_mean_variance_estimator_initialized = 0
        self.m_mean_variance_estimator_mean = 0
        self.m_mean_variance_estimator_sraw_offset = 0
        self.m_mean_variance_estimator_std = 0
        self.m_mean_variance_estimator_gamma = 0
        self.m_mean_variance_estimator_gamma_initial_mean = 0
        self.m_mean_variance_estimator_gamma_initial_variance = 0
        self.m_mean_variance_estimator_gamma_mean = 0
        self.m_mean_variance_estimator__gamma_variance = 0
        self.m_mean_variance_estimator_uptime_gamma = 0
        self.m_mean_variance_estimator_uptime_gating = 0
        self.m_mean_variance_estimator_gating_duration_minutes = 0
        self.m_mean_variance_estimator_sigmoid_l = 0
        self.m_mean_variance_estimator_sigmoid_k = 0
        self.m_mean_variance_estimator_sigmoid_x0 = 0
        self.m_mox_model_sraw_std = 0
        self.m_mox_model_sraw_mean = 0
        self.m_sigmoid_scaled_offset = 0
        self.m_adaptive_lowpass_a1 = 0
        self.m_adaptive_lowpass_a2 = 0
        self.m_adaptive_lowpass_initialized = 0
        self.m_adaptive_lowpass_x1 = 0
        self.m_adaptive_lowpass_x2 = 0
        self.m_adaptive_lowpass_x3 = 0

    def pack_into(self, buf: bytearray | memoryview, offset: int = 0) -> bool:
        # Every field is frozen, the uptime_gamma/uptime_gating learning counters included (owner, 2026-07-21)
        try:
            struct.pack_into(
                "32q",
                buf,
                offset,
                self.mvoc_index_offset,
                self.mtau_mean_variance_hours,
                self.mgating_max_duration_minutes,
                self.msraw_std_initial,
                self.muptime,
                self.msraw,
                self.mvoc_index,
                self.m_mean_variance_estimator_gating_max_duration_minutes,
                self.m_mean_variance_estimator_initialized,
                self.m_mean_variance_estimator_mean,
                self.m_mean_variance_estimator_sraw_offset,
                self.m_mean_variance_estimator_std,
                self.m_mean_variance_estimator_gamma,
                self.m_mean_variance_estimator_gamma_initial_mean,
                self.m_mean_variance_estimator_gamma_initial_variance,
                self.m_mean_variance_estimator_gamma_mean,
                self.m_mean_variance_estimator__gamma_variance,
                self.m_mean_variance_estimator_uptime_gamma,
                self.m_mean_variance_estimator_uptime_gating,
                self.m_mean_variance_estimator_gating_duration_minutes,
                self.m_mean_variance_estimator_sigmoid_l,
                self.m_mean_variance_estimator_sigmoid_k,
                self.m_mean_variance_estimator_sigmoid_x0,
                self.m_mox_model_sraw_std,
                self.m_mox_model_sraw_mean,
                self.m_sigmoid_scaled_offset,
                self.m_adaptive_lowpass_a1,
                self.m_adaptive_lowpass_a2,
                self.m_adaptive_lowpass_initialized,
                self.m_adaptive_lowpass_x1,
                self.m_adaptive_lowpass_x2,
                self.m_adaptive_lowpass_x3,
            )
        except (OverflowError, TypeError, ValueError):  # what struct raises for a bad buffer or offset (py/modstruct.c)
            return False
        else:
            return True

    def unpack_from(self, buf: bytes | bytearray | memoryview, offset: int = 0) -> bool:
        try:
            values = struct.unpack_from("32q", buf, offset)
        except (OverflowError, ValueError):  # a short buffer or an offset past it; a MemoryError propagates, its text logged by the caller
            return False
        (
            self.mvoc_index_offset,
            self.mtau_mean_variance_hours,
            self.mgating_max_duration_minutes,
            self.msraw_std_initial,
            self.muptime,
            self.msraw,
            self.mvoc_index,
            self.m_mean_variance_estimator_gating_max_duration_minutes,
            self.m_mean_variance_estimator_initialized,
            self.m_mean_variance_estimator_mean,
            self.m_mean_variance_estimator_sraw_offset,
            self.m_mean_variance_estimator_std,
            self.m_mean_variance_estimator_gamma,
            self.m_mean_variance_estimator_gamma_initial_mean,
            self.m_mean_variance_estimator_gamma_initial_variance,
            self.m_mean_variance_estimator_gamma_mean,
            self.m_mean_variance_estimator__gamma_variance,
            self.m_mean_variance_estimator_uptime_gamma,
            self.m_mean_variance_estimator_uptime_gating,
            self.m_mean_variance_estimator_gating_duration_minutes,
            self.m_mean_variance_estimator_sigmoid_l,
            self.m_mean_variance_estimator_sigmoid_k,
            self.m_mean_variance_estimator_sigmoid_x0,
            self.m_mox_model_sraw_std,
            self.m_mox_model_sraw_mean,
            self.m_sigmoid_scaled_offset,
            self.m_adaptive_lowpass_a1,
            self.m_adaptive_lowpass_a2,
            self.m_adaptive_lowpass_initialized,
            self.m_adaptive_lowpass_x1,
            self.m_adaptive_lowpass_x2,
            self.m_adaptive_lowpass_x3,
        ) = values
        return True


class VOCAlgorithm:
    def __init__(self) -> None:
        self.params = DFRobot_vocalgorithmParams()
        # Precomputed once for _fix16_exp() - these never change between calls, and it's called
        # several times per vocalgorithm_process() invocation (see SPECIFICATION.md C.11 point 6).
        self._exp_pos_values = (
            178145,  # F16(2.7182818)
            74262,  # F16(1.1331485)
            66568,  # F16(1.0157477)
            65664,  # F16(1.0019550)
        )
        self._exp_neg_values = (
            24109,  # F16(0.3678794)
            57835,  # F16(0.8824969)
            64520,  # F16(0.9844964)
            65408,  # F16(0.9980488)
        )

    def _fix16_from_int(self, a: float) -> int:
        return int(a * _FIX16_ONE)

    def _fix16_cast_to_int(self, a: float) -> int:
        return int(a) >> 16

    def _fix16_mul(self, inarg0: float, inarg1: float) -> int:
        # libfixmath's fix16_mul() as one exact int product: its 0x8000/0x7FFF rounding bias and fix16_overflow past
        # 48 bits, bit for bit with the reference's 16x16 partial products (tests/test_voc_algorithm.py's vectors).
        product = _int32(int(inarg0)) * _int32(int(inarg1))
        if not -0x800000000000 <= product <= 0x7FFFFFFFFFFF:
            return _FIX16_OVERFLOW
        return (product + (0x7FFF if product < 0 else 0x8000)) >> 16

    def _fix16_div(self, a: float, b: float) -> int:
        # libfixmath's fix16_div() as one exact int quotient, rounded to nearest as its bit-serial loop's final step;
        # fix16_minimum for b == 0 and fix16_overflow past the range, as the reference.
        a = _int32(int(a))
        b = _int32(int(b))
        if b == 0:
            return _FIX16_MINIMUM
        remainder = -a if a < 0 else a
        divider = -b if b < 0 else b
        if (divider << 15) < remainder:
            return _FIX16_OVERFLOW
        quotient = ((remainder << 17) // divider + 1) >> 1
        if (a < 0) != (b < 0):
            if quotient == 0x80000000:
                return _FIX16_OVERFLOW
            quotient = -quotient
        return _int32(quotient)

    def _fix16_sqrt(self, x: float) -> int:
        x = _int32(int(x))
        num = x & 0xFFFFFFFF
        result = 0
        bit = 1 << 30
        while bit > num:
            bit >>= 2
        for n in range(2):
            while bit:
                if num >= result + bit:
                    num = num - (result + bit) & 0xFFFFFFFF
                    result = (result >> 1) + bit
                else:
                    result = result >> 1
                bit >>= 2
            if n == 0:
                if num > _FIX16_FRACTION_MAX:
                    num = (num - result) & 0xFFFFFFFF
                    num = ((num << 16) - 0x8000) & 0xFFFFFFFF
                    result = ((result << 16) + 0x8000) & 0xFFFFFFFF
                else:
                    num = (num << 16) & 0xFFFFFFFF
                    result = (result << 16) & 0xFFFFFFFF
                bit = 1 << 14
        if num > result:
            result += 1
        return result

    def _fix16_exp(self, x: float) -> int:
        x = _int32(int(x))
        if x >= 681391:  # F16(10.3972)
            return _FIX16_MAXIMUM
        if x <= -772243:  # F16(-11.7835)
            return 0
        if x < 0:
            x = -x
            exp_values = self._exp_neg_values
        else:
            exp_values = self._exp_pos_values
        res = _FIX16_ONE
        arg = _FIX16_ONE
        for i in range(4):
            while x >= arg:
                res = self._fix16_mul(res, exp_values[i])
                x -= arg
            arg >>= 3
        return res

    def _vocalgorithm__init_instances(self) -> None:
        self._vocalgorithm__mean_variance_estimator__init()
        self._vocalgorithm__mean_variance_estimator__set_parameters(
            3276800,  # F16(SRAW_STD_INITIAL)
            self.params.mtau_mean_variance_hours,
            self.params.mgating_max_duration_minutes,
        )
        self._vocalgorithm__mox_model__init()
        self._vocalgorithm__mox_model__set_parameters(
            self._vocalgorithm__mean_variance_estimator__get_std(),
            self._vocalgorithm__mean_variance_estimator__get_mean(),
        )
        self._vocalgorithm__sigmoid_scaled__init()
        self._vocalgorithm__sigmoid_scaled__set_parameters(self.params.mvoc_index_offset)
        self._vocalgorithm__adaptive_lowpass__init()
        self._vocalgorithm__adaptive_lowpass__set_parameters()

    def _vocalgorithm_get_states(self) -> tuple[int, int]:
        state0 = self._vocalgorithm__mean_variance_estimator__get_mean()
        state1 = self._vocalgorithm__mean_variance_estimator__get_std()
        return state0, state1

    def _vocalgorithm_set_states(self, state0: int, state1: int) -> None:
        self._vocalgorithm__mean_variance_estimator__set_states(
            state0,
            state1,
            707788800,  # F16(PERSISTENCE_UPTIME_GAMMA)
        )
        self.params.msraw = state0

    def _vocalgorithm_set_tuning_parameters(
        self,
        voc_index_offset: float,
        learning_time_hours: float,
        gating_max_duration_minutes: float,
        std_initial: float,
    ) -> None:
        self.params.mvoc_index_offset = self._fix16_from_int(voc_index_offset)
        self.params.mtau_mean_variance_hours = self._fix16_from_int(learning_time_hours)
        self.params.mgating_max_duration_minutes = self._fix16_from_int(gating_max_duration_minutes)
        self.params.msraw_std_initial = self._fix16_from_int(std_initial)
        self._vocalgorithm__init_instances()

    def _vocalgorithm__mean_variance_estimator__init(self) -> None:
        self._vocalgorithm__mean_variance_estimator__set_parameters(0, 0, 0)
        self._vocalgorithm__mean_variance_estimator___init_instances()

    def _vocalgorithm__mean_variance_estimator___init_instances(self) -> None:
        self._vocalgorithm__mean_variance_estimator___sigmoid__init()

    def _vocalgorithm__mean_variance_estimator__set_parameters(
        self,
        std_initial: int,
        tau_mean_variance_hours: int,
        gating_max_duration_minutes: int,
    ) -> None:
        self.params.m_mean_variance_estimator_gating_max_duration_minutes = gating_max_duration_minutes
        self.params.m_mean_variance_estimator_initialized = 0
        self.params.m_mean_variance_estimator_mean = 0
        self.params.m_mean_variance_estimator_sraw_offset = 0
        self.params.m_mean_variance_estimator_std = std_initial
        self.params.m_mean_variance_estimator_gamma = self._fix16_div(
            1165,  # F16(MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * (SAMPLING_INTERVAL / 3600.0))
            (tau_mean_variance_hours + 18),  # F16(SAMPLING_INTERVAL / 3600.0)
        )
        self.params.m_mean_variance_estimator_gamma_initial_mean = 199729  # F16((MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * SAMPLING_INTERVAL) / (TAU_INITIAL_MEAN + SAMPLING_INTERVAL))
        self.params.m_mean_variance_estimator_gamma_initial_variance = 1677  # F16((MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING * SAMPLING_INTERVAL) / (TAU_INITIAL_VARIANCE + SAMPLING_INTERVAL))
        self.params.m_mean_variance_estimator_gamma_mean = 0
        self.params.m_mean_variance_estimator__gamma_variance = 0
        self.params.m_mean_variance_estimator_uptime_gamma = 0
        self.params.m_mean_variance_estimator_uptime_gating = 0
        self.params.m_mean_variance_estimator_gating_duration_minutes = 0

    def _vocalgorithm__mean_variance_estimator__set_states(self, mean: int, std: int, uptime_gamma: int) -> None:
        self.params.m_mean_variance_estimator_mean = mean
        self.params.m_mean_variance_estimator_std = std
        self.params.m_mean_variance_estimator_uptime_gamma = uptime_gamma
        self.params.m_mean_variance_estimator_initialized = True

    def _vocalgorithm__mean_variance_estimator__get_std(self) -> int:
        return self.params.m_mean_variance_estimator_std

    def _vocalgorithm__mean_variance_estimator__get_mean(self) -> int:
        return self.params.m_mean_variance_estimator_mean + self.params.m_mean_variance_estimator_sraw_offset

    def _vocalgorithm__mean_variance_estimator___calculate_gamma(self, voc_index_from_prior: int) -> None:
        uptime_limit = 2147352576  # F16(MEAN_VARIANCE_ESTIMATOR__FIX16_MAX - SAMPLING_INTERVAL)
        if self.params.m_mean_variance_estimator_uptime_gamma < uptime_limit:
            self.params.m_mean_variance_estimator_uptime_gamma = (
                self.params.m_mean_variance_estimator_uptime_gamma + 65536  # F16(SAMPLING_INTERVAL)
            )

        if self.params.m_mean_variance_estimator_uptime_gating < uptime_limit:
            self.params.m_mean_variance_estimator_uptime_gating = (
                self.params.m_mean_variance_estimator_uptime_gating + 65536  # F16(SAMPLING_INTERVAL)
            )

        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            65536,
            176947200,  # F16(INITI_DURATION_MEAN)
            655,  # F16(INITI_TRANSITION_MEAN)
        )
        sigmoid_gamma_mean = self._vocalgorithm__mean_variance_estimator___sigmoid__process(
            self.params.m_mean_variance_estimator_uptime_gamma,
        )
        gamma_mean = self.params.m_mean_variance_estimator_gamma + (
            self._fix16_mul(
                (
                    self.params.m_mean_variance_estimator_gamma_initial_mean
                    - self.params.m_mean_variance_estimator_gamma
                ),
                sigmoid_gamma_mean,
            )
        )
        gating_threshold_mean = 22282240 + (  # F16(GATING_THRESHOLD)
            self._fix16_mul(
                11141120,  # F16(GATING_THRESHOLD_INITIAL - GATING_THRESHOLD)
                self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                    self.params.m_mean_variance_estimator_uptime_gating,
                ),
            )
        )
        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            65536,
            gating_threshold_mean,
            5898,  # F16(GATING_THRESHOLD_TRANSITION)
        )

        sigmoid_gating_mean = self._vocalgorithm__mean_variance_estimator___sigmoid__process(voc_index_from_prior)
        self.params.m_mean_variance_estimator_gamma_mean = self._fix16_mul(sigmoid_gating_mean, gamma_mean)

        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            65536,
            342097920,  # F16(INITI_DURATION_VARIANCE)
            655,  # F16(INITI_TRANSITION_VARIANCE)
        )

        sigmoid_gamma_variance = self._vocalgorithm__mean_variance_estimator___sigmoid__process(
            self.params.m_mean_variance_estimator_uptime_gamma,
        )

        gamma_variance = self.params.m_mean_variance_estimator_gamma + (
            self._fix16_mul(
                (
                    self.params.m_mean_variance_estimator_gamma_initial_variance
                    - self.params.m_mean_variance_estimator_gamma
                ),
                (sigmoid_gamma_variance - sigmoid_gamma_mean),
            )
        )

        gating_threshold_variance = 22282240 + (  # F16(GATING_THRESHOLD)
            self._fix16_mul(
                11141120,  # F16(GATING_THRESHOLD_INITIAL - GATING_THRESHOLD)
                self._vocalgorithm__mean_variance_estimator___sigmoid__process(
                    self.params.m_mean_variance_estimator_uptime_gating,
                ),
            )
        )

        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            65536,
            gating_threshold_variance,
            5898,  # F16(GATING_THRESHOLD_TRANSITION)
        )

        sigmoid_gating_variance = self._vocalgorithm__mean_variance_estimator___sigmoid__process(voc_index_from_prior)

        self.params.m_mean_variance_estimator__gamma_variance = self._fix16_mul(sigmoid_gating_variance, gamma_variance)

        self.params.m_mean_variance_estimator_gating_duration_minutes = (
            self.params.m_mean_variance_estimator_gating_duration_minutes
            + (
                self._fix16_mul(
                    1092,  # F16(SAMPLING_INTERVAL / 60.0)
                    (
                        (
                            self._fix16_mul(
                                (65536 - sigmoid_gating_mean),
                                85197,  # F16((1.0 + GATING_MAX_RATIO))
                            )
                        )
                        - 19661  # F16(GATING_MAX_RATIO)
                    ),
                )
            )
        )

        self.params.m_mean_variance_estimator_gating_duration_minutes = max(
            self.params.m_mean_variance_estimator_gating_duration_minutes, 0,
        )

        if (
            self.params.m_mean_variance_estimator_gating_duration_minutes
            > self.params.m_mean_variance_estimator_gating_max_duration_minutes
        ):
            self.params.m_mean_variance_estimator_uptime_gating = 0

    def _vocalgorithm__mean_variance_estimator__process(self, sraw: int, voc_index_from_prior: int) -> None:
        if self.params.m_mean_variance_estimator_initialized == 0:
            self.params.m_mean_variance_estimator_initialized = 1
            self.params.m_mean_variance_estimator_sraw_offset = sraw
            self.params.m_mean_variance_estimator_mean = 0
        else:
            if (self.params.m_mean_variance_estimator_mean >= 6553600) or (  # F16(100.0)
                self.params.m_mean_variance_estimator_mean <= -6553600  # F16(-100.0)
            ):
                self.params.m_mean_variance_estimator_sraw_offset = (
                    self.params.m_mean_variance_estimator_sraw_offset + self.params.m_mean_variance_estimator_mean
                )
                self.params.m_mean_variance_estimator_mean = 0

            sraw = sraw - self.params.m_mean_variance_estimator_sraw_offset
            self._vocalgorithm__mean_variance_estimator___calculate_gamma(voc_index_from_prior)
            delta_sgp = self._fix16_div(
                (sraw - self.params.m_mean_variance_estimator_mean),
                4194304,  # F16(MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING)
            )
            std = self.params.m_mean_variance_estimator_std
            c = std - delta_sgp if delta_sgp < 0 else std + delta_sgp
            additional_scaling = 65536
            if c > 94371840:  # F16(1440.0)
                additional_scaling = 262144  # F16(4.0)
            self.params.m_mean_variance_estimator_std = self._fix16_mul(
                self._fix16_sqrt(

                        self._fix16_mul(
                            additional_scaling,
                            (
                                4194304  # F16(MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING)
                                - self.params.m_mean_variance_estimator__gamma_variance
                            ),
                        ),

                ),
                self._fix16_sqrt(

                        (
                            self._fix16_mul(
                                self.params.m_mean_variance_estimator_std,
                                (
                                    self._fix16_div(
                                        self.params.m_mean_variance_estimator_std,
                                        (
                                            self._fix16_mul(
                                                4194304,  # F16(MEAN_VARIANCE_ESTIMATOR__GAMMA_SCALING)
                                                additional_scaling,
                                            )
                                        ),
                                    )
                                ),
                            )
                        )
                        + (
                            self._fix16_mul(
                                (
                                    self._fix16_div(
                                        (
                                            self._fix16_mul(
                                                self.params.m_mean_variance_estimator__gamma_variance,
                                                delta_sgp,
                                            )
                                        ),
                                        additional_scaling,
                                    )
                                ),
                                delta_sgp,
                            )
                        ),

                ),
            )
            self.params.m_mean_variance_estimator_mean = self.params.m_mean_variance_estimator_mean + (
                self._fix16_mul(self.params.m_mean_variance_estimator_gamma_mean, delta_sgp)
            )

    def _vocalgorithm__mean_variance_estimator___sigmoid__init(self) -> None:
        self._vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(
            0, 0, 0,
        )

    def _vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self, L: int, X0: int, K: int) -> None:
        self.params.m_mean_variance_estimator_sigmoid_l = L
        self.params.m_mean_variance_estimator_sigmoid_k = K
        self.params.m_mean_variance_estimator_sigmoid_x0 = X0

    def _vocalgorithm__mean_variance_estimator___sigmoid__process(self, sample: int) -> int:
        x = self._fix16_mul(
            self.params.m_mean_variance_estimator_sigmoid_k,
            (sample - self.params.m_mean_variance_estimator_sigmoid_x0),
        )
        if x < -3276800:  # F16(-50.0)
            return self.params.m_mean_variance_estimator_sigmoid_l
        if x > 3276800:  # F16(50.0)
            return 0
        return self._fix16_div(
            self.params.m_mean_variance_estimator_sigmoid_l,
            (65536 + self._fix16_exp(x)),
        )

    def _vocalgorithm__mox_model__init(self) -> None:
        self._vocalgorithm__mox_model__set_parameters(65536, 0)

    def _vocalgorithm__mox_model__set_parameters(self, SRAW_STD: int, SRAW_MEAN: int) -> None:
        self.params.m_mox_model_sraw_std = SRAW_STD
        self.params.m_mox_model_sraw_mean = SRAW_MEAN

    def _vocalgorithm__mox_model__process(self, sraw: int) -> int:
        return self._fix16_mul(
            (
                self._fix16_div(
                    (sraw - self.params.m_mox_model_sraw_mean),
                    (-(self.params.m_mox_model_sraw_std + 14417920)),  # F16(SRAW_STD_BONUS)
                )
            ),
            15073280,  # F16(VOC_INDEX_GAIN)
        )

    def _vocalgorithm__sigmoid_scaled__init(self) -> None:
        self._vocalgorithm__sigmoid_scaled__set_parameters(0)

    def _vocalgorithm__sigmoid_scaled__set_parameters(self, offset: int) -> None:
        self.params.m_sigmoid_scaled_offset = offset

    def _vocalgorithm__sigmoid_scaled__process(self, sample: int) -> int:
        x = self._fix16_mul(
            -426,  # F16(SIGMOID_K)
            (sample - 13959168),  # F16(SIGMOID_X0)
        )
        if x < -3276800:  # F16(-50.0)
            return 32768000  # F16(SIGMOID_L)
        if x > 3276800:  # F16(50.0)
            return 0
        if sample >= 0:
            shift = self._fix16_div(
                (
                    32768000  # F16(SIGMOID_L)
                    - (self._fix16_mul(327680, self.params.m_sigmoid_scaled_offset))  # F16(5.0)
                ),
                262144,  # F16(4.0)
            )
            return (
                self._fix16_div(
                    (32768000 + shift),  # F16(SIGMOID_L)
                    (65536 + self._fix16_exp(x)),
                )
            ) - shift
        return self._fix16_mul(
            (
                self._fix16_div(
                    self.params.m_sigmoid_scaled_offset,
                    6553600,  # F16(VOC_INDEX_OFFSET_DEFAULT)
                )
            ),
            (
                self._fix16_div(
                    32768000,  # F16(SIGMOID_L)
                    (65536 + self._fix16_exp(x)),
                )
            ),
        )

    def _vocalgorithm__adaptive_lowpass__init(self) -> None:
        self._vocalgorithm__adaptive_lowpass__set_parameters()

    def _vocalgorithm__adaptive_lowpass__set_parameters(self) -> None:
        self.params.m_adaptive_lowpass_a1 = 3121  # F16(SAMPLING_INTERVAL / (LP_TAU_FAST + SAMPLING_INTERVAL))
        self.params.m_adaptive_lowpass_a2 = 131  # F16(SAMPLING_INTERVAL / (LP_TAU_SLOW + SAMPLING_INTERVAL))
        self.params.m_adaptive_lowpass_initialized = 0

    def _vocalgorithm__adaptive_lowpass__process(self, sample: int) -> int:
        if self.params.m_adaptive_lowpass_initialized == 0:
            self.params.m_adaptive_lowpass_x1 = sample
            self.params.m_adaptive_lowpass_x2 = sample
            self.params.m_adaptive_lowpass_x3 = sample
            self.params.m_adaptive_lowpass_initialized = 1
        self.params.m_adaptive_lowpass_x1 = (
            self._fix16_mul(
                (65536 - self.params.m_adaptive_lowpass_a1),
                self.params.m_adaptive_lowpass_x1,
            )
        ) + (self._fix16_mul(self.params.m_adaptive_lowpass_a1, sample))

        self.params.m_adaptive_lowpass_x2 = (
            self._fix16_mul(
                (65536 - self.params.m_adaptive_lowpass_a2),
                self.params.m_adaptive_lowpass_x2,
            )
        ) + (self._fix16_mul(self.params.m_adaptive_lowpass_a2, sample))

        abs_delta = self.params.m_adaptive_lowpass_x1 - self.params.m_adaptive_lowpass_x2

        if abs_delta < 0:
            abs_delta = -abs_delta
        F1 = self._fix16_exp(self._fix16_mul(-13107, abs_delta))  # F16(LP_ALPHA)
        tau_a = (self._fix16_mul(31457280, F1)) + 1310720  # F16(LP_TAU_SLOW - LP_TAU_FAST), F16(LP_TAU_FAST)
        a3 = self._fix16_div(
            65536,  # F16(SAMPLING_INTERVAL)
            (65536 + tau_a),  # F16(SAMPLING_INTERVAL)
        )
        self.params.m_adaptive_lowpass_x3 = (
            self._fix16_mul((65536 - a3), self.params.m_adaptive_lowpass_x3)
        ) + (self._fix16_mul(a3, sample))
        return self.params.m_adaptive_lowpass_x3

    @staticmethod
    def get_params_memsize() -> int:
        return _VOC_PARAMS_MEMSIZE

    def vocalgorithm_reset(self) -> None:
        self.params.reset()
        self.vocalgorithm_init()

    def vocalgorithm_init(self) -> None:
        self.params.mvoc_index_offset = 6553600  # F16(VOC_INDEX_OFFSET_DEFAULT)
        self.params.mtau_mean_variance_hours = 786432  # F16(TAU_MEAN_VARIANCE_HOURS)
        self.params.mgating_max_duration_minutes = 11796480  # F16(GATING_MAX_DURATION_MINUTES)
        self.params.msraw_std_initial = 3276800  # F16(SRAW_STD_INITIAL)
        self.params.muptime = 0
        self.params.msraw = 0
        self.params.mvoc_index = 0
        self._vocalgorithm__init_instances()

    def vocalgorithm_process(self, sraw: int) -> int:
        if self.params.muptime <= 2949120:  # F16(INITIAL_BLACKOUT)
            self.params.muptime = self.params.muptime + 65536  # F16(SAMPLING_INTERVAL)
        else:
            if (sraw > 0) and (sraw < _SRAW_VALID_MAX):
                if sraw < _SRAW_CLAMP_MIN:
                    sraw = _SRAW_CLAMP_MIN
                elif sraw > _SRAW_CLAMP_MAX:
                    sraw = _SRAW_CLAMP_MAX
                self.params.msraw = self._fix16_from_int(sraw - 20000)
            self.params.mvoc_index = self._vocalgorithm__mox_model__process(self.params.msraw)
            self.params.mvoc_index = self._vocalgorithm__sigmoid_scaled__process(self.params.mvoc_index)
            self.params.mvoc_index = self._vocalgorithm__adaptive_lowpass__process(self.params.mvoc_index)
            self.params.mvoc_index = max(self.params.mvoc_index, 32768)  # F16(0.5)
            if self.params.msraw > 0:
                self._vocalgorithm__mean_variance_estimator__process(self.params.msraw, self.params.mvoc_index)
                self._vocalgorithm__mox_model__set_parameters(
                    self._vocalgorithm__mean_variance_estimator__get_std(),
                    self._vocalgorithm__mean_variance_estimator__get_mean(),
                )
        return self._fix16_cast_to_int(self.params.mvoc_index + 32768)  # F16(0.5)

    def vocalgorithm_proc_ser_des(
        self,
        sraw: int,
        buf: bytearray | memoryview | None = None,
        *,
        serialize: bool = False,
        deserialize: bool = False,
        offset: int = 0,
    ) -> tuple[int, bool, bool]:
        serialized = deserialized = False
        if buf is not None and deserialize:
            deserialized = self.params.unpack_from(buf, offset=offset)
        voc_index = self.vocalgorithm_process(sraw)
        if buf is not None and serialize:
            serialized = self.params.pack_into(buf, offset=offset)
        return voc_index, serialized, deserialized

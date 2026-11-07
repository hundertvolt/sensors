# The Python port on the C experiment's 0.1-day ramp: max gating duration and samples at index >= 497.
import sys
from voc_algorithm import VOCAlgorithm
days = float(sys.argv[1])
algo = VOCAlgorithm()
algo.vocalgorithm_init()
for _ in range(2 * 3600):
    algo.vocalgorithm_process(52767)
total = int(days * 86400)
maxd = 0.0
at = 0
hi = 0
for n in range(total + int(float(sys.argv[2]) * 86400)):
    s = 52767 - int((52767.0 - 20001.0) * n / total) if n < total else 20001
    idx = algo.vocalgorithm_process(s)
    d = algo.params.m_mean_variance_estimator_gating_duration_minutes / 65536.0
    if idx >= 497:
        hi += 1
    if d > maxd:
        maxd = d
        at = n
print("port ramp %.2f days: max duration %.2f min at day %.2f; samples at index>=497: %d" % (days, maxd, at / 86400.0, hi))

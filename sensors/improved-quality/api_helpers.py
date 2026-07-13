from async_manager import ConfigManager
from typing import Any, Tuple, Literal, Callable, Dict, List, Union, Coroutine
from microdot import Request


ResultValue = Union[int, float, str, bool, None]
JsonValidity = Dict[str, Literal["Invalid", "Unchanged", "Valid", "Failed"]]
ApiData = Tuple[
    bool,
    bool,
    Union[str, None],
    bool,
    JsonValidity,
    Dict[str, Union[int, float, str, bool, None]],
    ResultValue,
    List[str],
]


async def init_json_from_cfg(
    cfgmgr: ConfigManager,
    keys: List[str],
    cmd_keys: Dict[str, int | float | str | bool] | None = None,
) -> Tuple[
    ApiData | None,
    Dict[str, str | int | JsonValidity] | None,
]:
    (valid, data) = await cfgmgr.get_dict(keys)
    # TODO what if data is None (valid is obsolete)
    return await _init_json(valid, data, cmd_keys)


async def init_json_from_ext(
    valid: bool,
    ext_json: Dict[str, int | float | str | bool | None],
    cmd_keys: Dict[str, int | float | str | bool] | None = None,
) -> Tuple[
    ApiData | None,
    Dict[str, str | int | JsonValidity] | None,
]:
    return await _init_json(valid, ext_json, cmd_keys)


async def _init_json(
    valid: bool,
    data: Dict[str, int | float | str | bool | None],
    cmd_keys: Dict[str, int | float | str | bool] | None = None,
) -> Tuple[
    ApiData | None,
    Dict[str, str | int | JsonValidity] | None,
]:
    cmd = []
    if not valid:
        return None, {"res": "ERR", "code": 4, "descr": "Internal config read error"}
    if (
        cmd_keys is not None
    ):  # cmd_keys is the List of command-only keys and gets value True if changed from default
        for key in cmd_keys:
            cmd.append(key)
            data[key] = cmd_keys[key]
    res: ApiData = False, False, None, False, {}, data, None, cmd
    return res, None


def update_valid_json(
    json_in: Dict[str, int | float | str],
    json_key: str,
    dtype: Literal["str", "int", "float", "switch"],
    prev_values: ApiData,
    min_len_val: int | float | None,
    max_len_val: int | float | None,
    special_val: List[int | float | str] | None = None,
    weight_fct: Callable[[int | float], int | float] = lambda x: x,
    debug: bool = False,
) -> ApiData:
    # check and update from JSON.
    # json_in: Input JSON (Dict) object
    # json_key: Key of JSON to be checked
    # dtype: Expected type - "str", "int", "float", "switch" (expects "On" and "Off" --> bool)
    # prev_values: contains results from previous key. Contains forwarded:
    #   dst_json_value: JSON (Dict), it must also contain the key and will be updated if valid
    #   json_validity: will get key added, content = "Unchanged" in case of valid but no update, "Valid" or "Invalid"
    #   any_set: Input for ORed variable. Will be unchanged if no update, True if update
    # min_len_val: minimum length for "str", minumum value for "int" or "float", ignored if "switch"
    # max_len_val: maximum length for "str", minumum value for "int" or "float", ignored if "switch"
    # special_val: allowed special singular values which would not be allowed by min_len_val and max_len_val otherwise
    # an empty input ("") will be considered as valid value for "don't change".
    # Returns: validity (bool), updated (bool), used_key (str), any_set (bool), json_validity (Dict), updated destination (Dict), value, List of command-only keys

    if special_val is None:
        special_val = []
    (
        prev_valid,
        prev_updated,
        prev_key,
        any_set,
        json_validity,
        dst_json_value,
        prev_val,
        cmd_keys,
    ) = prev_values

    dst_val: ResultValue = None

    if json_key not in json_in:
        if debug:
            print("Key not found:", json_key)
        json_validity[json_key] = "Invalid"
        return (
            False,
            False,
            json_key,
            any_set,
            json_validity,
            dst_json_value,
            None,
            cmd_keys,
        )
    if json_in[json_key] == "":
        if debug:
            print("Key is empty, no update:", json_key)
        json_validity[json_key] = "Unchanged"
        return (
            True,
            False,
            json_key,
            any_set,
            json_validity,
            dst_json_value,
            None,
            cmd_keys,
        )

    if dtype == "str":
        try:
            strval = str(json_in[json_key])
        except ValueError:
            if debug:
                print("Key is no valid string!")
            json_validity[json_key] = "Invalid"
            return (
                False,
                False,
                json_key,
                any_set,
                json_validity,
                dst_json_value,
                None,
                cmd_keys,
            )
        if min_len_val is not None:
            if (len(strval) < min_len_val) and (strval not in special_val):
                if debug:
                    print("String type key is too short!")
                json_validity[json_key] = "Invalid"
                return (
                    False,
                    False,
                    json_key,
                    any_set,
                    json_validity,
                    dst_json_value,
                    None,
                    cmd_keys,
                )
        if max_len_val is not None:
            if (len(strval) > max_len_val) and (strval not in special_val):
                if debug:
                    print("String type key is too long!")
                json_validity[json_key] = "Invalid"
                return (
                    False,
                    False,
                    json_key,
                    any_set,
                    json_validity,
                    dst_json_value,
                    None,
                    cmd_keys,
                )
        dst_val = strval
        if debug:
            print("Key is valid string")

    elif (dtype == "int") or (dtype == "float"):
        try:
            if dtype == "int":
                numval = int(json_in[json_key])
            else:
                numval = float(json_in[json_key])
        except ValueError:
            if debug:
                print("Key is no valid int / float!")
            json_validity[json_key] = "Invalid"
            return (
                False,
                False,
                json_key,
                any_set,
                json_validity,
                dst_json_value,
                None,
                cmd_keys,
            )
        if min_len_val is not None:
            if (numval < min_len_val) and (numval not in special_val):
                if debug:
                    print("Int / Float type key is too small!")
                json_validity[json_key] = "Invalid"
                return (
                    False,
                    False,
                    json_key,
                    any_set,
                    json_validity,
                    dst_json_value,
                    None,
                    cmd_keys,
                )
        if max_len_val is not None:
            if (numval > max_len_val) and (numval not in special_val):
                if debug:
                    print("Int / Float type key is too great!")
                json_validity[json_key] = "Invalid"
                return (
                    False,
                    False,
                    json_key,
                    any_set,
                    json_validity,
                    dst_json_value,
                    None,
                    cmd_keys,
                )
        if numval not in special_val:
            numval = weight_fct(numval)
        dst_val = numval
        if debug:
            print("Key is valid int / float")

    elif dtype == "switch":
        state_val = json_in[json_key]
        if state_val == "On":
            dst_val = True
        elif state_val == "Off":
            dst_val = False
        else:
            if debug:
                print("Key is no valid switch")
            json_validity[json_key] = "Invalid"
            return (
                False,
                False,
                json_key,
                any_set,
                json_validity,
                dst_json_value,
                None,
                cmd_keys,
            )
        if debug:
            print("Key is valid switch")

    else:  # no valid dtype value
        if debug:  # type: ignore[unreachable]
            print("Invalid data type specified!")
        json_validity[json_key] = "Invalid"
        return (
            False,
            False,
            json_key,
            any_set,
            json_validity,
            dst_json_value,
            None,
            cmd_keys,
        )

    if json_key in dst_json_value and dst_val is not None:
        if dst_val == dst_json_value[json_key]:
            if debug:
                print("Valid and identical to old JSON value.")
            json_validity[json_key] = "Unchanged"
            return (
                True,
                False,
                json_key,
                any_set,
                json_validity,
                dst_json_value,
                dst_val,
                cmd_keys,
            )
        if debug:
            print("Valid and different from old JSON value.")
        dst_json_value[json_key] = dst_val
        json_validity[json_key] = "Valid"
        if json_key in cmd_keys:
            any_set_value = any_set  # if command key only, don't change flash save trigger
        else:
            any_set_value = True  # if storage key, trigger flash save
        return (
            True,
            True,
            json_key,
            any_set_value,
            json_validity,
            dst_json_value,
            dst_val,
            cmd_keys,
        )
    if debug:
        print("Not contained in old JSON.")
    json_validity[json_key] = "Invalid"
    return (
        False,
        False,
        json_key,
        any_set,
        json_validity,
        dst_json_value,
        None,
        cmd_keys,
    )


def to_switch(val: bool) -> Literal["On", "Off"]:
    return "On" if val else "Off"


def cmd_pre_check(
    request: Request, keys: List[str]
) -> Tuple[Dict[str, int | float | str] | None, Dict[str, str | int | JsonValidity] | None]:
    # convert request to JSON and check general validity (JsonValidity included in return for compatibility)
    try:
        req_json = request.json
    except:
        req_json = None
    if req_json is None:
        return None, {"res": "ERR", "code": 1, "descr": "Invalid JSON Request"}
    if "cmd" not in req_json:
        return None, {"res": "ERR", "code": 2, "descr": "Command specifier missing"}
    if req_json["cmd"] not in keys:
        return None, {"res": "ERR", "code": 3, "descr": "Invalid command"}
    return req_json, None


def generic_error_return() -> Dict[str, str | int | JsonValidity]:
    return {"res": "ERR", "code": 100, "descr": "Generic command error"}


async def cmd_post_check(
    prev_values: ApiData,
    cfgmgr: ConfigManager | None,
    post_fct: Callable[[], None] | None = None,
    post_asy_fct: Callable[[], Coroutine[Any, Any, None]] | None = None,
    special_err: Literal["invalidLED", "busyLED", "pauseLED", "sysCmd"] | None = None,
    ok_descr: str = "Command exectuted",
    debug: bool = False,
) -> Dict[str, str | int | JsonValidity]:
    # take result from update_valid_json and save it to system configuration
    (
        prev_valid,
        prev_updated,
        prev_key,
        any_set,
        json_validity,
        dst_json_value,
        value,
        cmd_keys,
    ) = prev_values
    if special_err is None:
        if any_set:
            if cfgmgr is None:
                if debug:
                    print("Using new values...")
                data_written = True
            else:
                if debug:
                    print("Saving new configuration...")
                for key in cmd_keys:
                    if debug:
                        print("Ignoring command key", key)
                    dst_json_value.pop(key, None)  # ignore for saving, but keep validity result
                data_written = await cfgmgr.write_config(dst_json_value)
            if not data_written:
                return {
                    "res": "ERR",
                    "code": 5,
                    "descr": "Internal config write error",
                    "result": {},
                }
            if post_fct is not None:
                post_fct()
            if post_asy_fct is not None:
                await post_asy_fct()
        else:
            if debug:
                print("Configuration unchanged, not saving any values.")
        return {"res": "OK", "code": 0, "descr": ok_descr, "result": json_validity}

    # predefined and special errors:
    # 0: Success, no error
    # 1: Invalid JSON Request
    # 2: Command specifier missing
    # 3: Invalid command
    # 4: Internal config read error
    # 5: Internal config write error
    #
    # *** Special values ***
    # 6: Unknown error
    # 7: Incomplete or invalid LED command
    # 8: LED is busy
    # 9: Invalid Auto LED Pause time
    # 10: Invalid or unknown system command

    if special_err == "invalidLED":
        return {
            "res": "ERR",
            "code": 7,
            "descr": "Incomplete or invalid LED command",
            "result": json_validity,
        }
    elif special_err == "busyLED":
        return {
            "res": "ERR",
            "code": 8,
            "descr": "LED is busy",
            "result": json_validity,
        }
    elif special_err == "pauseLED":
        return {
            "res": "ERR",
            "code": 9,
            "descr": "Invalid Auto LED Pause time",
            "result": json_validity,
        }
    elif special_err == "sysCmd":
        return {
            "res": "ERR",
            "code": 10,
            "descr": "Invalid or unknown system command",
            "result": json_validity,
        }
    else:
        return {  # type: ignore[unreachable]
            "res": "ERR",
            "code": 6,
            "descr": "Unknown error",
            "result": json_validity,
        }


async def set_sensor_value(
    prev_values: ApiData,
    setter: Callable[[ResultValue], Coroutine[Any, Any, None]],
    cfgmgr: ConfigManager,
    getter: Callable[[], Coroutine[Any, Any, ResultValue]] | None = None,
    default: ResultValue = 0,
    force: bool = False,
    debug: bool = False,
) -> ApiData:
    # take result from update_valid_json and save it to sensor with the setter function.
    # for volatile sensor memories, return values to cmd_post_check to be saved to system config.
    # in case of sensor update errors, try to load values from sensor to keep them
    # in case of load error, try to load from system config. If this also fails, take default value.
    # force updates the value in case of a valid, non-empty value even if it's unchanged.
    (
        prev_valid,
        prev_updated,
        prev_key,
        any_set,
        json_validity,
        dst_json_value,
        value,
        cmd_keys,
    ) = prev_values
    if prev_valid and prev_key is not None and (prev_updated or (force and (value is not None))):
        try:
            await setter(value)
            if debug:
                print(prev_key + " set to " + str(value))
            if force and (value is not None):
                json_validity[prev_key] = "Valid"
            success = True
        except:
            json_validity[prev_key] = "Failed"
            if debug:
                print(prev_key + " setting failed!")
            success = False
        if (not success) and (
            prev_key not in cmd_keys
        ):  # reuse "success" as guaranteed to be False below. Only if not command-only key.
            if getter is not None:
                try:
                    if debug:
                        print("Loading current value from sensor.")
                    value = await getter()
                    if value is not None:
                        success = True
                except:
                    if debug:
                        print("Loading value from sensor failed.")
                    success = False
            if not success:
                if debug:
                    print("Loading previous setting.")
                json_val = await cfgmgr.get_dict([prev_key])
                if json_val is not None:
                    value = json_val[prev_key]
                else:
                    if debug:
                        print("Loading previous setting failed, using default value")
                    value = default
            dst_json_value[prev_key] = value
    return (
        prev_valid,
        prev_updated,
        prev_key,
        any_set,
        json_validity,
        dst_json_value,
        value,
        cmd_keys,
    )


def get_valid_values(
    prev_values: ApiData,
    keys: List[str],
) -> Tuple[Dict[str, int | float | str | bool], bool]:
    (
        prev_valid,
        prev_updated,
        prev_key,
        any_set,
        json_validity,
        dst_json_value,
        value,
        cmd_keys,
    ) = prev_values
    ret = {}
    for key in keys:
        if key in dst_json_value:
            if key not in json_validity:
                return {}, False
            if json_validity[key] not in ["Valid", "Unchanged"]:
                return {}, False
            value = dst_json_value[key]
            if value is None:
                return {}, False
            ret[key] = value
        else:
            return {}, False
    return ret, True


def time_to_dict(gmt_raw: Tuple[int] | None) -> Dict[str, int | float | str | None]:
    timedict: Dict[str, int | float | str | None] = {
        "Year": None,
        "Month": None,
        "Day": None,
        "Hour": None,
        "Min": None,
        "Sec": None,
    }
    if gmt_raw is None:
        return timedict

    gmt: Tuple[int, int, int, int, int, int, int, int, int] | None = (
        gmt_raw if len(gmt_raw) == 9 else None
    )

    if gmt is not None:
        timedict["Year"] = gmt[0]
        timedict["Month"] = gmt[1]
        timedict["Day"] = gmt[2]
        timedict["Hour"] = gmt[3]
        timedict["Min"] = gmt[4]
        timedict["Sec"] = gmt[5]
    return timedict

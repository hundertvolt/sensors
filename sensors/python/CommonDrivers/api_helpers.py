import asyncio

async def init_json_from_cfg(cfg, keys, ext_json=None, cmd_keys=None):
    if ext_json is None:
        (valid, data) = await cfg.get_json(keys)
    else:
        (valid, data) = ext_json
    res = None
    err = None
    cmd = []
    if not valid:
        err = {"res": "ERR", "code": 4, "descr": "Internal config read error"}
    else:
        if cmd_keys is not None: # cmd_keys is the list of command-only keys and gets value True if changed from default
            for key in cmd_keys:
                cmd.append(key)
                data[key] = cmd_keys[key]
        res = False, False, None, False, {}, data, None, cmd
    return res, err

def update_valid_json(json_in, json_key, dtype, prev_values, min_len_val, max_len_val, special_val=[], weight_fct=lambda x : x, debug=False):
    # check and update from JSON.
    # json_in: Input JSON (dict) object
    # json_key: Key of JSON to be checked
    # dtype: Expected type - "str", "int", "float", "switch" (expects "On" and "Off" --> bool)
    # prev_values: contains results from previous key. Initializes new variables if None. Contains forwarded:
    #   dst_json_value: JSON (dict), it must also contain the key and will be updated if valid
    #   json_validity: will get key added, content = "Unchanged" in case of valid but no update, "Valid" or "Invalid"
    #   any_set: Input for ORed variable. Will be unchanged if no update, True if update
    # min_len_val: minimum length for "str", minumum value for "int" or "float", ignored if "switch"
    # max_len_val: maximum length for "str", minumum value for "int" or "float", ignored if "switch"
    # special_val: allowed special singular values which would not be allowed by min_len_val and max_len_val otherwise
    # an empty input ("") will be considered as valid value for "don't change".
    # Returns: validity (bool), updated (bool), used_key (str), any_set (bool), json_validity (dict), updated destination (dict), value, list of command-only keys

    prev_valid, prev_updated, prev_key, any_set, json_validity, dst_json_value, prev_val, cmd_keys = prev_values

    if not json_key in json_in:
        if debug: print("Key not found:", json_key)
        json_validity[json_key] = "Invalid"
        return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
    if json_in[json_key] == "":
        if debug: print("Key is empty, no update:", json_key)
        json_validity[json_key] = "Unchanged"
        return True, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys

    if dtype == "str":
        try:
            val = str(json_in[json_key])
        except ValueError:
            if debug: print("Key is no valid string!")
            json_validity[json_key] = "Invalid"
            return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
        if min_len_val is not None:
            if (len(val) < min_len_val) and not (val in special_val):
                if debug: print("String type key is too short!")
                json_validity[json_key] = "Invalid"
                return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
        if max_len_val is not None:
            if (len(val) > max_len_val) and not (val in special_val):
                if debug: print("String type key is too long!")
                json_validity[json_key] = "Invalid"
                return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
        if debug: print("Key is valid string")

    if (dtype == "int") or (dtype == "float"):
        try:
            if (dtype == "int"):
                val = int(json_in[json_key])
            else:
                val = float(json_in[json_key])
        except ValueError:
            if debug: print("Key is no valid int / float!")
            json_validity[json_key] = "Invalid"
            return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
        if min_len_val is not None:
            if (val < min_len_val) and not (val in special_val):
                if debug: print("Int / Float type key is too small!")
                json_validity[json_key] = "Invalid"
                return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
        if max_len_val is not None:
            if (val > max_len_val) and not (val in special_val):
                if debug: print("Int / Float type key is too great!")
                json_validity[json_key] = "Invalid"
                return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
        if not (val in special_val):
            val = weight_fct(val)
        if debug: print("Key is valid int / float")

    if dtype == "switch":
        state_val = json_in[json_key]
        if state_val == "On":
            val = True
        elif state_val == "Off":
            val = False
        else:
            if debug: print("Key is no valid switch")
            json_validity[json_key] = "Invalid"
            return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys
        if debug: print("Key is valid switch")

    if json_key in dst_json_value:
        if val == dst_json_value[json_key]:
            if debug: print("Valid and identical to old JSON value.")
            json_validity[json_key] = "Unchanged"
            return True, False, json_key, any_set, json_validity, dst_json_value, val, cmd_keys
        if debug: print("Valid and different from old JSON value.")
        dst_json_value[json_key] = val
        json_validity[json_key] = "Valid"
        if json_key in cmd_keys:
            any_set_value = any_set  # if command key only, don't change flash save trigger
        else:
            any_set_value = True  # if storage key, trigger flash save
        return True, True, json_key, any_set_value, json_validity, dst_json_value, val, cmd_keys
    if debug: print("Not contained in old JSON.")
    json_validity[json_key] = "Invalid"
    return False, False, json_key, any_set, json_validity, dst_json_value, None, cmd_keys

def toSwitch(val):
    return "On" if val else "Off"

def cmd_pre_check(request, keys):
    # convert request to JSON and check general validity
    try:
        req_json = request.json
    except:
        req_json = None
    if req_json is None:
        return None, {"res": "ERR", "code": 1, "descr": "Invalid JSON Request"}
    if not "cmd" in req_json:
        return None, {"res": "ERR", "code": 2, "descr": "Command specifier missing"}
    if not req_json["cmd"] in keys:
        return None, {"res": "ERR", "code": 3, "descr": "Invalid command"}
    return req_json, None

async def cmd_post_check(prev_values, cfg, post_fct=None, post_asy_fct=None, specialErr=None, okDescr="Command exectuted", debug=False):
    # take result from update_valid_json and save it to system configuration
    prev_valid, prev_updated, prev_key, any_set, json_validity, dst_json_value, value, cmd_keys = prev_values
    if specialErr is None:
        if any_set:
            if cfg is None:
                if debug: print("Using new values...")
                data_written = True
            else:
                if debug: print("Saving new configuration...")
                for key in cmd_keys:
                    if debug: print("Ignoring command key", key)
                    dst_json_value.pop(key, None)  # ignore for saving, but keep validity result
                data_written = await cfg.write_config(dst_json_value)
            if not data_written:
                return {"res": "ERR", "code": 5, "descr": "Internal config write error"}
            if post_fct is not None:
                post_fct()
            if post_asy_fct is not None:
                await post_asy_fct()
        else:
            if debug: print("Configuration unchanged, not saving any values.")
        return {"res": "OK", "code": 0, "descr": okDescr, "result": json_validity}

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

    if specialErr == "invalidLED":
        return {"res": "ERR", "code": 7, "descr": "Incomplete or invalid LED command", "result": json_validity}
    if specialErr == "busyLED":
        return {"res": "ERR", "code": 8, "descr": "LED is busy", "result": json_validity}
    if specialErr == "pauseLED":
        return {"res": "ERR", "code": 9, "descr": "Invalid Auto LED Pause time", "result": json_validity}
    if specialErr == "sysCmd":
        return {"res": "ERR", "code": 10, "descr": "Invalid or unknown system command", "result": json_validity}
    return {"res": "ERR", "code": 6, "descr": "Unknown error", "result": json_validity}

async def set_sensor_value(prev_values, setter, cfg, getter=None, default=0, force=False, debug=False):
    # take result from update_valid_json and save it to sensor with the setter function.
    # for volatile sensor memories, return values to cmd_post_check to be saved to system config.
    # in case of sensor update errors, try to load values from sensor to keep them
    # in case of load error, try to load from system config. If this also fails, take default value.
    # force updates the value in case of a valid, non-empty value even if it's unchanged.
    prev_valid, prev_updated, prev_key, any_set, json_validity, dst_json_value, value, cmd_keys = prev_values
    if prev_valid and (prev_updated or (force and (value is not None))):
        try:
            await setter(value)
            if debug: print(prev_key + " set to " + str(value))
            if force and (value is not None):
                json_validity[prev_key] = "Valid"
            success = True
        except:
            json_validity[prev_key] = "Failed"
            if debug: print(prev_key + " setting failed!")
            success = False
        if (not success) and (not prev_key in cmd_keys):  # reuse "success" as guaranteed to be False below. Only if not command-only key.
            if getter is not None:
                try:
                    if debug: print("Loading current value from sensor.")
                    value = await getter()
                    success = True
                except:
                    if debug: print("Loading value from sensor failed.")
                    success = False
            if not success:
                if debug: print("Loading previous setting.")
                (valid, json_val) = await cfg.get_json([prev_key])
                if valid:
                    value = json_val[prev_key]
                else:
                    if debug: print("Loading previous setting failed, using default value")
                    value = default
            dst_json_value[prev_key] = value
    return prev_valid, prev_updated, prev_key, any_set, json_validity, dst_json_value, value, cmd_keys

def get_valid_values(prev_values, keys):
    prev_valid, prev_updated, prev_key, any_set, json_validity, dst_json_value, value, cmd_keys = prev_values
    ret = {}
    valid = True
    for key in keys:
        if key in dst_json_value:
            ret[key] = dst_json_value[key]
            if json_validity[key] not in ["Valid", "Unchanged"]:
                valid = False
        else:
            ret[key] = None
            valid = False
    return ret, valid



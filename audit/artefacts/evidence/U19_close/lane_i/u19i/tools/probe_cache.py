from _sensortask_scenarios import register_for_device, build, _module_objects, _float_config_keys
register_for_device("dev")
m = build("dev")
for name, obj in _module_objects(m).items():
    keys = _float_config_keys(obj)
    if keys:
        print(name, keys, sorted(getattr(obj.cfgmgr, "_cache", {}).keys()))

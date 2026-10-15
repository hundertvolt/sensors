import sys
src, dst, which = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
plants = {
    "mgr_none_reads_callback": ('            if sensor_conf is None:\n                return {name: {"error": "unavailable"}}  # the store persisted its own entry; the callback is not read\n', ""),
    "callback_none_merged": ('                    if sensor_callback is None:\n                        return {name: {"error": "unavailable"}}  # the driver persisted its own entry\n', ""),
    "callback_raise_keeps_map": ('                    await self.pr.err_s("Error reading config from sensor:", e, errno=_ERR_CFG_CALLBACK_RAISED)\n                    return {name: {"error": "unavailable"}}\n', '                    await self.pr.err_s("Error reading config from sensor:", e, errno=_ERR_CFG_CALLBACK_RAISED)\n'),
    "mgr_raise_keeps_map": ('                await self.pr.err_s("Error updating config dict:", e, errno=_ERR_CFG_GET_RAISED)\n                return {name: {"error": "unavailable"}}\n', '                await self.pr.err_s("Error updating config dict:", e, errno=_ERR_CFG_GET_RAISED)\n                sensor_conf = {}\n'),
}
old, new = plants[which]
assert s.count(old) == 1, which
open(dst, "w").write(s.replace(old, new))

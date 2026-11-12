# R0, DECREV 9 item 3: does a C-stack check inside the logger's entry still record an overflow caught at a nearly
# exhausted C stack? Each level's handler only logs (pr.err-style, the planned form); a logging call that overflows again
# raises out of its handler, so an outer handler must record it. Prints one fact line per case.
import asyncio

_STACK_EXHAUSTED = "maximum recursion depth exceeded"
state = {"fatal": False, "recorded_at": None, "log_raised": 0, "logged": 0}


class Log:
    def _line(self, depth, args):
        for a in args:  # the planned check: ahead of the level gate and any write
            if isinstance(a, BaseException) and a.args and a.args[0] == _STACK_EXHAUSTED and not state["fatal"]:
                state["fatal"] = True
                state["recorded_at"] = depth
        state["logged"] += 1

    def err(self, depth, *args):
        self._line(depth, args)


pr = Log()


def dive(n):
    try:
        return dive(n + 1)
    except Exception as e:
        try:
            pr.err(n, "handler caught", e)
        except RuntimeError:
            state["log_raised"] += 1
            raise
        return n


async def adive(n):
    try:
        return await adive(n + 1)
    except Exception as e:
        try:
            pr.err(n, "handler caught", e)
        except RuntimeError:
            state["log_raised"] += 1
            raise
        return n


def report(name, deepest):
    print("FACT", name, "fatal=%s recorded_at=%s deepest_handler=%s log_raised=%d" % (
        state["fatal"], state["recorded_at"], deepest, state["log_raised"]))


def reset():
    state.update(fatal=False, recorded_at=None, log_raised=0, logged=0)


try:
    d = dive(0)
except RuntimeError:
    d = "escaped"
report("sync", d)
reset()


async def main():
    try:
        return await adive(0)
    except RuntimeError:
        return "escaped"


report("async", asyncio.run(main()))

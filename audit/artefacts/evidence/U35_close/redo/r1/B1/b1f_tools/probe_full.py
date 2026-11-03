# B1 falsifier probe 2: a C-stack overflow handed to a logger entry on a really full heap (not locked).
import gc

import asy_print_log as L


def overflow():
    def dive(d):
        return dive(d + 1)

    try:
        dive(0)
    except RuntimeError as e:
        return e
    return None


def attempt(i, pr, ov):
    hog = [None] * 4000
    n = 0
    size = 1 << 20
    raised = None
    c = None
    while size >= 1 and n < 4000:
        try:
            hog[n] = bytearray(size)
            n += 1
        except MemoryError:
            size //= 2
    try:
        if i == 0:
            L.report_if_fatal(ov)
        elif i == 1:
            pr.err("caught:", ov)
        elif i == 2:
            pr.wrn("caught:", ov)
        elif i == 3:
            c = pr.err_s("caught:", ov, errno=0)
            c.send(None)
        else:
            pr.err_nomem("caught:", ov)
    except StopIteration:
        pass
    except MemoryError as m:
        raised = m
    rec = L.fatal_reported()
    hog = None
    return n, raised, rec


def main():
    ov = overflow()
    pr = L.PrintLogHistory(2, 0, name="P")
    names = ("report_if_fatal", "err", "wrn", "err_s", "err_nomem")
    for i in range(len(names)):
        L._fatal = False
        n, raised, rec = attempt(i, pr, ov)
        gc.collect()
        print("FULL", names[i], "blocks", n, "raised:", raised, "|", "recorded" if rec else "NOT recorded")


main()

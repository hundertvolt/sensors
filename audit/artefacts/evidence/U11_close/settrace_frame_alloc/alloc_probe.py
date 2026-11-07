import gc, sys
def raised():
    try:
        raise ValueError("probe")
    except ValueError as e:
        return e
exc = raised()
def m(label, fn):
    fn()  # warm once
    for i in range(3):
        gc.collect(); b = gc.mem_alloc(); fn(); a = gc.mem_alloc()
        print("RESULT", label, i, a - b)
def nothing(): pass
m("empty_py_call", nothing)
m("print", lambda: print("X", "unretrieved"))
m("print_exception", lambda: sys.print_exception(exc))
def f2():
    try:
        sys.print_exception(exc)
    finally:
        pass
m("print_exception_in_try", f2)

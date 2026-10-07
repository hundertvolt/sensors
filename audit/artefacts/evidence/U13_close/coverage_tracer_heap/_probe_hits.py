hits = None
def count():
    if hits is None:
        return -1
    n = 0
    for v in hits.values():
        n += len(v)
    return n

import gc
import sys
names = sys.argv[2].split(",")
if len(sys.argv) > 3:
    gc.threshold(int(sys.argv[3]))
src = open(sys.argv[1]).read().replace('if __name__ == "__main__":', 'if False:')
g = {"__name__": "x"}
exec(src, g)
import microtest
microtest.run({n: g[n] for n in names})

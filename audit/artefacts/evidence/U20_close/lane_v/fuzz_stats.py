import sys, tempfile, copy, random, tomllib, collections
from pathlib import Path
root = Path(sys.argv[1]); sys.path[:0] = [str(root), str(root / "tests_scripts")]
import test_buildgen_fuzz as t
from buildgen.validate import build_model
from buildgen.errors import BuildError
from buildgen.graph import build_construction_order
from buildgen.codegen import generate_module_source
from _toml_fixtures import base_doc, write_doc
from _devices import DEVICE_NAMES, device_toml
src = root / "src"
bases = [base_doc(), *(tomllib.loads(device_toml(d).read_text()) for d in DEVICE_NAMES)]
rng = random.Random(t._SEED); rules = collections.Counter(); built = 0
with tempfile.TemporaryDirectory(dir=".") as d:
    for case in range(t._CASES):
        doc = copy.deepcopy(rng.choice(bases))
        did = [t._mutate(rng, doc) for _ in range(rng.randint(1, 3))]
        path = write_doc(Path(d), "fixture", doc)
        try:
            m = build_model(path, src); generate_module_source(m, build_construction_order(m), "x", src); built += 1
        except BuildError as e:
            rules[e.rule] += 1
print("built", built, "refused", sum(rules.values()), "distinct rules", len(rules))
for r, c in rules.most_common(): print(c, r)

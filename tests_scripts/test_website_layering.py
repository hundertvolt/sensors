"""The website's visual/mechanics split (SPECIFICATION.md Part H.3) over js/*.js: elements built in templates.js only,
`document` read by entries only, controllers writing only documented data-* hooks, key selectors escaped, HTML sinks
banned. Text-based, no JS parser offline: an aliased or computed call evades it. Each rule bites on a planted copy."""

import re
import shutil
from pathlib import Path

import pytest

_TEMPLATES = "templates.js"
_ENTRIES = frozenset({"main.js", "app.js"})
_CONTROLLERS = frozenset({"render.js", "nav.js", "shell.js", "main.js", "app.js"})
# The data-* hooks a controller may write (SPECIFICATION.md Part H.3); every other one is the visual layer's.
_DATASET_HOOKS = frozenset({"applyStatus", "shown", "navOpen", "sourceState"})
_PRODUCTION_GLOBS = ('"js/**/*.js"', '"html/**/*.html"')
_SINKS = ('{ property: "innerHTML" }', '{ property: "outerHTML" }', '{ property: "insertAdjacentHTML" }', '{ object: "document", property: "write" }', '{ object: "document", property: "writeln" }')

_CREATE_ELEMENT = re.compile(r"\bcreateElement\s*\(")
_DOCUMENT_QUERY = re.compile(r"\bdocument\s*\.\s*(?:querySelector\w*|getElementById|getElementsBy\w+|addEventListener|body|documentElement|visibilityState)\b")
_CLASS_OR_STYLE_WRITE = re.compile(
    r"\.className\s*(?:=(?!=)|\+=)|\.classList\s*\.\s*(?:add|remove|toggle|replace)\s*\(|\.style\s*(?:\.\s*\w+\s*)?(?:=(?!=)|\+=)|\.style\s*\.\s*(?:setProperty|removeProperty)\s*\(",
)
_DATASET_WRITE = re.compile(r"\.dataset\s*\.\s*(?P<hook>\w+)\s*(?:=(?!=)|\+=|\?\?=|\|\|=)")
_DATASET_DELETE = re.compile(r"\bdelete\s+[\w$.?]+?\.dataset\s*\.\s*(?P<hook>\w+)")
_DATASET_COMPUTED = re.compile(r"\.dataset\s*\[")
_SELECTOR_CALL = re.compile(r"\b(?:querySelector|querySelectorAll|closest)\s*\(\s*`")
# After a regex literal may start: an operator, an opening bracket or one of these keywords.
_REGEX_KEYWORDS = ("return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do")


def _code_of(source: str) -> str:
    """The JS source with comments, string text and template text dropped; every `${...}` and newline kept."""
    return _strip(source, 0, in_expression=False)[0]


def _eslint_problems(config: str) -> "list[str]":
    problems = [f"eslint.config.js: PRODUCTION_ONLY_RULES lacks {sink}" for sink in _SINKS if sink not in config]
    for glob in _PRODUCTION_GLOBS:
        start = config.find(f"files: [{glob}]")
        end = config.find("files:", start + 1)
        if start < 0 or "...PRODUCTION_ONLY_RULES" not in config[start : end if end > 0 else len(config)]:
            problems.append(f"eslint.config.js: the {glob} block does not apply PRODUCTION_ONLY_RULES")
    return problems


def _file_problems(name: str, code: str) -> "list[str]":
    problems: list[str] = []

    def at(offset: int, what: str) -> None:
        problems.append(f"js/{name}:{code.count(chr(10), 0, offset) + 1}: {what}")

    if name != _TEMPLATES:
        for match in _CREATE_ELEMENT.finditer(code):
            at(match.start(), "createElement outside js/templates.js")
        for match in _CLASS_OR_STYLE_WRITE.finditer(code):
            at(match.start(), f"class or style write outside js/templates.js: {match.group(0).strip()}")
    if name not in _ENTRIES:
        for match in _DOCUMENT_QUERY.finditer(code):
            at(match.start(), f"{match.group(0)} outside the entries")
    if name in _CONTROLLERS:
        for pattern in (_DATASET_WRITE, _DATASET_DELETE):
            for match in pattern.finditer(code):
                if match.group("hook") not in _DATASET_HOOKS:
                    at(match.start(), f"controller writes dataset.{match.group('hook')}, not a documented hook")
        for match in _DATASET_COMPUTED.finditer(code):
            at(match.start(), "controller writes a computed dataset key")
    for match in _SELECTOR_CALL.finditer(code):
        if any("CSS.escape(" not in expression for expression in _template_expressions(code, match.end() - 1)):
            at(match.start(), "a selector template interpolates a value without CSS.escape()")
    return problems


def _layering_problems(root: Path) -> "list[str]":
    """Every layering breach in `root`'s js/*.js and eslint.config.js, one "<where>: <what>" line each."""
    problems = _eslint_problems((root / "eslint.config.js").read_text(encoding="utf-8"))
    for path in sorted((root / "js").glob("*.js")):
        problems += _file_problems(path.name, _code_of(path.read_text(encoding="utf-8")))
    return problems


def _planted_copy(repo_root: Path, tmp_path: Path) -> Path:
    shutil.copytree(repo_root / "js", tmp_path / "js")
    shutil.copy(repo_root / "eslint.config.js", tmp_path / "eslint.config.js")
    return tmp_path


def _regex_may_start(code: str) -> bool:
    # Whether a `/` after the code emitted so far opens a regex literal rather than dividing.
    tail = code.rstrip()
    if not tail:
        return True
    if tail[-1] in "(,=:[!&|?{};+-*%<>~^":
        return True
    word = re.search(r"[\w$]+$", tail)
    return word is not None and word.group(0) in _REGEX_KEYWORDS


def _skip_quoted(source: str, start: int) -> int:
    # The index just past the string literal opening at `start`.
    quote, i = source[start], start + 1
    while i < len(source) and source[i] != quote:
        i += 2 if source[i] == "\\" else 1
    return i + 1


def _skip_regex(source: str, start: int) -> int:
    # The index just past the regex literal (flags included) opening at `start`.
    i, in_class = start + 1, False
    while i < len(source):
        ch = source[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif ch == "/" and not in_class:
            i += 1
            break
        i += 1
    while i < len(source) and source[i].isalpha():
        i += 1
    return i


def _strip(source: str, start: int, *, in_expression: bool) -> "tuple[str, int]":
    # Code with comments and string text dropped and template text dropped around its kept ${...}; newlines kept.
    out: list[str] = []
    i, depth = start, 0
    while i < len(source):
        ch, nxt = source[i], source[i + 1 : i + 2]
        if ch == "/" and nxt == "/":
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
        elif ch == "/" and nxt == "*":
            end = source.find("*/", i + 2)
            end = len(source) if end < 0 else end + 2
            out.append("\n" * source.count("\n", i, end))
            i = end
        elif ch in "'\"":
            i = _skip_quoted(source, i)
            out.append(ch * 2)
        elif ch == "`":
            text, i = _strip_template(source, i)
            out.append(text)
        elif ch == "/" and _regex_may_start("".join(out)):
            i = _skip_regex(source, i)
            out.append("/r/")
        elif in_expression and ch == "}" and depth == 0:
            return "".join(out), i + 1
        else:
            depth += {"{": 1, "}": -1}.get(ch, 0)
            out.append(ch)
            i += 1
    return "".join(out), i


def _strip_template(source: str, start: int) -> "tuple[str, int]":
    # A template literal as "`" + each ${...} kept + "`", its text dropped but its newlines kept.
    out = ["`"]
    i = start + 1
    while i < len(source) and source[i] != "`":
        if source[i] == "\\":
            i += 2
        elif source.startswith("${", i):
            expression, i = _strip(source, i + 2, in_expression=True)
            out.append("${" + expression + "}")
        else:
            out.append("\n" if source[i] == "\n" else "")
            i += 1
    out.append("`")
    return "".join(out), i + 1


def _template_expressions(code: str, start: int) -> "list[str]":
    # The top-level ${...} expressions of the stripped template literal whose backtick is at `start`.
    expressions: list[str] = []
    i = start + 1
    while i < len(code) and code[i] != "`":
        if code.startswith("${", i):
            depth, j = 1, i + 2
            while j < len(code) and depth > 0:
                depth += {"{": 1, "}": -1}.get(code[j], 0)
                j += 1
            expressions.append(code[i + 2 : j - 1])
            i = j
        else:
            i += 1
    return expressions


def test_the_real_tree_keeps_the_layering(repo_root: Path) -> None:
    assert _layering_problems(repo_root) == []


def test_code_of_drops_comments_and_text_and_keeps_template_expressions() -> None:
    source = 'a("x // y"); // document.body\n/* createElement( */ b(`t ${c(`u ${d}`)} v`, /[`"]/u, \'z\');\n'
    assert _code_of(source) == 'a(""); \n b(`${c(`${d}`)}`, /r/, \'\');\n'


@pytest.mark.parametrize(
    ("name", "snippet", "expected"),
    [
        ("render.js", 'const made = document.createElement("div");', "createElement outside js/templates.js"),
        ("nav.js", 'document.querySelector("#x");', "document.querySelector outside the entries"),
        ("shell.js", "document.visibilityState;", "document.visibilityState outside the entries"),
        ("render.js", 'card.classList.add("hidden");', "class or style write outside js/templates.js"),
        ("nav.js", 'card.className = "card";', "class or style write outside js/templates.js"),
        ("render.js", 'card.style.color = "red";', "class or style write outside js/templates.js"),
        ("render.js", 'card.dataset.hasErrors = "true";', "controller writes dataset.hasErrors"),
        ("nav.js", "delete card.dataset.filter;", "controller writes dataset.filter"),
        ("shell.js", 'card.dataset[key] = "1";', "controller writes a computed dataset key"),
        ("render.js", 'card.querySelector(`[data-field-key="${key}"]`);', "without CSS.escape()"),
        ("templates.js", 'card.closest(`[data-a="${CSS.escape(a)}"][data-b="${b}"]`);', "without CSS.escape()"),
    ],
)
def test_each_rule_bites_on_a_planted_breach(repo_root: Path, tmp_path: Path, name: str, snippet: str, expected: str) -> None:
    before = set(_layering_problems(repo_root))
    copy = _planted_copy(repo_root, tmp_path)
    with (copy / "js" / name).open("a", encoding="utf-8") as js:
        js.write(f"\n{snippet}\n")
    planted = set(_layering_problems(copy)) - before
    assert len(planted) == 1, planted
    assert expected in planted.pop()


@pytest.mark.parametrize("snippet", ['// document.createElement("x");', 'const text = "el.className = 1; document.body";', "const t = `card.style.color = ${CSS.escape(a)}`;"])
def test_a_breach_inside_a_comment_or_text_is_not_one(repo_root: Path, tmp_path: Path, snippet: str) -> None:
    before = set(_layering_problems(repo_root))
    copy = _planted_copy(repo_root, tmp_path)
    with (copy / "js" / "render.js").open("a", encoding="utf-8") as js:
        js.write(f"\n{snippet}\n")
    assert set(_layering_problems(copy)) - before == set()


@pytest.mark.parametrize(("old", "expected"), [('        { property: "innerHTML" },\n', 'lacks { property: "innerHTML" }'), ("rules: { ...BUG_CATCHING_RULES, ...PRODUCTION_ONLY_RULES, ...COMMENT_RULES },\n    },\n];", '"html/**/*.html" block')])
def test_the_eslint_sink_rule_bites_when_dropped(repo_root: Path, tmp_path: Path, old: str, expected: str) -> None:
    copy = _planted_copy(repo_root, tmp_path)
    config = (copy / "eslint.config.js").read_text(encoding="utf-8")
    assert config.count(old) == 1
    (copy / "eslint.config.js").write_text(config.replace(old, old.replace("innerHTML", "x-innerHTML").replace(", ...PRODUCTION_ONLY_RULES", "")), encoding="utf-8")
    planted = set(_layering_problems(copy)) - set(_layering_problems(repo_root))
    assert any(expected in problem for problem in planted), planted

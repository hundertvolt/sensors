"""The await-chain analysis tests_scripts/test_await_depth.py runs (SPECIFICATION.md F.1): from every task top in src/ and
the generated modules, the longest run of nested coroutine frames a resumed task re-enters in C, through the calls that
constructions and argument flow resolve, annotations only where a call goes unseen; a task-creating call starts a chain."""

import ast
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from buildgen.generate import generate_device

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

Function = ast.FunctionDef | ast.AsyncFunctionDef
Key = tuple[str, str]
Stack = tuple[Key, ...]

_MAX_NESTING = 3  # a container of containers of containers: deeper element sets are dropped, never followed
_MAX_PASSES = 40
_MICRODOT = "microdot.Microdot"
_INVOKE = "microdot.invoke_handler"
_ERROR_RESPONSE = "microdot.Microdot.error_response"
_ROUTE_REGISTRARS = frozenset({"get", "put", "post", "delete", "patch", "route"})
_ERROR_REGISTRARS = frozenset({"errorhandler"})
# asyncio's own awaitables, by the frames a resumed task re-enters for each (extmod/asyncio/, v1.29.0): wait_for() and its
# sleep; Lock.__aenter__() and its acquire() generator; every other one, a single generator or SingletonGenerator frame.
_ASYNCIO_AWAIT_DEPTH = {"wait_for": 2, "wait_for_ms": 2}
_ASYNCIO_WITH_DEPTH = {"Lock": 2}
_TASK_STARTERS = frozenset({"create_task", "wait_for", "wait_for_ms", "gather", "run"})
_SEQUENCE_TYPES = frozenset({"list", "List", "Sequence", "Iterable", "Iterator", "set", "frozenset", "Set", "deque"})
_MAPPING_TYPES = frozenset({"dict", "Dict", "Mapping"})
_COPYING_BUILTINS = frozenset({"list", "tuple", "sorted", "iter", "reversed", "set", "frozenset"})
_CONTAINER_MUTATORS = frozenset({"append", "extend", "insert", "update"})


class V(NamedTuple):
    # One abstract value: `kind` names the variant, the other fields carry what that variant needs (unused ones stay empty).
    kind: str
    name: str = ""
    recv: str = ""
    attr: str = ""
    depth: int = 0
    inner: frozenset["V"] = frozenset()
    parts: tuple[frozenset["V"], ...] = ()


_NO: frozenset[V] = frozenset()


class Chain(NamedTuple):
    depth: int
    path: tuple[str, ...]


class _Fn:
    def __init__(self, q: str, module: str, node: Function, cls: "_Cls | None", outer: "_Fn | None") -> None:
        self.q, self.module, self.node, self.cls, self.outer = q, module, node, cls, outer
        self.is_async = isinstance(node, ast.AsyncFunctionDef)
        self.globals_declared = {name for stmt in ast.walk(node) if isinstance(stmt, ast.Global) for name in stmt.names}
        decorators = {d.id for d in node.decorator_list if isinstance(d, ast.Name)}
        self.is_classmethod = "classmethod" in decorators
        # Called by the interpreter (a dunder; __init__ follows its constructions) or through a decorator: never by a call
        # the walk binds, so its parameters keep their annotations.
        dunder = node.name[:2] == node.name[-2:] == "__" and node.name != "__init__"
        self.called_unseen = dunder or any(not (isinstance(d, ast.Name) and d.id in ("classmethod", "staticmethod")) for d in node.decorator_list)
        params = node.args.posonlyargs + node.args.args
        bound = cls is not None and bool(params) and "staticmethod" not in decorators and not self.is_classmethod
        self.self_name = params[0].arg if bound else ""


class _Cls:
    def __init__(self, q: str, module: str, node: ast.ClassDef) -> None:
        self.q, self.module, self.node = q, module, node
        self.bases: list[str] = []
        self.methods: dict[str, list[_Fn]] = {}
        names = {b.id if isinstance(b, ast.Name) else b.attr if isinstance(b, ast.Attribute) else "" for b in node.bases}
        self.is_protocol = "Protocol" in names
        self.is_namedtuple = "NamedTuple" in names
        self.fields = [s.target.id for s in node.body if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)]


class Program:
    def __init__(self, modules: "dict[str, ast.Module]", top_modules: "set[str]") -> None:
        self.modules, self.top_modules = modules, top_modules
        self.fns: dict[str, _Fn] = {}
        self.classes: dict[str, _Cls] = {}
        self.tops: set[str] = set()
        self._by_node: dict[ast.AST, str] = {}
        self._symbols: dict[str, dict[str, set[tuple[str, ...]]]] = {m: {} for m in modules}
        self._aliases: dict[str, dict[str, ast.expr]] = {m: {} for m in modules}
        self._locals: dict[str, dict[str, frozenset[V]]] = {}
        self._attrs: dict[tuple[str, str], frozenset[V]] = {}
        self._returns: dict[str, frozenset[V]] = {}
        self._handlers: dict[str, frozenset[V]] = {}
        self._constructed: set[str] = set()
        self._changed = False
        self._frozen = False
        self._memo: dict[tuple[Key, frozenset[Key]], Chain] = {}
        self._components: dict[Key, frozenset[Key]] = {}
        self._site_cache: dict[Key, tuple[tuple[frozenset[Key], int], ...]] = {}
        for module, tree in modules.items():
            self._index_body(module, tree.body, module, None, None)
        for c in self.classes.values():
            for base in c.node.bases:
                c.bases.extend(s[1] for s in self._symbol_expr(c.module, base) if s[0] == "cls")
        self._mro_of = {q: _linearized(q, self.classes) for q in self.classes}
        self._subclasses_of: dict[str, set[str]] = {q: set() for q in self.classes}
        for q, mro in self._mro_of.items():
            for ancestor in mro[1:]:
                self._subclasses_of[ancestor].add(q)
        self._family_of = {q: set(mro).union(*(self._mro_of[s] for s in self._subclasses_of[q])) for q, mro in self._mro_of.items()}
        self._implementers_of = {q: self._implementers(q) for q, c in self.classes.items() if c.is_protocol}
        self._parts: dict[ast.stmt, tuple[list[ast.Call], list[ast.stmt]]] = {}
        # A parameter takes its annotation only where a call the walk cannot bind may fill it (_open_unbound()): every one
        # of an _open function, each _open_params pair; the per-pass records below decide it at each fixpoint.
        self._open = {q for q, f in self.fns.items() if f.called_unseen}
        self._open_params: set[tuple[str, str]] = set()
        self._called: set[str] = set()
        self._partial: set[str] = set()
        self._unresolved: set[str] = set()
        self._loose: set[tuple[str, str]] = set()
        self._bound_calls: set[ast.Call] = set()

    def _add(self, store: "dict[str, frozenset[V]]", key: str, vals: "Iterable[V]") -> None:
        merged = self._merged(store.get(key, _NO), vals)
        if merged is not None:
            store[key] = merged

    def _add_attr(self, key: "tuple[str, str]", vals: "Iterable[V]") -> None:
        merged = self._merged(self._attrs.get(key, _NO), vals)
        if merged is not None:
            self._attrs[key] = merged

    def _add_top(self, q: str) -> None:
        if not self._frozen and q not in self.tops:
            self.tops.add(q)
            self._changed = True

    def _annotation(self, module: str, expr: "ast.expr | None", depth: int = 0) -> frozenset[V]:
        # The values an annotation names: a project class's instances, with list, dict and tuple element sets.
        if expr is None or depth > _MAX_NESTING * 2:
            return _NO
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            try:
                return self._annotation(module, ast.parse(expr.value, mode="eval").body, depth + 1)
            except SyntaxError:
                return _NO
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.BitOr):
            return self._annotation(module, expr.left, depth + 1) | self._annotation(module, expr.right, depth + 1)
        if isinstance(expr, ast.Subscript):
            return self._annotation_generic(module, expr, depth)
        if isinstance(expr, (ast.Name, ast.Attribute)):
            found = frozenset(V("inst", s[1]) for s in self._symbol_expr(module, expr) if s[0] == "cls")
            if not found and isinstance(expr, ast.Name) and expr.id in self._aliases[module]:
                return self._annotation(module, self._aliases[module][expr.id], depth + 1)
            return found
        return _NO

    def _annotation_generic(self, module: str, expr: ast.Subscript, depth: int) -> frozenset[V]:
        base = expr.value.attr if isinstance(expr.value, ast.Attribute) else expr.value.id if isinstance(expr.value, ast.Name) else ""
        args = expr.slice.elts if isinstance(expr.slice, ast.Tuple) else [expr.slice]
        sub = [self._annotation(module, a, depth + 1) for a in args]
        if base in ("Optional", "Final", "ClassVar"):
            return sub[0]
        if base == "Union":
            return frozenset().union(*sub)
        if base in _SEQUENCE_TYPES:
            return _seq(sub[0])
        if base in _MAPPING_TYPES:
            return _seq(sub[-1])
        if base in ("tuple", "Tuple"):
            if len(args) == 2 and isinstance(args[1], ast.Constant) and args[1].value is Ellipsis:
                return _seq(sub[0])
            return _normalized({V("tup", parts=tuple(sub))})
        return _NO

    def _attr_values(self, cq: str, name: str, *, exact: bool) -> frozenset[V]:
        # An exact receiver reads its own MRO; a class-or-subclass one reads the whole family (class hierarchy analysis).
        owners = self._mro(cq) if exact else self._family_of.get(cq, {cq})
        found = frozenset().union(*(self._attrs.get((k, name), _NO) for k in owners))
        if exact and self._definer(cq, name):
            return found | {V("emeth", cq, attr=name)}
        if not exact and self._method_defs(cq, name):
            return found | {V("meth", cq, attr=name)}
        return found

    def _bind(self, fn: "_Fn | None", module: str, target: ast.expr, vals: frozenset[V]) -> None:
        if isinstance(target, ast.Name):
            scope = "<module>." + module if fn is None or target.id in fn.globals_declared else fn.q
            self._add(self._locals.setdefault(scope, {}), target.id, vals)
        elif isinstance(target, ast.Attribute):
            for v in self._ev(fn, module, target.value):
                if v.kind in ("inst", "exact"):
                    self._add_attr((v.name, target.attr), vals)
        elif isinstance(target, (ast.Tuple, ast.List)):
            width = len(target.elts)
            for i, sub in enumerate(target.elts):
                part = frozenset().union(*(v.parts[i] if v.kind == "tup" and len(v.parts) == width else v.inner for v in vals if v.kind in ("tup", "seq")))
                self._bind(fn, module, sub.value if isinstance(sub, ast.Starred) else sub, part)
        elif isinstance(target, ast.Subscript):
            self._bind(fn, module, target.value, _seq(vals))

    def _bind_arg(self, q: str, env: "dict[str, frozenset[V]]", param: str, fn: "_Fn | None", module: str, arg: ast.expr) -> None:
        # One argument (or default) into q's parameter; one whose value the flow does not know leaves the parameter loose.
        vals = self._ev(fn, module, arg)
        if vals:
            self._add(env, param, vals)
        elif not isinstance(arg, ast.Constant):
            self._loose.add((q, param))

    def _bind_call(self, fn: "_Fn | None", module: str, call: ast.Call) -> None:
        # Argument flow: each resolved callee's parameters, a constructor's NamedTuple fields, an append/extend's list. A
        # call resolving to nothing, its receiver not outside the program, is recorded by the name it calls.
        callees = self._ev(fn, module, call.func)
        self._bound_calls.add(call)
        if not callees and not self._external_receiver(fn, module, call.func):
            self._unresolved.add(_callee_name(call.func))
        for v in callees:
            if v.kind == "func":
                self._bind_params(self.fns[v.name], call, fn, module)
            elif v.kind in ("meth", "emeth", "smeth"):
                for d in self._callables(frozenset({v})):
                    self._bind_params(d, call, fn, module)
            elif v.kind in ("cls", "subcls"):
                for k in [v.name] if v.kind == "cls" else [v.name, *sorted(self._subclasses_of[v.name])]:
                    self._bind_constructor(self.classes[k], call, fn, module)
                self._construct(v.name)
            elif v.kind == "cmeth" and v.attr in _CONTAINER_MUTATORS and isinstance(call.func, ast.Attribute) and call.args:
                last = self._ev(fn, module, call.args[-1])
                self._bind(fn, module, call.func.value, _seq(last if v.attr in ("append", "insert") else _elements(last)))
        if isinstance(call.func, ast.Call) and call.args:
            self._register_handler(fn, module, call)
        if isinstance(call.func, ast.Attribute) and call.func.attr in _TASK_STARTERS | {"start_server"}:
            self._ev(fn, module, call)

    def _bind_constructor(self, cls: _Cls, call: ast.Call, fn: "_Fn | None", module: str) -> None:
        if cls.is_namedtuple:
            for name, arg in zip(cls.fields, call.args, strict=False):
                self._add_attr((cls.q, name), self._ev(fn, module, arg))
            for kw in call.keywords:
                if kw.arg:
                    self._add_attr((cls.q, kw.arg), self._ev(fn, module, kw.value))
        for init in self._definer(cls.q, "__init__")[:1]:
            self._bind_params(init, call, fn, module)

    def _bind_params(self, callee: _Fn, call: ast.Call, fn: "_Fn | None", module: str) -> None:
        args = callee.node.args
        params = [p.arg for p in args.posonlyargs + args.args]
        if (callee.self_name or callee.is_classmethod) and params:
            params = params[1:]
        env = self._locals.setdefault(callee.q, {})
        self._called.add(callee.q)
        for i, arg in enumerate(call.args):
            if isinstance(arg, ast.Starred):
                if i < len(params):
                    self._partial.add(callee.q)
                if args.vararg is not None:
                    self._add(env, args.vararg.arg, self._ev(fn, module, arg.value))
                break
            if i < len(params):
                self._bind_arg(callee.q, env, params[i], fn, module, arg)
            elif args.vararg is not None:
                self._add(env, args.vararg.arg, _seq(self._ev(fn, module, arg)))
        names = set(params) | {p.arg for p in args.kwonlyargs}
        for kw in call.keywords:
            if kw.arg in names:
                self._bind_arg(callee.q, env, kw.arg, fn, module, kw.value)
            else:
                self._partial.add(callee.q)  # a ** mapping, or a name only a **kwargs takes

    def _builtin_call(self, fn: "_Fn | None", module: str, call: ast.Call, recv: str) -> frozenset[V]:
        name = call.func.id if isinstance(call.func, ast.Name) else ""
        if name in _COPYING_BUILTINS and call.args:
            return _seq(_elements(self._ev(fn, module, call.args[0], recv)))
        if name == "dict" and call.args:
            return self._ev(fn, module, call.args[0], recv)
        if name == "super" and fn is not None and fn.cls is not None:
            return frozenset({V("super", fn.cls.q, recv=recv)})
        if name != "getattr" or len(call.args) < 2:
            return _NO
        objects = [v for v in self._ev(fn, module, call.args[0], recv) if v.kind in ("inst", "exact")]
        found: set[V] = set()
        for s in self._ev(fn, module, call.args[1], recv):
            for obj in objects if s.kind == "str" else []:
                found |= self._attr_values(obj.name, s.name, exact=obj.kind == "exact")
        for default in call.args[2:]:
            found |= self._ev(fn, module, default, recv)
        return frozenset(found)

    def _call_result(self, defs: "Iterable[_Fn]", recv: str) -> frozenset[V]:
        # An async callee returns its coroutine (the receiver it runs on kept); a plain one returns what it returns.
        out: set[V] = set()
        for d in defs:
            out |= {V("coro", d.q, recv=recv)} if d.is_async else self._returns.get(d.q, _NO)
        return frozenset(out)

    def _callables(self, vals: frozenset[V]) -> "list[_Fn]":
        out: list[_Fn] = []
        for v in vals:
            if v.kind == "func":
                out.append(self.fns[v.name])
            elif v.kind == "meth":
                out.extend(self._method_defs(v.name, v.attr))
            elif v.kind == "emeth":
                out.extend(self._definer(v.name, v.attr))
            elif v.kind == "smeth":
                out.extend(self._definer(v.recv or v.name, v.attr, after=v.name))
        return out

    def _chain_of(self, q: str, recv: str, stack: Stack) -> Chain:
        key = (q, recv)
        if key in stack:
            return Chain(1, (self._label(q, recv) + " (cycle)",))
        # A walk below key can cut only the stack's members on a cycle with key: memoised with them, a cut chain is
        # reused only where the same cuts happen, so the result never depends on which top reached key first.
        memo_key = (key, self._component(key).intersection(stack))
        if memo_key in self._memo:
            return self._memo[memo_key]
        best = Chain(0, ())
        for targets, floor in self._sites(key):
            site = self._deepest(targets, (*stack, key))
            best = _deeper(best, site if site.depth >= floor else Chain(floor, ()))
        chain = Chain(best.depth + 1, (self._label(q, recv), *best.path))
        self._memo[memo_key] = chain
        return chain

    def _component(self, key: Key) -> frozenset[Key]:
        # The keys on a cycle with key, key alone when it is on none: its strongly connected component of the await graph.
        if key not in self._components:
            self._tarjan(key, {}, [])
        return self._components[key]

    def _concrete(self, cq: str) -> "list[str]":
        # The classes a class-or-subclass value can be at run time: the constructed ones of its family (a Protocol's
        # family: every class with its methods), or the whole family where none of it is constructed.
        cls = self.classes.get(cq)
        if cls is None:
            return []
        family = self._implementers_of.get(cq, []) if cls.is_protocol else [cq, *sorted(self._subclasses_of[cq])]
        return [k for k in family if k in self._constructed] or family

    def _construct(self, q: str) -> None:
        # A construction anywhere, its value kept or not, makes its class concrete; a new one is a change.
        if not self._frozen and q not in self._constructed:
            self._constructed.add(q)
            self._changed = True

    def _deepest(self, targets: "frozenset[Key]", stack: Stack) -> Chain:
        best = Chain(0, ())
        for q, r in sorted(targets):
            best = _deeper(best, self._chain_of(q, r, stack))
        return best

    def _definer(self, k: str, name: str, after: str = "") -> "list[_Fn]":
        mro = self._mro(k)
        if after in mro:
            mro = mro[mro.index(after) + 1 :]
        for owner in mro:
            if name in self.classes[owner].methods:
                return self.classes[owner].methods[name]
        return []

    def _ev(self, fn: "_Fn | None", module: str, expr: "ast.expr | None", recv: str = "") -> frozenset[V]:
        # The values an expression can take; recv, in the depth pass, is the exact class `self` is.
        if isinstance(expr, ast.Constant):
            return frozenset({V("str", expr.value)}) if isinstance(expr.value, str) else _NO
        if isinstance(expr, ast.Name):
            return self._lookup(fn, module, expr.id, recv)
        if isinstance(expr, ast.Attribute):
            return self._ev_attribute(fn, module, expr, recv)
        if isinstance(expr, ast.Call):
            return self._ev_call(fn, module, expr, recv)
        if isinstance(expr, (ast.List, ast.Set, ast.Tuple, ast.Dict)):
            return self._ev_display(fn, module, expr, recv)
        return _NO if expr is None else self._ev_compound(fn, module, expr, recv)

    def _ev_attribute(self, fn: "_Fn | None", module: str, expr: ast.Attribute, recv: str) -> frozenset[V]:
        out: set[V] = set()
        for v in self._ev(fn, module, expr.value, recv):
            if v.kind in ("inst", "exact"):
                out |= self._attr_values(v.name, expr.attr, exact=v.kind == "exact")
            elif v.kind == "mod":
                out |= self._symbol(v.name, expr.attr)
            elif v.kind == "ext":
                out.add(V("ext", v.name + "." + expr.attr))
            elif v.kind in ("cls", "subcls"):
                out |= self._attrs.get((v.name, expr.attr), _NO)
            elif v.kind == "super" and self._definer(v.recv or v.name, expr.attr, after=v.name):
                out.add(V("smeth", v.name, recv=v.recv, attr=expr.attr))
            elif v.kind in ("seq", "tup"):
                out.add(V("cmeth", attr=expr.attr, inner=frozenset({v})))
        return frozenset(out)

    def _ev_call(self, fn: "_Fn | None", module: str, call: ast.Call, recv: str) -> frozenset[V]:
        callees = self._ev(fn, module, call.func, recv)
        if isinstance(call.func, ast.Name) and not callees:
            return self._builtin_call(fn, module, call, recv)
        out: set[V] = set()
        for v in callees:
            if v.kind in ("cls", "subcls"):
                # A construction makes exactly the class it names; a classmethod's cls() whichever class cls is.
                out.add(V("exact" if v.kind == "cls" else "inst", v.name))
                self._construct(v.name)
            elif v.kind == "func":
                out |= self._call_result([self.fns[v.name]], "")
            elif v.kind == "meth":
                for k in self._concrete(v.name):
                    out |= self._call_result(self._definer(k, v.attr), k)
            elif v.kind in ("emeth", "smeth"):
                out |= self._call_result(self._callables(frozenset({v})), v.name if v.kind == "emeth" else v.recv)
            elif v.kind == "ext":
                out |= self._external_call(fn, module, v.name, call)
            elif v.kind == "cmeth":
                out |= _container_call(v)
        if isinstance(call.func, ast.Attribute) and call.func.attr == "create_task" and call.args and module in self.top_modules:
            self._mark_tops(fn, module, call.args[0])
        return frozenset(out)

    def _ev_compound(self, fn: "_Fn | None", module: str, expr: ast.expr, recv: str) -> frozenset[V]:
        if isinstance(expr, ast.Await):
            return frozenset().union(*(self._returns.get(v.name, _NO) for v in self._ev(fn, module, expr.value, recv) if v.kind == "coro"))
        if isinstance(expr, ast.IfExp):
            return self._ev(fn, module, expr.body, recv) | self._ev(fn, module, expr.orelse, recv)
        if isinstance(expr, ast.BoolOp):
            return frozenset().union(*(self._ev(fn, module, x, recv) for x in expr.values))
        if isinstance(expr, ast.NamedExpr):
            vals = self._ev(fn, module, expr.value, recv)
            self._bind(fn, module, expr.target, vals)
            return vals
        if isinstance(expr, ast.Subscript):
            return _elements(self._ev(fn, module, expr.value, recv))
        return _NO

    def _ev_display(self, fn: "_Fn | None", module: str, expr: "ast.List | ast.Set | ast.Tuple | ast.Dict", recv: str) -> frozenset[V]:
        if isinstance(expr, ast.Dict):
            vals = [self._ev(fn, module, v, recv) if k is not None else _elements(self._ev(fn, module, v, recv)) for k, v in zip(expr.keys, expr.values, strict=True)]
            return _seq(frozenset().union(*vals))
        starred = any(isinstance(x, ast.Starred) for x in expr.elts)
        parts = [_elements(self._ev(fn, module, x.value, recv)) if isinstance(x, ast.Starred) else self._ev(fn, module, x, recv) for x in expr.elts]
        if isinstance(expr, ast.Tuple) and not starred:
            return _normalized({V("tup", parts=tuple(parts))})
        return _seq(frozenset().union(*parts))

    def _external_call(self, fn: "_Fn | None", module: str, name: str, call: ast.Call) -> frozenset[V]:
        # A call into asyncio: a task-creating call starts chains; an awaitable counts _ASYNCIO_AWAIT_DEPTH's frames; a
        # class gives an external instance. Any other module outside the program yields nothing to follow.
        head, _, short = name.partition(".")
        if head != "asyncio":
            return _NO
        if module in self.top_modules and short in _TASK_STARTERS:
            for arg in call.args if short == "gather" else call.args[:1]:
                self._mark_tops(fn, module, arg.value if isinstance(arg, ast.Starred) else arg)
        if module in self.top_modules and short == "start_server" and call.args:
            for d in self._callables(self._ev(fn, module, call.args[0])):
                if d.is_async:
                    self._add_top(d.q)
        if short[:1].isupper():
            return frozenset({V("extinst", short)})
        return frozenset({V("extcoro", short, depth=_ASYNCIO_AWAIT_DEPTH.get(short, 1))})

    def _external_receiver(self, fn: "_Fn | None", module: str, func: ast.expr) -> bool:
        # A method of objects outside the program only: an asyncio primitive, a string, a base past the program (super()).
        receivers = self._ev(fn, module, func.value) if isinstance(func, ast.Attribute) else _NO
        return bool(receivers) and all(v.kind in ("extinst", "str", "super") for v in receivers)

    def _implementers(self, cq: str) -> "list[str]":
        wanted = {n for n in self.classes[cq].methods if not n.startswith("__")}
        if not wanted:
            return []
        return sorted(k for k, c in self.classes.items() if not c.is_protocol and wanted <= {n for owner in self._mro_of[k] for n in self.classes[owner].methods})

    def _index_body(self, module: str, body: "list[ast.stmt]", prefix: str, cls: "_Cls | None", outer: "_Fn | None") -> None:
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = prefix + "." + stmt.name
                q = q if q not in self.fns else f"{q}@{stmt.lineno}"
                fn = _Fn(q, module, stmt, cls, outer)
                self.fns[q], self._by_node[stmt] = fn, q
                if cls is None and outer is None:
                    self._symbols[module].setdefault(stmt.name, set()).add(("func", q))
                if cls is not None:
                    cls.methods.setdefault(stmt.name, []).append(fn)
                self._index_body(module, stmt.body, q, None, fn)
            elif isinstance(stmt, ast.ClassDef):
                c = _Cls(prefix + "." + stmt.name, module, stmt)
                self.classes[c.q] = c
                if cls is None and outer is None:
                    self._symbols[module].setdefault(stmt.name, set()).add(("cls", c.q))
                self._index_body(module, stmt.body, c.q, c, outer)
            elif cls is None and outer is None:
                self._index_module_stmt(module, stmt)
            elif outer is not None:
                for block in _blocks(stmt):
                    self._index_body(module, block, prefix, None, outer)

    def _index_module_stmt(self, module: str, stmt: ast.stmt) -> None:
        symbols = self._symbols[module]
        if isinstance(stmt, ast.Import):
            for a in stmt.names:
                symbols.setdefault(a.asname or a.name.split(".")[0], set()).add(("mod", a.name if a.asname else a.name.split(".")[0]))
        elif isinstance(stmt, ast.ImportFrom) and stmt.module:
            for a in stmt.names:
                symbols.setdefault(a.asname or a.name, set()).add(("imp", stmt.module, a.name))
        elif isinstance(stmt, (ast.If, ast.Try)):
            for block in _blocks(stmt):
                self._index_body(module, block, module, None, None)
        elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            self._aliases[module][stmt.targets[0].id] = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            self._aliases[module][stmt.target.id] = stmt.value

    def _label(self, q: str, recv: str) -> str:
        # module.function, Class.method, or Receiver(Owner).method for a method the receiver inherits.
        fn = self.fns[q]
        if fn.cls is None:
            return q.partition("@")[0]
        owner = fn.cls.q.split(".", 1)[1]
        if recv and recv != fn.cls.q and recv in self.classes:
            return f"{recv.split('.', 1)[1]}({owner}).{fn.node.name}"
        return f"{owner}.{fn.node.name}"

    def _lookup(self, fn: "_Fn | None", module: str, name: str, recv: str) -> frozenset[V]:
        if fn is not None and recv and name == fn.self_name:
            return frozenset({V("exact", recv)})
        scope = fn
        while scope is not None and name not in scope.globals_declared:
            env = self._locals.get(scope.q, {})
            if name in env:
                return env[name]
            scope = scope.outer
        return self._symbol(module, name)

    def _mark_tops(self, fn: "_Fn | None", module: str, arg: ast.expr) -> None:
        vals = self._ev(fn, module, arg)
        for v in vals | _elements(vals):
            if v.kind == "coro":
                self._add_top(v.name)

    def _merged(self, cur: frozenset[V], vals: "Iterable[V]") -> "frozenset[V] | None":
        # The store's new value set, or None when nothing is new (a frozen program records nothing).
        new = frozenset(vals)
        if self._frozen or not new or new <= cur:
            return None
        fresh = new - cur  # a store is normalized already, so new plain values join it as they are
        merged = _normalized(cur | new) if any(v.kind in ("seq", "tup") for v in fresh) else cur | fresh
        if merged == cur:
            return None
        self._changed = True
        return merged

    def _method_defs(self, cq: str, name: str) -> "list[_Fn]":
        out: list[_Fn] = []
        for k in self._concrete(cq):
            out.extend(d for d in self._definer(k, name) if d not in out)
        return out

    def _mro(self, q: str) -> "list[str]":
        return self._mro_of.get(q, [q])

    def _names_of(self, fn: _Fn) -> "set[str]":
        # The names a call to fn goes by: its own, and for an __init__ each class whose construction runs it.
        names = {fn.node.name}
        if fn.cls is not None and fn.node.name == "__init__":
            names |= {self.classes[k].node.name for k in [fn.cls.q, *self._subclasses_of[fn.cls.q]] if fn in self._definer(k, "__init__")}
        return names

    def _open_by_value(self) -> None:
        # Once the first pass has bound every call it can: open each function a value, a string or an unbound call names,
        # at once rather than at the first fixpoint, since that never changes.
        by_value = _value_names(self.modules.values(), self._bound_calls)
        opened = {q for q, f in self.fns.items() if not by_value.isdisjoint(self._names_of(f))} - self._open
        self._open |= opened
        self._changed = self._changed or bool(opened)

    def _open_unbound(self) -> bool:
        # At a fixpoint, open every function never called here, called partly bound or named by an unresolved call, and
        # each parameter a loose argument fills; True when one opened, so the passes go on.
        unresolved = self._unresolved
        opened = {q for q, f in self.fns.items() if q not in self._called or q in self._partial or not unresolved.isdisjoint(self._names_of(f))}
        opened -= self._open
        loose = self._loose - self._open_params
        self._open |= opened
        self._open_params |= loose
        return bool(opened or loose)

    def _receivers(self, q: str) -> "list[str]":
        # The exact classes a method runs on: each constructed class whose lookup of its name reaches it ("" for a plain
        # function).
        fn = self.fns[q]
        if fn.cls is None or not fn.self_name:
            return [""]
        reaching = [k for k in [fn.cls.q, *sorted(self._subclasses_of[fn.cls.q])] if fn in self._definer(k, fn.node.name)]
        return [k for k in reaching if k in self._constructed] or reaching or [""]

    def _register_handler(self, fn: "_Fn | None", module: str, call: ast.Call) -> None:
        # Microdot's registration, app.get(path)(handler): every registered handler reaches invoke_handler().
        if not isinstance(call.func, ast.Call):
            return
        for v in self._ev(fn, module, call.func.func):
            owners = [v.name] if v.kind == "emeth" else self._concrete(v.name) if v.kind == "meth" else []
            if _MICRODOT in owners and v.attr in _ROUTE_REGISTRARS | _ERROR_REGISTRARS:
                self._add(self._handlers, "errors" if v.attr in _ERROR_REGISTRARS else "routes", self._ev(fn, module, call.args[0]))

    def _run_function(self, fn: _Fn) -> None:
        args = fn.node.args
        env = self._locals.setdefault(fn.q, {})
        params = args.posonlyargs + args.args + args.kwonlyargs + [a for a in (args.vararg, args.kwarg) if a is not None]
        for i, p in enumerate(params):
            if fn.cls is not None and p.arg == fn.self_name:
                self._add(env, p.arg, {V("inst", fn.cls.q)})
            elif fn.cls is not None and i == 0 and fn.is_classmethod:
                self._add(env, p.arg, {V("subcls", fn.cls.q)})
            elif fn.q in self._open or (fn.q, p.arg) in self._open_params:
                self._add(env, p.arg, self._annotation(fn.module, p.annotation))
        positional = args.posonlyargs + args.args
        defaults = list(zip(positional[len(positional) - len(args.defaults) :], args.defaults, strict=True))
        defaults += [(k, d) for k, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d is not None]
        for p, default in defaults:  # evaluated where the def stands, filling a parameter its call leaves out
            self._bind_arg(fn.q, env, p.arg, fn.outer, fn.module, default)
        for stmt in fn.node.body:
            self._run_stmt(fn, fn.module, stmt)
        returns = fn.node.returns
        if fn.cls is not None and fn.node.name in ("__aenter__", "__enter__") and returns is not None:
            named_self = (returns.value if isinstance(returns, ast.Constant) else ast.unparse(returns)) == "Self"
            self._add(self._returns, fn.q, {V("inst", fn.cls.q)} if named_self else self._annotation(fn.module, returns))

    def _run_stmt(self, fn: "_Fn | None", module: str, stmt: ast.stmt) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if fn is not None:
                self._add(self._locals.setdefault(fn.q, {}), stmt.name, {V("func", self._by_node[stmt])})
            return
        if isinstance(stmt, ast.ClassDef):
            return
        calls, children = self._stmt_parts(stmt)
        for call in calls:
            self._bind_call(fn, module, call)
        if isinstance(stmt, ast.Assign):
            vals = self._ev(fn, module, stmt.value)
            for target in stmt.targets:
                self._bind(fn, module, target, vals)
        elif isinstance(stmt, ast.AnnAssign):
            self._bind(fn, module, stmt.target, self._ev(fn, module, stmt.value) | self._annotation(module, stmt.annotation))
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            self._bind(fn, module, stmt.target, _elements(self._ev(fn, module, stmt.iter)))
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            self._run_with(fn, module, stmt)
        elif isinstance(stmt, ast.Return) and fn is not None and stmt.value is not None:
            self._add(self._returns, fn.q, self._ev(fn, module, stmt.value))
        for child in children:
            self._run_stmt(fn, module, child)

    def _run_with(self, fn: "_Fn | None", module: str, stmt: "ast.With | ast.AsyncWith") -> None:
        enter = "__aenter__" if isinstance(stmt, ast.AsyncWith) else "__enter__"
        for item in stmt.items:
            if item.optional_vars is not None:
                managers = self._ev(fn, module, item.context_expr)
                defs = [d for v in managers for d in (self._definer(v.name, enter) if v.kind == "exact" else self._method_defs(v.name, enter) if v.kind == "inst" else [])]
                self._bind(fn, module, item.optional_vars, frozenset().union(*(self._returns.get(d.q, _NO) for d in defs)))

    def _site_targets(self, fn: _Fn, kind: str, node: ast.expr, recv: str) -> "tuple[frozenset[Key], int]":
        # One await site's continuations (an awaited coroutine, an async with/for's dunder methods) and the frames
        # asyncio's own awaitable at it re-enters, at least the one level the site counts by itself.
        targets: set[Key] = set()
        external = 0
        for v in self._ev(fn, fn.module, node, recv):
            if kind == "await" and v.kind == "coro":
                targets |= {(v.name, r) for r in ([v.recv] if v.recv else self._receivers(v.name))}
            elif kind == "await" and v.kind == "extcoro":
                external = max(external, v.depth)
            elif kind == "with" and v.kind == "extinst":
                external = max(external, _ASYNCIO_WITH_DEPTH.get(v.name, 1))
            elif kind != "await" and v.kind in ("inst", "exact"):
                dunders = ("__aenter__", "__aexit__") if kind == "with" else ("__anext__",)
                for k in [v.name] if v.kind == "exact" else self._concrete(v.name):
                    targets |= {(d.q, k) for name in dunders for d in self._definer(k, name) if d.is_async}
        context = "errors" if fn.q == _ERROR_RESPONSE else "all"
        return frozenset((q, context) if q.partition("@")[0] == _INVOKE else (q, r) for q, r in targets), max(external, 1)

    def _sites(self, key: Key) -> "tuple[tuple[frozenset[Key], int], ...]":
        # Each await site of key's function as (continuations, the site's own depth); Microdot's invoke_handler(), one
        # frame awaiting the handler it is given in both of its definitions, as one site that counts nothing by itself.
        if key not in self._site_cache:
            q, recv = key
            if recv in ("errors", "all"):
                handlers = self._handlers.get("errors", _NO) | (self._handlers.get("routes", _NO) if recv == "all" else _NO)
                self._site_cache[key] = ((frozenset((d.q, r) for d in self._callables(handlers) if d.is_async for r in self._receivers(d.q)), 0),)
            else:
                fn = self.fns[q]
                self._site_cache[key] = tuple(self._site_targets(fn, kind, node, recv) for kind, node in _await_sites(fn.node))
        return self._site_cache[key]

    def _stmt_parts(self, stmt: ast.stmt) -> "tuple[list[ast.Call], list[ast.stmt]]":
        # A statement's own calls and its nested statements, walked once for all the passes.
        parts = self._parts.get(stmt)
        if parts is None:
            parts = self._parts[stmt] = (_own_calls(stmt), list(_child_stmts(stmt)))
        return parts

    def _symbol(self, module: str, name: str, depth: int = 0) -> frozenset[V]:
        out: set[V] = set()
        for entry in self._symbols.get(module, {}).get(name, ()):
            if entry[0] == "imp":
                source, attr = entry[1], entry[2]
                inside = source in self.modules and depth < _MAX_NESTING * 2
                out |= self._symbol(source, attr, depth + 1) if inside else {V("ext", f"{source}.{attr}")}
            elif entry[0] == "mod":
                out.add(V("mod", entry[1]) if entry[1] in self.modules else V("ext", entry[1]))
            else:
                out.add(V(entry[0], entry[1]))
        return frozenset(out) | self._locals.get("<module>." + module, {}).get(name, _NO)

    def _symbol_expr(self, module: str, expr: ast.expr) -> "set[tuple[str, ...]]":
        if isinstance(expr, ast.Name):
            return {(v.kind, v.name) for v in self._symbol(module, expr.id)}
        if isinstance(expr, ast.Attribute):
            inner = self._symbol_expr(module, expr.value)
            return {(v.kind, v.name) for kind, name in inner if kind == "mod" for v in self._symbol(name, expr.attr)}
        return set()

    def _tarjan(self, key: Key, index: "dict[Key, int]", path: "list[Key]") -> int:
        # Tarjan's walk from key: each component found is recorded for all its keys; returns key's lowest reachable index.
        index[key] = low = len(index)
        path.append(key)
        for targets, _floor in self._sites(key):
            for child in sorted(targets):
                if child not in self._components:  # a finished component holds no key of this one
                    low = min(low, self._tarjan(child, index, path) if child not in index else index[child])
        if low == index[key]:
            members = frozenset(path[path.index(key) :])
            del path[path.index(key) :]
            self._components.update(dict.fromkeys(members, members))
        return low

    def chains(self) -> "list[Chain]":
        # Every task top's longest chain, deepest first; a method top once per exact class it runs on.
        self._memo, self._components, self._site_cache = {}, {}, {}
        found = [self._chain_of(q, r, ()) for q in sorted(self.tops) for r in self._receivers(q)]
        return sorted(found, key=lambda c: (-c.depth, c.path))

    def solve(self) -> int:
        # The value flow to its fixpoint: module code, then every function, until a pass changes nothing and opens no
        # parameter to its annotation (the records it decides on are the pass's own, so a fixpoint's are final).
        for n in range(1, _MAX_PASSES + 1):
            self._changed = False
            self._called, self._partial, self._unresolved, self._loose = set(), set(), set(), set()
            for module, tree in self.modules.items():
                for stmt in tree.body:
                    self._run_stmt(None, module, stmt)
            for fn in self.fns.values():
                self._run_function(fn)
            if n == 1:
                self._open_by_value()
            if not self._changed and not self._open_unbound():
                self._frozen = True
                return n
        msg = f"the value flow did not settle in {_MAX_PASSES} passes"
        raise RuntimeError(msg)


def _await_sites(node: Function) -> "list[tuple[str, ast.expr]]":
    # A function's own await expressions and async with/for headers, never a nested function's.
    out: list[tuple[str, ast.expr]] = []
    stack: list[ast.AST] = list(node.body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(n, ast.Await):
            out.append(("await", n.value))
        elif isinstance(n, ast.AsyncWith):
            out.extend(("with", item.context_expr) for item in n.items)
        elif isinstance(n, ast.AsyncFor):
            out.append(("for", n.iter))
        stack.extend(ast.iter_child_nodes(n))
    return out


def _blocks(stmt: ast.stmt) -> "list[list[ast.stmt]]":
    blocks = [block for f in ("body", "orelse", "finalbody") if isinstance(block := getattr(stmt, f, None), list)]
    return blocks + [h.body for h in getattr(stmt, "handlers", [])]


def _callee_name(func: ast.expr) -> str:
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def _child_stmts(stmt: ast.stmt) -> "Iterator[ast.stmt]":
    for block in _blocks(stmt):
        yield from block


def _container_call(v: V) -> frozenset[V]:
    if v.attr in ("values", "keys", "copy"):
        return _seq(_elements(v.inner))
    if v.attr == "items":
        return _normalized({V("seq", inner=frozenset({V("tup", parts=(_NO, _elements(v.inner)))}))})
    if v.attr in ("get", "pop"):
        return _elements(v.inner)
    return _NO


def _deeper(a: Chain, b: Chain) -> Chain:
    # The deeper chain; on a tie the alphabetically first path, so the reported chain is stable.
    if a.depth != b.depth:
        return a if a.depth > b.depth else b
    return a if a.path <= b.path else b


def _elements(vals: "Iterable[V]") -> frozenset[V]:
    out: set[V] = set()
    for v in vals:
        if v.kind == "seq":
            out |= v.inner
        elif v.kind == "tup":
            for part in v.parts:
                out |= part
    return frozenset(out)


def _linearized(q: str, classes: "dict[str, _Cls]", depth: int = 0) -> "list[str]":
    out = [q]
    for base in classes[q].bases if depth < _MAX_PASSES else []:
        out.extend(x for x in _linearized(base, classes, depth + 1) if x not in out)
    return out


def _normalized(vals: "Iterable[V]", nesting: int = 0) -> frozenset[V]:
    # One sequence value and one tuple value per arity, their element sets merged, nesting cut at _MAX_NESTING.
    seq: set[V] | None = None
    tups: dict[int, list[set[V]]] = {}
    out: set[V] = set()
    for v in vals:
        if v.kind == "seq":
            seq = (seq or set()) | v.inner
        elif v.kind == "tup":
            for slot, part in zip(tups.setdefault(len(v.parts), [set() for _ in v.parts]), v.parts, strict=True):
                slot.update(part)
        else:
            out.add(v)
    if nesting < _MAX_NESTING:
        if seq is not None:
            out.add(V("seq", inner=_normalized(seq, nesting + 1)))
        out |= {V("tup", parts=tuple(_normalized(p, nesting + 1) for p in parts)) for parts in tups.values()}
    return frozenset(out)


def _own_calls(stmt: ast.stmt) -> "list[ast.Call]":
    # The calls in a statement's own expressions, never in its nested statements or a lambda.
    out: list[ast.Call] = []
    stack = [c for c in ast.iter_child_nodes(stmt) if not isinstance(c, ast.stmt)]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Lambda):
            continue
        if isinstance(n, ast.Call):
            out.append(n)
        stack.extend(c for c in ast.iter_child_nodes(n) if not isinstance(c, ast.stmt))
    return out


def _seq(vals: "Iterable[V]") -> frozenset[V]:
    return _normalized({V("seq", inner=frozenset(vals))})


def _value_names(trees: "Iterable[ast.Module]", bound: "set[ast.Call]") -> "set[str]":
    # The names a function or class may be reached by other than a call the walk binds: a reference that is no callee
    # (annotations aside), any string (getattr()), the callee of a call never bound or bound inside a comprehension.
    out: set[str] = set()
    stack: list[tuple[ast.AST, bool]] = [(tree, True) for tree in trees]
    while stack:
        node, binds = stack.pop()
        children = [c for c in ast.iter_child_nodes(node) if not isinstance(c, ast.arg)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            children = [c for c in children if c is not node.returns]
        elif isinstance(node, ast.ClassDef):  # a base is no value: its __init__ runs through the subclass's names
            children = [c for c in children if all(c is not b for b in node.bases)]
        elif isinstance(node, ast.AnnAssign):
            children = [c for c in (node.target, node.value) if c is not None]
        elif isinstance(node, ast.Call):
            if not (binds and node in bound):
                out.add(_callee_name(node.func))
            if isinstance(node.func, (ast.Name, ast.Attribute)):
                children = [c for c in children if c is not node.func] + ([node.func.value] if isinstance(node.func, ast.Attribute) else [])
        elif isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load):
            out.add(node.id if isinstance(node, ast.Name) else node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.add(node.value)
        inner = binds and not isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
        stack.extend((c, inner) for c in children)
    return out


def load_program(repo_root: Path, devices: "Iterable[str]") -> Program:
    # src/ and ext/microdot.py from disk, each device's module and boot entry generated in memory; only src/ and the
    # generated code start chains (Microdot's own server is not the one the firmware runs).
    modules = {p.stem: ast.parse(p.read_text(encoding="utf-8")) for p in sorted((repo_root / "src").glob("*.py"))}
    tops = set(modules)
    modules["microdot"] = ast.parse((repo_root / "ext" / "microdot.py").read_text(encoding="utf-8"))
    for device in devices:
        result = generate_device(repo_root / "devices" / f"{device}.toml", repo_root / "src", repo_root / "ext")
        for name, source in ((f"sensortask_{device}", result.module_source), (f"sensortask_{device}_main", result.boot_entry_source)):
            modules[name] = ast.parse(source)
            tops.add(name)
    return Program(modules, tops)


def program_from_sources(sources: "dict[str, str]") -> Program:
    # A fabricated program for the checks' own bites: every module given starts chains.
    return Program({name: ast.parse(source) for name, source in sources.items()}, set(sources))

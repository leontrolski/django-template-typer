from __future__ import annotations

import pathlib
from collections.abc import Callable, Iterable
from dataclasses import KW_ONLY, dataclass, field
from functools import cache
from typing import NewType, assert_never

from django.template import smartif

from django_template_typer import dtt, parser, typing

Line = NewType("Line", str)


@dataclass
class _Node:
    _: KW_ONLY
    source_line: Line = Line("<missing>")


@dataclass
class Noop(_Node): ...


@dataclass
class Name(_Node):
    name: str
    scope_ref: typing.ScopeRef
    path: typing.Path

    @property
    def is_top_level(self) -> bool:
        return self.path == tuple(self.name.split("."))


@dataclass
class Literal(_Node):
    value: parser.LiteralValue


@dataclass
class Call(_Node):
    f: Signature
    args: list[Expr]
    kwargs: dict[str, Expr]


@dataclass
class For(_Node):
    scope: parser.Lineno
    elts: list[str]
    iter: Expr
    body: list[Statement]


@dataclass
class If(_Node):
    conditions: list[tuple[Expr | None, list[Statement]]]


@dataclass
class WithClosing(_Node):
    contextmanager: Expr
    body: list[Statement]


@dataclass
class UseBlock(_Node):
    extends_path: pathlib.Path
    name: str
    body: list[Statement]


@dataclass
class DefineBlock(_Node):
    body: list[Statement]


@dataclass
class Include(_Node):
    name: str
    kwargs: dict[str, Expr]


@dataclass
class WithAssignments(_Node):
    i: int
    scope: parser.Lineno
    assignments: list[tuple[str, Expr]]
    body: list[Statement]


Expr = Name | Literal | Call
Statement = (
    Noop
    | Expr
    | For
    | If
    | WithClosing
    | UseBlock
    | DefineBlock
    | Include
    | WithAssignments
)


@dataclass
class Extends:
    source: pathlib.Path
    blocks: set[str]
    extends: Extends | None


@dataclass
class ArgsDict:
    _by_name: dict[str, typing.InferredType] = field(default_factory=dict)
    _var_positional: typing.InferredType = typing.InferredType(dtt.Unknown)
    _var_keyword: typing.InferredType = typing.InferredType(dtt.Unknown)

    def by_key(self, key: str | int) -> typing.InferredType:
        if isinstance(key, int):
            if key >= len(self._by_name):
                return self._var_positional
            return list(self._by_name.values())[key]
        return self._by_name.get(key, self._var_keyword)


@dataclass
class Signature:
    name: str
    namespaced_name: str
    t_args: ArgsDict
    t_return: object

    def __hash__(self) -> int:
        return hash(self.namespaced_name)


def _name_to_path(name: str) -> typing.Path:
    return tuple(name.split("."))


@dataclass(kw_only=True)
class Context:
    template_dirs: tuple[pathlib.Path, ...]
    source: pathlib.Path | str
    signatures: tuple[Signature, ...]

    # The following get mutated over the course of resolving
    extends: Extends | None = None
    load: list[str] = field(default_factory=list)
    blocks: set[str] = field(default_factory=set)
    includes: set[str] = field(default_factory=set)

    scopes: typing.Scopes = field(default_factory=typing.Scopes)
    types: typing.InferredTypes = field(default_factory=set)

    _i: int = -1

    def add_type(self, node: Name, t: typing.InferredType) -> None:
        if isinstance(node.scope_ref, typing.ScopeRefIfTruthy):
            t = typing.InferredType(t.t | None)  # type: ignore
        self.types.add((node.path, t))

    @property
    def i(self) -> int:
        self._i += 1
        return self._i


def resolve_expr(context: Context, node: parser.Expr) -> Expr:
    if isinstance(node, parser.Name):
        return Name(node.name, *context.scopes.resolve(_name_to_path(node.name)))
    if isinstance(node, parser.Literal):
        return Literal(node.value)
    if isinstance(node, parser.Call):
        args = list[Expr]()
        kwargs = dict[str, Expr]()
        for i, arg_ in enumerate(node.args):
            args.append(resolve_expr(context, arg_))
        for k, arg_ in node.kwargs.items():
            kwargs[k] = resolve_expr(context, arg_)

        sig = _signature_by_name(context.signatures, node.f_name)
        for i, arg in enumerate(args):
            if isinstance(arg, Name):
                context.add_type(arg, sig.t_args.by_key(i))
        for k, arg in kwargs.items():
            if isinstance(arg, Name):
                context.add_type(arg, sig.t_args.by_key(k))

        return Call(sig, args, kwargs)

    assert_never(node)


def resolve_predicate(context: Context, predicate: parser.Predicate) -> Expr:
    if isinstance(predicate, parser.UnaryOp | parser.BinaryOp):
        if isinstance(predicate, parser.UnaryOp):
            args_ = [predicate.first]
        else:
            args_ = [predicate.first, predicate.second]
        args = [resolve_predicate(context, arg) for arg in args_]
        sig = _signature_by_name(context.signatures, OPERATORS[predicate.op].__name__)
        for i, arg in enumerate(args):
            if isinstance(arg, Name):
                context.add_type(arg, sig.t_args.by_key(i))
        return Call(sig, args, {})

    return resolve_expr(context, predicate.to_expr())


def resolve_statement(context: Context, node: parser.Node) -> Statement:
    if isinstance(node, parser.TextNode):
        return Noop()
    if isinstance(node, parser.ExprNode):
        return resolve_expr(context, parser.Call("render", [node.value.to_expr()], {}))
    if isinstance(node, parser.ForNode):
        elts = [elt.name for elt in node.elts]
        iter = resolve_expr(context, node.iter.to_expr())

        if isinstance(iter, Name):
            for i, elt in enumerate(node.elts):
                context.scopes.add(
                    node.lineno,
                    _name_to_path(elt.name),
                    _name_to_path(iter.name)
                    + ((typing.ITER,) if len(elts) == 1 else (typing.ITER, i)),
                )

        with context.scopes.push(node.lineno):
            if isinstance(iter, Name):
                for elt in node.elts:
                    elt_name = Name(
                        elt.name, *context.scopes.resolve(_name_to_path(elt.name))
                    )
                    context.add_type(elt_name, typing.InferredType(object))
            statements = resolve_statements(context, node.children)

        return For(node.lineno, elts, iter, statements)
    if isinstance(node, parser.IfNode):
        if_ = If([])
        for i, (predicate_, statements_) in enumerate(node.conditions):
            predicate = None
            if predicate_ is not None:
                predicate = resolve_predicate(context, predicate_)
            scope_ref = typing.ScopeRefIfTruthy((node.lineno, i))
            with context.scopes.push(scope_ref):
                if isinstance(predicate, Name):
                    context.scopes.add(
                        scope_ref,
                        _name_to_path(predicate.name),
                        _name_to_path(predicate.name),
                    )
                    context.add_type(predicate, typing.InferredType(object))
                statements = resolve_statements(context, statements_)
            if_.conditions.append((predicate, statements))
        return if_
    if isinstance(node, parser.TagNode):
        if node.name == "load":
            for arg in node.args:
                assert isinstance(arg.var, parser.Name)
                context.load.append(arg.var.name)
            return Noop()
        if node.name == "extends":
            [arg] = node.args
            assert isinstance(arg.var, parser.Literal)
            assert isinstance(arg.var.value, str)
            context.extends = _parse_and_load_extends(context, arg.var.value)
            return Noop()
        if node.name == "block":
            [arg] = node.args
            assert isinstance(arg.var, parser.Name)
            name = arg.var.name
            if extends_path := _block_exists_in_ancestor(context, name):
                return UseBlock(
                    extends_path,
                    name,
                    resolve_statements(context, node.children),
                )
            context.blocks.add(name)
            return DefineBlock(resolve_statements(context, node.children))
        if node.name == "with":
            assignments = list[tuple[str, Expr]]()
            assert not node.args
            assert not node.pre_bools
            assert not node.post_bools
            for name, arg in node.kwargs.items():
                arg_expr = resolve_expr(context, arg.to_expr())
                assignments.append((name, arg_expr))
                if isinstance(arg_expr, Name):
                    context.scopes.add(
                        node.lineno,
                        _name_to_path(name),
                        _name_to_path(arg_expr.name),
                    )

            with context.scopes.push(node.lineno):
                statements = resolve_statements(context, node.children)

            return WithAssignments(context.i, node.lineno, assignments, statements)
        if node.name == "include":
            [arg] = node.args
            assert not arg.filters
            assert isinstance(arg.var, parser.Literal)
            assert isinstance(arg.var.value, str)
            if node.post_bools != [parser.Name("only")]:
                raise RuntimeError(
                    "Expected 'only' - like {% include 'blah.html' with a=1 only %}"
                )
            context.includes.add(arg.var.value)
            return Include(
                arg.var.value,
                {k: resolve_expr(context, v.to_expr()) for k, v in node.kwargs.items()},
            )
        call = resolve_expr(
            context,
            parser.Call(
                node.name,
                [arg.to_expr() for arg in node.args],
                {k: v.to_expr() for k, v in node.kwargs_with_bools.items()},
            ),
        )
        if node.with_closing:
            return WithClosing(call, resolve_statements(context, node.children))
        return call

    assert_never(node)


def resolve_statements(
    context: Context, nodes: Iterable[parser.Node]
) -> list[Statement]:
    out = list[Statement]()
    for node in nodes:
        source_line = Line(_source_lines(context.source)[node.lineno - 1].strip())
        statement = resolve_statement(context, node)
        statement.source_line = source_line
        out.append(statement)
    return out


# Helpers


OPERATORS: dict[str, Callable[..., object]] = {
    "not": dtt._not,  # Unary
    "or": dtt._or,
    "and": dtt._and,
    "in": dtt._in,
    "not in": dtt._not_in,
    "is": dtt._is,
    "is not": dtt._is_not,
    "==": dtt._eq,
    "!=": dtt._neq,
    ">": dtt._gt,
    ">=": dtt._gte,
    "<": dtt._lt,
    "<=": dtt._lte,
}
assert OPERATORS.keys() == smartif.OPERATORS.keys()


@cache
def _signature_by_name(signatures: tuple[Signature, ...], f_name: str) -> Signature:
    for s in signatures:
        if s.name == f_name:
            return s
    raise RuntimeError(f"No function registered with name: {f_name}")


@cache
def _find_template(template_dirs: tuple[pathlib.Path, ...], name: str) -> pathlib.Path:
    for dir in template_dirs:
        if (dir / name).exists():
            return dir / name
    raise RuntimeError(f"Could not find {name} in template dirs")


def _parse_and_load_extends(existing_context: Context, name: str) -> Extends:
    source = _find_template(existing_context.template_dirs, name)
    root = parser.parse_template(source)
    context = Context(
        template_dirs=existing_context.template_dirs,
        source=source,
        signatures=existing_context.signatures,
    )
    resolve_statements(context, root.children)
    return Extends(source, context.blocks, context.extends)


def _block_exists_in_ancestor(
    context: Context | Extends | None, name: str
) -> pathlib.Path | None:
    if context is None:
        return None
    if name in context.blocks:
        assert isinstance(context.source, pathlib.Path)
        return context.source
    return _block_exists_in_ancestor(context.extends, name)


@cache
def _source_lines(source: pathlib.Path | str) -> list[str]:
    if isinstance(source, pathlib.Path):
        source = source.read_text()
    return source.splitlines()

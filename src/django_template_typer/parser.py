from __future__ import annotations

import itertools
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import NewType

from django.template import base, defaulttags, engine, smartif

from django_template_typer import django_patched

LiteralValue = NewType("LiteralValue", object)
Lineno = NewType("Lineno", int)


@dataclass(kw_only=True)
class _Node:
    lineno: Lineno = Lineno(1)
    children: tuple[Node, ...] = ()


@dataclass(kw_only=True)
class RootNode(_Node):
    source: str | Path

    def to_str(self) -> str:
        return "".join(c.to_str() for c in self.children)


@dataclass
class Name:
    name: str

    def to_str(self) -> str:
        return self.name


@dataclass
class Literal:
    value: LiteralValue

    def to_str(self) -> str:
        return repr(self.value)


@dataclass
class Filter:
    var: Name
    arg: Name | Literal | None

    def to_str(self) -> str:
        if self.arg is None:
            return self.var.to_str()
        return f"{self.var.to_str()}:{self.arg.to_str()}"


@dataclass
class FilterExpression:
    var: Name | Literal
    filters: list[Filter] = field(default_factory=list)

    def to_str(self) -> str:
        if not self.filters:
            return self.var.to_str()
        return f"{self.var.to_str()}|{'|'.join(n.to_str() for n in self.filters)}"

    def to_expr(self) -> Expr:
        value: Expr = self.var
        for filter in self.filters:
            value = Call(
                filter.var.name,
                [value] if filter.arg is None else [value, filter.arg],
                {},
            )
        return value


@dataclass(kw_only=True)
class TextNode(_Node):
    s: str

    def to_str(self) -> str:
        return self.s


@dataclass(kw_only=True)
class ExprNode(_Node):
    value: FilterExpression

    def to_str(self) -> str:
        return f"{{{{ {self.value.to_str()} }}}}"


@dataclass(kw_only=True)
class ForNode(_Node):
    elts: list[Name]
    iter: FilterExpression

    def to_str(self) -> str:
        return (
            f"{{% for {', '.join(l.to_str() for l in self.elts)} in {self.iter.to_str()} %}}"
            + "".join(c.to_str() for c in self.children)
            + "{% endfor %}"
        )


@dataclass(kw_only=True)
class IfNode(_Node):
    conditions: list[tuple[Predicate | None, list[Node]]]

    def to_str(self) -> str:
        ifs = itertools.chain(iter(["if"]), itertools.cycle(iter(["elif"])))
        s = ""
        for if_, [predicate, body] in zip(ifs, self.conditions):
            if predicate is None:
                s += "{% else %}"
            else:
                s += f"{{% {if_} {predicate.to_str()} %}}"
            for c in body:
                s += c.to_str()
        s += "{% endif %}"
        return s


def _join(args: Iterator[str]) -> str:
    return "".join(" " + arg for arg in args)


@dataclass(kw_only=True)
class TagNode(_Node):
    name: str
    args: list[FilterExpression]
    kwargs: dict[str, FilterExpression]
    pre_bools: list[Name] = field(default_factory=list)
    post_bools: list[Name] = field(default_factory=list)
    with_closing: bool = False

    @property
    def kwargs_with_bools(self) -> dict[str, FilterExpression]:
        kwargs = self.kwargs
        for b in self.pre_bools + self.post_bools:
            kwargs[b.name] = FilterExpression(Literal(LiteralValue(True)))
        return kwargs

    def to_str(self) -> str:
        args = _join(n.to_str() for n in self.args)
        kwargs = _join(f"{k}={n.to_str()}" for k, n in self.kwargs.items())
        pre_bools = _join(n.to_str() for n in self.pre_bools)
        post_bools = _join(n.to_str() for n in self.post_bools)
        s = f"{{% {self.name}{args}{pre_bools}{kwargs}{post_bools} %}}"
        s += "".join(c.to_str() for c in self.children)
        if self.with_closing:
            s += f"{{% end{self.name} %}}"
        return s


Node = TextNode | ExprNode | ForNode | IfNode | TagNode


def parse_template(source: str | Path) -> RootNode:
    source_str = source
    if isinstance(source_str, Path):
        source_str = source_str.read_text()
    t = django_patched.Template(source_str, engine=engine.Engine())
    return RootNode(source=source, children=tuple(convert(n) for n in t.nodelist))


def _convert_variable(o: object) -> Name | Literal:
    if isinstance(o, base.Variable):
        if not isinstance(o.var, str):
            raise TypeError("Expected str")
        if o.literal is not None:
            return Literal(LiteralValue(o.literal))
        return Name(o.var)
    if not isinstance(o, str):
        raise TypeError("Expected str")
    return Literal(LiteralValue(o))


def _convert_filter_expression(f: base.FilterExpression | str) -> FilterExpression:
    if not isinstance(f, base.FilterExpression):
        raise TypeError("Expected FilterExpression")
    out = FilterExpression(filters=[], var=_convert_variable(f.var))
    for filter_callable, args in f.filters:
        if not isinstance(filter_callable, django_patched.Filter):
            raise TypeError("Expected Filter, are you using django_patched?")
        if not isinstance(filter_callable.name, str):
            raise TypeError("Expected str")
        filter = Filter(var=Name(filter_callable.name), arg=None)
        if len(args) not in (0, 1):
            raise TypeError("Expected 0 or 1 args to filter")
        for _, var in args:
            filter.arg = _convert_variable(var)
        out.filters.append(filter)
    return out


def convert(n: base.Node | str) -> Node:
    if isinstance(n, str):
        raise TypeError("Didn't expect to actually see a str, where is this from?")

    if n.token is None or n.token.lineno is None:
        raise RuntimeError("Expected node to have token with lineno")

    node: Node
    if isinstance(n, base.TextNode):
        node = TextNode(s=n.s)
    elif isinstance(n, base.VariableNode):
        node = ExprNode(value=_convert_filter_expression(n.filter_expression))
    elif isinstance(n, defaulttags.ForNode):
        node = ForNode(
            elts=[Name(n.loopvars)]
            if isinstance(n.loopvars, str)
            else [Name(m) for m in n.loopvars],
            iter=_convert_filter_expression(n.sequence),
        )
    elif isinstance(n, defaulttags.IfNode):
        n.child_nodelists = ()
        node = IfNode(conditions=[])
        for predicate, children in n.conditions_nodelists:
            node.conditions.append(
                (
                    None if predicate is None else _convert_predicate(predicate),
                    [convert(c) for c in children],
                )
            )
    elif isinstance(n, django_patched.Tag):
        node = TagNode(
            name=n.name,
            args=[_convert_filter_expression(m) for m in n.args],
            kwargs={k: _convert_filter_expression(m) for k, m in n.kwargs.items()},
            with_closing=isinstance(n, django_patched.TagWithClosing),
        )
        if node.name == "include":
            args = list(node.args)
            node.args = []
            for arg in args:
                if arg == FilterExpression(var=Name(name="with"), filters=[]):
                    node.pre_bools.append(Name(name="with"))
                elif arg == FilterExpression(var=Name(name="only"), filters=[]):
                    node.post_bools.append(Name(name="only"))
                else:
                    node.args.append(arg)
    else:
        raise TypeError(f"Unexpected node type: {type(n)}")

    node.lineno = Lineno(n.token.lineno)
    for attr in n.child_nodelists:
        node.children += tuple(convert(n) for n in getattr(n, attr))
    return node


# Predicates


@dataclass
class UnaryOp:
    op: str
    first: Predicate

    def to_str(self) -> str:
        return f"{self.op} {self.first.to_str()}"


@dataclass
class BinaryOp:
    op: str
    first: Predicate
    second: Predicate

    def to_str(self) -> str:
        return f"{self.first.to_str()} {self.op} {self.second.to_str()}"


Predicate = UnaryOp | BinaryOp | FilterExpression


def _convert_predicate(n: object) -> Predicate:
    if not isinstance(n, smartif.TokenBase):
        raise TypeError("Expected TokenBase")

    if isinstance(n, smartif.Literal):
        if not isinstance(n.value, base.FilterExpression):
            raise TypeError("Expected FilterExpression")
        return _convert_filter_expression(n.value)

    assert n.id in smartif.OPERATORS

    if n.second is None:
        return UnaryOp(n.id, _convert_predicate(n.first))

    return BinaryOp(n.id, _convert_predicate(n.first), _convert_predicate(n.second))


# Exprs


@dataclass
class Call:
    f_name: str
    args: list[Expr]
    kwargs: dict[str, Expr]


Expr = Name | Literal | Call

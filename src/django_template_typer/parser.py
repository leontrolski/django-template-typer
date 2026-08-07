from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path

from django.template import base, defaulttags, smartif

from django_template_typer import django_patched


@dataclass(kw_only=True)
class _Node:
    lineno: int | None = 1
    children: tuple[Node, ...] = ()


@dataclass(kw_only=True)
class RootNode(_Node):
    def to_str(self) -> str:
        return "".join(c.to_str() for c in self.children)


@dataclass
class Name:
    name: str

    def to_str(self) -> str:
        return self.name


@dataclass
class Literal:
    value: object

    def to_str(self) -> str:
        return repr(self.value)


@dataclass(kw_only=True)
class Filter:
    var: Name
    arg: Name | Literal | None

    def to_str(self) -> str:
        if self.arg is None:
            return self.var.to_str()
        return f"{self.var.to_str()}:{self.arg.to_str()}"


@dataclass(kw_only=True)
class FilterExpression:
    var: Name | Literal
    filters: list[Filter]

    def to_str(self) -> str:
        if not self.filters:
            return self.var.to_str()
        return f"{self.var.to_str()}|{'|'.join(n.to_str() for n in self.filters)}"


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
    conditions: list[tuple[Predicate, list[Node]]]

    def to_str(self) -> str:
        ifs = itertools.chain(iter(["if"]), itertools.cycle(iter(["elif"])))
        s = ""
        for if_, [predicate, body] in zip(ifs, self.conditions):
            s += f"{{% {if_} {predicate.to_str()} %}}"
            for c in body:
                s += c.to_str()
        s += "{% endif %}"
        return s


@dataclass
class IncludeSpecialArgs:
    with_: bool = False
    only: bool = False


@dataclass(kw_only=True)
class SimpleTagNode(_Node):
    name: str
    args: list[FilterExpression]
    kwargs: dict[str, FilterExpression]
    with_closing: bool
    include: IncludeSpecialArgs | None = None

    def to_str(self) -> str:
        args, kwargs = "", ""
        if self.args:
            args = " " + " ".join(n.to_str() for n in self.args)
        if self.kwargs:
            kwargs = " " + " ".join(f"{k}={n.to_str()}" for k, n in self.kwargs.items())
        with_ = " with" if self.include and self.include.with_ else ""
        only = " only" if self.include and self.include.only else ""
        s = f"{{% {self.name}{args}{with_}{kwargs}{only} %}}"
        if self.with_closing:
            s += "".join(c.to_str() for c in self.children)
            s += f"{{% end{self.name} %}}"
        return s


Node = TextNode | ExprNode | ForNode | IfNode | SimpleTagNode


def parse_template(template: str | Path) -> RootNode:
    if isinstance(template, Path):
        template = template.read_text()

    t = django_patched.Template(template)
    return RootNode(children=tuple(convert(n) for n in t.nodelist))


def _convert_variable(o: object) -> Name | Literal:
    if isinstance(o, base.Variable):
        if not isinstance(o.var, str):
            raise TypeError("Expected str")
        return Name(o.var)
    if not isinstance(o, str):
        raise TypeError("Expected str")
    return Literal(o)


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

    assert n.token is not None
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
        node = IfNode(conditions=[])
        for predicate, children in n.conditions_nodelists:
            node.conditions.append(
                (_convert_predicate(predicate), [convert(c) for c in children])
            )
    elif isinstance(n, django_patched.Tag):
        node = SimpleTagNode(
            name=n.name,
            args=[_convert_filter_expression(m) for m in n.args],
            kwargs={k: _convert_filter_expression(m) for k, m in n.kwargs.items()},
            with_closing=isinstance(n, django_patched.TagWithClosing),
        )
        if node.name == "include":
            node.include = IncludeSpecialArgs()
            args = list(node.args)
            node.args = []
            for arg in args:
                if arg == FilterExpression(var=Name(name="with"), filters=[]):
                    node.include.with_ = True
                elif arg == FilterExpression(var=Name(name="only"), filters=[]):
                    node.include.only = True
                else:
                    node.args.append(arg)
    else:
        raise TypeError(f"Unexpected node type: {type(n)}")

    node.lineno = n.token.lineno
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

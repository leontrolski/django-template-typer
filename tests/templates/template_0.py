"""Converted from tests/templates/template_0.html"""

from __future__ import annotations

import datetime
from collections import abc
from typing import TYPE_CHECKING, Protocol, TypedDict, Unpack

from django_template_typer import dtt
from tests.external import custom
from tests.templates import header
from tests.templates.sub import name_snippet


class Nested1(Protocol):
    @property
    def foo(self) -> dtt.Renderable | None: ...


class Nested3(Protocol):
    @property
    def foo(self) -> dtt.Renderable: ...


class Nested2(Protocol):
    @property
    def woo(
        self,
    ) -> abc.Iterable[
        dtt.Intersection[abc.Iterable[tuple[Nested3, object]], dtt.Renderable]
    ]: ...


class Nested5(Protocol):
    @property
    def count(self) -> str: ...


class Nested4(Protocol):
    @property
    def employees(self) -> Nested5: ...


class Context(Protocol, header.Context):
    @property
    def a(self) -> int: ...

    @property
    def b(self) -> int: ...

    @property
    def d(self) -> datetime.datetime: ...

    @property
    def g(self) -> Nested1: ...

    @property
    def l(self) -> Nested2: ...

    @property
    def business(self) -> Nested4: ...

    @property
    def p(self) -> float: ...

    @property
    def surname(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def q(self) -> float: ...

    @property
    def some_arg(self) -> object: ...

    @property
    def t(self) -> object: ...

    @property
    def create_date(self) -> datetime.datetime | datetime.time | datetime.date: ...

    @property
    def f(self) -> object: ...

    @property
    def e(self) -> dtt.Renderable: ...

    @property
    def some_kw_arg(self) -> object: ...


class ContextKwargs(TypedDict):
    a: int
    b: int
    d: datetime.datetime
    g: Nested1
    l: Nested2
    business: Nested4
    p: float
    surname: str
    name: str
    q: float
    some_arg: object
    t: object
    create_date: datetime.datetime | datetime.time | datetime.date
    f: object
    e: dtt.Renderable
    some_kw_arg: object


def render(context: Context) -> None:
    """Function that demonstrates the context type is sufficient for rendering."""
    if TYPE_CHECKING:
        "{% block title %}"
        with header.title():
            "{{ a }}"
            dtt.render(context.a)
        "Hi {{ name|brrp }} {{ surname|arg:1 }}"
        dtt.render(custom.brrp(context.name))
        "Hi {{ name|brrp }} {{ surname|arg:1 }}"
        dtt.render(custom.arg(context.surname, 1))
        "{% for x in l.woo %}"
        for x in context.l.woo:
            "{{ x }}"
            dtt.render(x)
            "{% for y, z in x %}"
            for y, z in x:
                "{{ y.foo }}"
                dtt.render(y.foo)
        "{{ a|f:b|g:'c'|h:1 }}"
        dtt.render(custom.h(custom.g(custom.f(context.a, context.b), "c"), 1))
        "{% custom_tag p q r=d %} more args here"
        custom.custom_tag(context.p, context.q, r=context.d)
        "{% if e or not f %}"
        if dtt._or(context.e, dtt._not(context.f)):
            ...
        elif context.g.foo:
            "{{ g.foo }}"
            dtt.render(context.g.foo)
        else:
            "{{ e }}"
            dtt.render(context.e)
        "{% url 'some-url-name' t some_arg u=1 v=some_kw_arg %}"
        dtt.url(
            "some-url-name", context.t, context.some_arg, u=1, v=context.some_kw_arg
        )
        "{% csrf_token %}"
        dtt.csrf_token()
        "{% comment 'Optional note' %}"
        with dtt.comment("Optional note"):
            "<p>Commented out text with {{ create_date|date:'c' }}</p>"
            dtt.render(dtt.date(context.create_date, "c"))
        "{% include 'sub/name-snippet.html' with greeting='Hi' only %}"
        name_snippet.render_kwargs(greeting="Hi")
        "{% with total=business.employees.count %}"

        def _dtt_namespace_0() -> None:
            total = context.business.employees.count
            "{{ total }} employee{{ total|pluralize }}"
            dtt.render(total)
            "{{ total }} employee{{ total|pluralize }}"
            dtt.render(custom.pluralize(total))


def render_kwargs(**context: Unpack[ContextKwargs]) -> None:
    return None

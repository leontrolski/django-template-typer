"""Converted from tests/templates/readme.html"""

from __future__ import annotations

from collections import abc
from typing import TYPE_CHECKING, Protocol, TypedDict, Unpack

from django_template_typer import dtt
from tests.external import custom
from tests.templates import header


class Context(Protocol, header.Context):
    @property
    def l(self) -> abc.Iterable[dtt.Renderable]: ...

    @property
    def c(self) -> dtt.Renderable | None: ...

    @property
    def b(self) -> str: ...

    @property
    def a(self) -> dtt.Renderable: ...


class ContextKwargs(TypedDict):
    l: abc.Iterable[dtt.Renderable]
    c: dtt.Renderable | None
    b: str
    a: dtt.Renderable


def render(context: Context) -> None:
    """Function that demonstrates the context type is sufficient for rendering."""
    if TYPE_CHECKING:
        "{% block title %}"
        with header.title():
            "<h1>{{ a }}</h1>"
            dtt.render(context.a)
        "Hi {{ b|capitalize_name }}"
        dtt.render(custom.capitalize_name(context.b))
        "{% for x in l %}"
        for x in context.l:
            "{{ x }}"
            dtt.render(x)
        "{% if c %}"
        if context.c:
            "{{ c }}"
            dtt.render(context.c)


def render_kwargs(**context: Unpack[ContextKwargs]) -> None:
    return None

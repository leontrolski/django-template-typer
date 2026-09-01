"""Converted from tests/templates/header.html"""

from __future__ import annotations

import contextlib
from collections import abc
from typing import TYPE_CHECKING, Protocol, TypedDict, Unpack

from django_template_typer import dtt


class Context(Protocol):
    @property
    def a(self) -> dtt.Renderable: ...


class ContextKwargs(TypedDict):
    a: dtt.Renderable


@contextlib.contextmanager
def title() -> abc.Generator[None]:
    yield None


def render(context: Context) -> None:
    """Function that demonstrates the context type is sufficient for rendering."""
    if TYPE_CHECKING:
        "{% block title %}"
        with contextlib.nullcontext():
            "{{ a }}"
            dtt.render(context.a)


def render_kwargs(**context: Unpack[ContextKwargs]) -> None:
    return None

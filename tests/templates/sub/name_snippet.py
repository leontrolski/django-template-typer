"""Converted from tests/templates/sub/name-snippet.html"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypedDict, Unpack

from django_template_typer import dtt


class Context(Protocol):
    @property
    def greeting(self) -> dtt.Renderable: ...


class ContextKwargs(TypedDict):
    greeting: dtt.Renderable


def render(context: Context) -> None:
    """Function that demonstrates the context type is sufficient for rendering."""
    if TYPE_CHECKING:
        "Hi {{ greeting }}!"
        dtt.render(context.greeting)


def render_kwargs(**context: Unpack[ContextKwargs]) -> None:
    return None

import datetime
from collections.abc import Container, Generator
from contextlib import contextmanager
from typing import Generic, TypeVarTuple, Unpack

Ts = TypeVarTuple("Ts")


class Unknown:
    """This isn't implemented by mypy, but the error is a good thing."""


class Intersection(Generic[Unpack[Ts]]):
    """This isn't implemented by mypy, but the error is a good thing."""


Renderable = int | str | float


def render(value: Renderable) -> str:
    return ""


def url(name: str, *args: object, **kwargs: object) -> str:
    return ""


def csrf_token() -> str:
    return ""


@contextmanager
def comment(comment: str | None = None) -> Generator[None]:
    yield None


def date(
    value: datetime.datetime | datetime.date | datetime.time, format: str | None = None
) -> str:
    return ""


# fmt: off
def _not(x: object) -> object: return None
def _or(x: object, y: object) -> object: return None
def _and(x: object, y: object) -> object: return None
def _in(x: object, y: Container[object]) -> object: return None
def _not_in(x: object, y: Container[object]) -> object: return None
def _is(x: object, y: object) -> object: return None
def _is_not(x: object, y: object) -> object: return None
def _eq(x: object, y: object) -> object: return None
def _neq(x: object, y: object) -> object: return None
def _gt(x: object, y: object) -> object: return None
def _gte(x: object, y: object) -> object: return None
def _lt(x: object, y: object) -> object: return None
def _lte(x: object, y: object) -> object: return None
# fmt: on

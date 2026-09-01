from __future__ import annotations

from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import UnionType
from typing import TYPE_CHECKING, Union, get_args, get_origin, is_protocol

from django_template_typer import parser


# fmt: off
class ScopeRefIfTruthy(tuple[parser.Lineno, int]): ...
ScopeRef = parser.Lineno | ScopeRefIfTruthy
@dataclass(frozen=True)
class Iter: ...
ITER = Iter()
Path = tuple[str | int | Iter, ...]
@dataclass(frozen=True)
class InferredType: t: object
InferredTypes = set[tuple[Path, InferredType]]
# fmt: on

# Scopes


@dataclass
class Scopes:
    _scopes: dict[ScopeRef, dict[Path, Path]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    _stack: list[ScopeRef] = field(default_factory=list)

    @contextmanager
    def push(self, ref: ScopeRef) -> Generator[None]:
        self._stack.append(ref)
        yield None
        self._stack.pop()

    def add(self, ref: ScopeRef, assignment_path: Path, path: Path) -> None:
        self._scopes[ref][assignment_path] = self.resolve(path)[1]

    def resolve(self, path: Path) -> tuple[ScopeRef, Path]:
        for i in range(len(path), 0, -1):
            name, rest = tuple(path[:i]), tuple(path[i:])
            for ref in reversed(self._stack):
                if name in self._scopes[ref]:
                    return ref, self._scopes[ref][name] + tuple(rest)
        return parser.Lineno(0), path


# Type Grouping


class GroupedCls(dict[str, "Grouped"]):
    if not TYPE_CHECKING:

        def __hash__(self):
            return hash(tuple(self.items()))


@dataclass(frozen=True)
class GroupedIterable:
    t: Grouped


class GroupedIntersection(frozenset["Grouped"]):
    def __or__(self, other: set[Grouped]) -> GroupedIntersection:  # type: ignore
        return GroupedIntersection(super().__or__(other))

    def __sub__(self, other: set[Grouped]) -> GroupedIntersection:  # type: ignore
        return GroupedIntersection(super().__sub__(other))


type Grouped = (
    GroupedCls
    | GroupedIterable
    | GroupedIntersection
    | tuple[Grouped, ...]
    | InferredType
)


def group_types(types: InferredTypes) -> Grouped:
    intersection = GroupedIntersection()

    by_iter = InferredTypes()
    by_int: dict[int, InferredTypes] = defaultdict(set)
    by_str: dict[str, InferredTypes] = defaultdict(set)
    for path, t in types:
        if not path:
            intersection |= {t}
            continue
        head, tail = path[0], path[1:]
        if isinstance(head, Iter):
            by_iter.add((tail, t))
        elif isinstance(head, int):
            by_int[head].add((tail, t))
        else:
            by_str[head].add((tail, t))

    if (bool(by_iter) + bool(by_int) + bool(by_str)) not in (0, 1):
        raise RuntimeError("Unable to group types")

    if by_iter:
        intersection |= {GroupedIterable(group_types(by_iter))}
    elif by_int:
        vs = (by_int[i] for i in sorted(by_int))
        intersection |= {tuple(group_types(v) for v in vs)}
    elif by_str:
        intersection |= {GroupedCls({k: group_types(v) for k, v in by_str.items()})}

    return _canonicalize(intersection)


# Helpers


def _union(t: object) -> set[type[object]] | None:
    if get_origin(t) is Union or get_origin(t) is UnionType:
        out = set[type[object]]()
        for u in get_args(t):
            if isinstance(u, type) and not is_protocol(u):
                out.add(u)
            else:
                return None
        return out
    if isinstance(t, type) and not is_protocol(t):
        return {t}
    return None


def _canonicalize(intersection: GroupedIntersection) -> Grouped:
    # Poor man's Disjunctive Normal Form
    if all(
        isinstance(t, InferredType) and (_union(t.t) is not None) for t in intersection
    ):
        canonical: set[type[object]] = {object}
        for t in intersection:
            assert isinstance(t, InferredType)
            new_intersection = set[type[object]]()
            for u in _union(t.t) or set():
                for c in canonical:
                    if issubclass(u, c):
                        new_intersection.add(u)
                    elif issubclass(c, u):
                        new_intersection.add(c)
            canonical = new_intersection
        if len(canonical) == 0:
            return intersection
        if len(canonical) == 1:
            return InferredType(next(iter(canonical)))

        return InferredType(Union[*canonical])

    if InferredType(object) in intersection and len(intersection) > 1:
        intersection -= {InferredType(object)}

    if len(intersection) == 1:
        return next(iter(intersection))
    return intersection

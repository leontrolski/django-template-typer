from __future__ import annotations

import ast
import inspect
import keyword
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, assert_never

import trolskgen

from django_template_typer import dtt, parser, resolver, typing

Code = trolskgen.Template | parser.LiteralValue


def _renderable_converter(o: object, f: trolskgen.F) -> ast.AST | None:
    if o == dtt.Renderable:
        return f(trolskgen.t("dtt.Renderable"))
    if o == dtt.Renderable | None:
        return f(trolskgen.t("dtt.Renderable | None"))
    return None


config = trolskgen.Config().prepend_converter(_renderable_converter)

KEYWORDS = set(keyword.kwlist)
FILTER_AND_TAG_MODULES: tuple[object,] = (dtt,)
IMPORTS: tuple[str, ...] = (
    "from __future__ import annotations",
    "from collections import abc",
    "import contextlib",
    "import datetime",
    "from typing import Protocol, TypedDict, Unpack, TYPE_CHECKING",
)


def convert(
    template_dirs: tuple[Path, ...],
    filter_and_tag_modules: tuple[object, ...],
    source: str | Path,
) -> trolskgen.Template:
    filter_and_tag_modules = FILTER_AND_TAG_MODULES + filter_and_tag_modules
    node = parser.parse_template(source)
    context = resolver.Context(
        source=node.source,
        template_dirs=template_dirs,
        signatures=tuple(signatures_from_modules(*filter_and_tag_modules)),
    )
    statements_ = resolver.resolve_statements(context, node.children)

    imports = IMPORTS
    for module in filter_and_tag_modules:
        from_, _, name = module.__name__.rpartition(".")  # type: ignore
        imports += (f"from {from_} import {name}",)
    if context.extends is not None:
        from_ = ".".join(context.extends.source.parent.parts)
        imports += (f"from {from_} import {_underscore(context.extends.source.stem)}",)
    for include in context.includes:
        for template_dir in template_dirs:
            if include in {
                str(n.relative_to(template_dir)) for n in template_dir.glob("**/*.html")
            }:
                *from_prefix, name = Path(include).parts
                from_ = ".".join(template_dir.parts + tuple(from_prefix))
                imports += (f"from {from_} import {_stem(name)}",)
                break
        else:
            raise RuntimeError(f"No template found for {include}")

    statements = convert_statements(statements_)
    if isinstance(source, str):
        source = "<unknown source>"

    grouped = typing.group_types(context.types)
    if grouped == typing.InferredType(object):
        grouped = typing.GroupedCls({})
    assert isinstance(grouped, typing.GroupedCls)
    parent_base: str | None = None
    if context.extends is not None:
        parent_base = f"{Path(context.extends.source).stem}.Context"
    classes = (
        YieldProtocols(
            first_cls_name="Context",
            base="Protocol",
            parent_base=parent_base,
            read_only=True,
            root=grouped,
        ).list()
        + YieldProtocols(
            first_cls_name="ContextKwargs",
            base="TypedDict",
            parent_base=None,
            read_only=False,
            root=grouped,
        ).list()[-1:]
    )

    blocks = list[trolskgen.Template]()
    for block_name in context.blocks:
        block = trolskgen.t(
            f"""
            @contextlib.contextmanager
            def {block_name}() -> abc.Generator[None]:
                yield None
            """
        )
        blocks.append(block)

    # TODO: fix trolskgen so imports + classes are nicer
    prelude = f"""
'''Converted from {source}'''

{"\n".join(imports)}

{"\n".join(trolskgen.to_source(cls, config=config) for cls in classes)}
    """
    return trolskgen.t(
        prelude
        + """
{blocks:*}

def render(context: Context) -> None:
    '''Function that demonstrates the context type is sufficient for rendering.'''
    if TYPE_CHECKING:
        {statements:*}
    return None


def render_kwargs(**context: Unpack[ContextKwargs]) -> None:
    return None
        """,
        blocks=blocks,
        statements=statements,
    )


def convert_expr(node: resolver.Expr) -> Code:
    if isinstance(node, resolver.Name):
        return trolskgen.t(f"context.{node.name}" if node.is_top_level else node.name)
    if isinstance(node, resolver.Literal):
        return node.value
    return trolskgen.t(
        "{f}({args,kwargs:*})",
        f=trolskgen.t(".".join(node.f.namespaced_name.split(".")[-2:])),
        args=[convert_expr(arg) for arg in node.args],
        kwargs={_underscore(k): convert_expr(arg) for k, arg in node.kwargs.items()},
    )


def convert_statement(node: resolver.Statement) -> Code | None:
    if isinstance(node, resolver.Noop):
        return None
    if isinstance(node, resolver.Expr):
        return convert_expr(node)
    if isinstance(node, resolver.For):
        elts = ", ".join(node.elts)
        return trolskgen.t(
            f"for {elts} in {{iter}}:\n  {{statements:*}}",
            iter=convert_expr(node.iter),
            statements=convert_statements(node.body),
        )
    if isinstance(node, resolver.If):
        d = dict[str, list[Code | resolver.Line] | Code]()
        template = ""
        for i, [predicate, statements_] in enumerate(node.conditions):
            predicate_key, statements_key = f"statements_{i}", f"predicate_{i}"
            d[statements_key] = convert_statements(statements_)
            if predicate is None:
                template += f"else:\n    {{{statements_key}:*}}\n"
            else:
                d[predicate_key] = convert_expr(predicate)
                if_ = "if" if i == 0 else "elif"
                template += f"{if_} {{{predicate_key}}}:\n    {{{statements_key}:*}}\n"
        return trolskgen.t(template, **d)
    if isinstance(node, resolver.WithClosing):
        return trolskgen.t(
            "with {call}:\n    {statements:*}",
            call=convert_expr(node.contextmanager),
            statements=convert_statements(node.body),
        )
    if isinstance(node, resolver.UseBlock):
        return trolskgen.t(
            "with {call}:\n    {statements:*}",
            call=trolskgen.t(f"{_stem(node.extends_path.name)}.{node.name}()"),
            statements=convert_statements(node.body),
        )
    if isinstance(node, resolver.DefineBlock):
        return trolskgen.t(
            "with contextlib.nullcontext():\n    {statements:*}",
            statements=convert_statements(node.body),
        )
    if isinstance(node, resolver.Include):
        return trolskgen.t(
            "{f}.render_kwargs({kwargs:*})",
            f=trolskgen.t(_stem(node.name)),
            kwargs={_underscore(k): convert_expr(v) for k, v in node.kwargs.items()},
        )
    if isinstance(node, resolver.WithAssignments):
        assignments = list[trolskgen.Template]()
        for name, arg in node.assignments:
            assignment = trolskgen.t(
                "{name} = {arg}",
                name=trolskgen.t(name),
                arg=convert_expr(arg),
            )
            assignments.append(assignment)
        return trolskgen.t(
            f"def _dtt_namespace_{node.i}() -> None:\n    {{statements:*}}",
            statements=assignments + convert_statements(node.body),
        )
    assert_never(node)


def convert_statements(
    nodes: Iterable[resolver.Statement],
) -> list[Code | resolver.Line]:
    out = list[Code | resolver.Line]()
    for node in nodes:
        converted = convert_statement(node)
        if converted is None:
            continue
        out.append(node.source_line)
        out.append(converted)
    if not out:
        return [trolskgen.t("...")]
    return out


# Helpers


def signatures_from_modules(*modules: Any) -> Iterator[resolver.Signature]:
    for module in modules:
        for _, func in inspect.getmembers(module, inspect.isfunction):
            if func.__module__ != module.__name__:
                continue
            sig = inspect.signature(func)
            if sig.return_annotation is inspect.Parameter.empty:
                raise RuntimeError(f"Expected function with annotation - {func}")
            args_dict = resolver.ArgsDict()
            for k, p in sig.parameters.items():
                if p.kind is inspect.Parameter.VAR_POSITIONAL:
                    args_dict._var_positional = typing.InferredType(p.annotation)
                elif p.kind is inspect.Parameter.VAR_KEYWORD:
                    args_dict._var_keyword = typing.InferredType(p.annotation)
                else:
                    args_dict._by_name[k] = typing.InferredType(p.annotation)

            yield resolver.Signature(
                func.__name__,
                f"{module.__name__}.{func.__name__}",
                args_dict,
                sig.return_annotation,
            )


def _stem(s: str) -> str:
    return _underscore(Path(s).stem)


def _underscore(s: str) -> str:
    if s in KEYWORDS:
        return s + "_"
    return s.replace("-", "_")


@dataclass
class YieldProtocols:
    first_cls_name: str
    base: str
    parent_base: str | None
    read_only: bool
    root: typing.GroupedCls
    i: int = 0
    classes: list[trolskgen.Template] = field(default_factory=list)

    def list(self) -> list[trolskgen.Template]:
        self._convert(self.root)
        return self.classes

    def _convert(self, grouped: typing.Grouped) -> object:
        if isinstance(grouped, typing.GroupedIterable):
            return Iterable[self._convert(grouped.t)]  # type: ignore
        if isinstance(grouped, typing.GroupedIntersection):
            return dtt.Intersection[*(self._convert(u) for u in grouped)]  # type: ignore
        if isinstance(grouped, tuple):
            return tuple[*(self._convert(u) for u in grouped)]  # type: ignore
        if isinstance(grouped, typing.GroupedCls):
            i = self.i
            self.i += 1
            fields = list[trolskgen.Template]()
            for name, t in grouped.items():
                if self.read_only:
                    fields.append(
                        trolskgen.t(
                            f"@property\ndef {_underscore(name)}(self) -> {{t}}: ...",
                            t=self._convert(t),
                        )
                    )
                else:
                    fields.append(
                        trolskgen.t(f"{_underscore(name)}: {{t}}", t=self._convert(t))
                    )

            cls_name = f"Nested{i}"
            bases = [trolskgen.t(self.base)]
            if i == 0:
                cls_name = self.first_cls_name
                if self.parent_base is not None:
                    bases.append(trolskgen.t(self.parent_base))

            cls = trolskgen.t(
                """
                class {cls_name}({bases:*}):
                    {fields:*}
                """,
                cls_name=cls_name,
                bases=bases,
                fields=fields or [trolskgen.t("...")],
            )
            self.classes.append(cls)
            return trolskgen.t(cls_name)
        return grouped.t

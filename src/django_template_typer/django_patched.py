from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from django.template import base, exceptions

# For, commented tags, haven't determined whether they are "simple" or not.
SIMPLE_BUILTIN_TAGS = {
    # "autoescape": False,
    "block": True,
    "comment": True,
    # "csp_nonce_attr": False,
    "csrf_token": False,
    # "cycle": False,
    # "debug": False,
    "extends": False,
    # "filter": False,
    # "firstof": False,
    # "ifchanged": False,
    "include": False,
    "load": False,
    # "lorem": False,
    # "now": False,
    # "partial": False,
    # "partialdef": False,
    # "querystring": False,
    # "regroup": False,
    # "resetcycle": False,
    # "spaceless": False,
    # "templatetag": False,
    "url": False,
    # "verbatim": False,
    # "widthratio": False,
    "with": True,
}


class FilterExpression(base.FilterExpression):
    # Don't check args of filters
    @staticmethod
    def args_check(
        name: str, func: Callable[..., Any], provided: list[tuple[bool, Any]]
    ) -> bool:
        return True


class Parser(base.Parser):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # Resolve nearly all to generic `Tag`/`Library`/`Filter`
        for tag in SIMPLE_BUILTIN_TAGS:
            self.tags.pop(tag)
        self.tags = KeyDefaultDict(
            self.tags,
            lambda k: TagWithClosing if SIMPLE_BUILTIN_TAGS.get(cast(str, k)) else Tag,
        )
        self.libraries = KeyDefaultDict({}, lambda _: Library())
        self.filters = KeyDefaultDict({}, lambda k: Filter(k))

    def compile_filter(self, token: str) -> base.FilterExpression:
        return FilterExpression(token, self)


class Template(base.Template):
    def compile_nodelist(self) -> base.NodeList:
        lexer: base.Lexer
        if self.engine.debug:
            lexer = base.DebugLexer(self.source)
        else:
            lexer = base.Lexer(self.source)

        tokens = lexer.tokenize()

        # The only difference is that we use our `Parser`
        parser = Parser(
            tokens,
            self.engine.template_libraries,
            self.engine.template_builtins,
            self.origin,
        )

        try:
            nodelist = parser.parse()
            self.extra_data = parser.extra_data
            return nodelist
        except Exception as e:
            if self.engine.debug:
                e.template_debug = self.get_exception_info(e, e.token)  # type: ignore[attr-defined]
            if (
                isinstance(e, exceptions.TemplateSyntaxError)
                and self.origin.name != base.UNKNOWN_SOURCE
                and e.args
            ):
                raw_message = e.args[0]
                e.raw_error_message = raw_message  # type: ignore[attr-defined]
                e.args = (f"Template: {self.origin.name}, {raw_message}", *e.args[1:])
            raise


@dataclass
class Library:
    tags: dict[str, object] = field(default_factory=dict)
    filters: dict[str, object] = field(default_factory=dict)


class Tag(base.Node):
    child_nodelists: tuple[str, ...] = ()
    name: str
    args: list[base.FilterExpression]
    kwargs: dict[str, base.FilterExpression]

    def __init__(
        self,
        parser: base.Parser,
        token: base.Token,
    ):
        name, *bits = token.split_contents()
        self.name = name
        self.args = []
        self.kwargs = {}
        for bit in bits:
            kwarg = base.token_kwargs([bit], parser)
            if kwarg:
                param, value = kwarg.popitem()
                self.kwargs[str(param)] = value
            else:
                self.args.append(parser.compile_filter(bit))

    def render(self, context: object) -> str:
        raise NotImplementedError

    def render_annotated(self, context: object) -> str:
        raise NotImplementedError


class TagWithClosing(Tag):
    child_nodelists = ("nodelist",)
    nodelist: base.NodeList

    def __init__(
        self,
        parser: base.Parser,
        token: base.Token,
    ):
        super().__init__(parser, token)
        self.nodelist = parser.parse((f"end{self.name}",))
        parser.next_token()


@dataclass
class Filter:
    name: object

    def __call__(self) -> object:
        return None


class KeyDefaultDict(dict[Any, Any]):
    def __init__(self, iterable: Any, factory: Callable[[object], object]):
        super().__init__(iterable)
        self.factory = factory

    def __contains__(self, _: object) -> bool:
        return True

    def __missing__(self, key: object) -> object:
        return self.factory(key)

import datetime
import textwrap
from pathlib import Path

import trolskgen

from django_template_typer import codegen, dtt, parser, resolver, typing
from tests.external import custom

TEMPLATES = Path("tests/templates")


def _assert_eq(source: str, expected: str) -> None:
    root = parser.parse_template(source)
    context = resolver.Context(
        source=root.source,
        template_dirs=(TEMPLATES,),
        signatures=tuple(codegen.signatures_from_modules(dtt, custom)),
    )
    statements = codegen.convert_statements(
        resolver.resolve_statements(context, root.children)
    )
    # Add a fake docstring then strip it. Makes for better diff.
    codegenned = trolskgen.to_source(
        trolskgen.t("''\n\n{statements:*}", statements=statements)
    )
    actual = "\n".join(codegenned.splitlines()[1:])
    expected = textwrap.dedent(expected).strip()
    assert actual == expected


def test_exprs() -> None:
    _assert_eq(
        "{{ foo }}",
        """
        '{{ foo }}'
        dtt.render(context.foo)
        """,
    )
    _assert_eq(
        "{{ 1 }}",
        """
        '{{ 1 }}'
        dtt.render(1)
        """,
    )
    _assert_eq(
        "{{ foo|f|g:'1'|h }}",
        """
        "{{ foo|f|g:'1'|h }}"
        dtt.render(custom.h(custom.g(custom.f(context.foo), '1')))
        """,
    )


def test_tags() -> None:
    _assert_eq(
        "{% custom_tag p|f q r=d s=e|g %}",
        """
        '{% custom_tag p|f q r=d s=e|g %}'
        custom.custom_tag(custom.f(context.p), context.q, r=context.d, s=custom.g(context.e))
        """,
    )
    _assert_eq(
        """
        {% comment 'Optional note' %}
            <p>Commented out text with {{ create_date|date:'c' }}</p>
        {% endcomment %}
        """,
        """
        "{% comment 'Optional note' %}"
        with dtt.comment('Optional note'):
            "<p>Commented out text with {{ create_date|date:'c' }}</p>"
            dtt.render(dtt.date(context.create_date, 'c'))
        """,
    )
    _assert_eq(
        "{% csrf_token %}",
        """
        '{% csrf_token %}'
        dtt.csrf_token()
        """,
    )


def test_include() -> None:
    _assert_eq(
        "{% include 'name_snippet.html' with greeting='Hi' only %}",
        """
        "{% include 'name_snippet.html' with greeting='Hi' only %}"
        name_snippet.render_kwargs(greeting='Hi')
        """,
    )


def test_with() -> None:
    _assert_eq(
        """
        {% with total=business.employees.count %}
            {{ total }} employee{{ total|pluralize }}
        {% endwith %}
        """,
        """
        '{% with total=business.employees.count %}'

        def _dtt_namespace_0() -> None:
            total = context.business.employees.count
            '{{ total }} employee{{ total|pluralize }}'
            dtt.render(total)
            '{{ total }} employee{{ total|pluralize }}'
            dtt.render(custom.pluralize(total))
        """,
    )


def test_define_block() -> None:
    _assert_eq(
        """
        {% block title %}
            My Title
            {{ a }}
        {% endblock %}
        """,
        """
        '{% block title %}'
        with contextlib.nullcontext():
            '{{ a }}'
            dtt.render(context.a)
        """,
    )


def test_use_block() -> None:
    _assert_eq(
        """
        {% extends 'header.html' %}
        {% block title %}
            My Title
            {{ a }}
        {% endblock %}
        """,
        """
        '{% block title %}'
        with header.title():
            '{{ a }}'
            dtt.render(context.a)
        """,
    )


def test_if() -> None:
    _assert_eq(
        """
        {% if e or not f %}
            Hullo
        {% elif g %}
            There
        {% else %}
            {{ e }}
        {% endif %}
        """,
        """
        '{% if e or not f %}'
        if dtt._or(context.e, dtt._not(context.f)):
            ...
        elif context.g:
            ...
        else:
            '{{ e }}'
            dtt.render(context.e)
        """,
    )


def test_for() -> None:
    _assert_eq(
        """
        {% for x in l %}
            {{ x }}
            {% for y, z in x %}
                {{ y.foo }}
            {% endfor %}
        {% endfor %}
        """,
        """
        '{% for x in l %}'
        for x in context.l:
            '{{ x }}'
            dtt.render(x)
            '{% for y, z in x %}'
            for y, z in x:
                '{{ y.foo }}'
                dtt.render(y.foo)
        """,
    )


def test_whole_file_scope_and_types() -> None:
    node = parser.parse_template(TEMPLATES / "template_0.html")
    context = resolver.Context(
        source=node.source,
        template_dirs=(TEMPLATES,),
        signatures=tuple(codegen.signatures_from_modules(dtt, custom)),
    )
    resolver.resolve_statements(context, node.children)

    assert context.scopes._scopes == {
        12: {("x",): ("l", "woo", typing.ITER)},
        14: {
            ("y",): ("l", "woo", typing.ITER, typing.ITER, 0),
            ("z",): ("l", "woo", typing.ITER, typing.ITER, 1),
        },
        (23, 1): {("g", "foo"): ("g", "foo")},
        (23, 2): {},
        42: {("total",): ("business", "employees", "count")},
    }
    I = typing.InferredType
    expected_types: typing.InferredTypes = {
        (("a",), I(int)),
        (("a",), I(dtt.Renderable)),
        (("b",), I(int)),
        (("business", "employees", "count"), I(str)),
        (("business", "employees", "count"), I(dtt.Renderable)),
        (("create_date",), I(datetime.datetime | datetime.date | datetime.time)),
        (("d",), I(datetime.datetime)),
        (("e",), I(object)),
        (("e",), I(dtt.Renderable)),
        (("f",), I(object)),
        (("g", "foo"), I(object)),
        (("g", "foo"), I(dtt.Renderable | None)),
        (("l", "woo", typing.ITER), I(object)),
        (("l", "woo", typing.ITER), I(dtt.Renderable)),
        (("l", "woo", typing.ITER, typing.ITER, 0), I(object)),
        (("l", "woo", typing.ITER, typing.ITER, 0, "foo"), I(dtt.Renderable)),
        (("l", "woo", typing.ITER, typing.ITER, 1), I(object)),
        (("name",), I(str)),
        (("p",), I(float)),
        (("q",), I(float)),
        (("surname",), I(str)),
        (("t",), I(object)),
        (("some_arg",), I(object)),
        (("some_kw_arg",), I(object)),
    }
    assert sorted(context.types, key=repr) == sorted(expected_types, key=repr)
    expected_grouped: typing.Grouped = typing.GroupedCls(
        {
            "a": I(int),
            "b": I(int),
            "create_date": I(datetime.datetime | datetime.date | datetime.time),
            "d": I(datetime.datetime),
            "e": I(dtt.Renderable),
            "f": I(object),
            "g": typing.GroupedCls({"foo": I(dtt.Renderable | None)}),
            "name": I(str),
            "p": I(float),
            "q": I(float),
            "surname": I(str),
            "t": I(object),
            "some_arg": I(object),
            "some_kw_arg": I(object),
            "business": typing.GroupedCls(
                {
                    "employees": typing.GroupedCls(
                        {
                            "count": I(str),
                        }
                    ),
                }
            ),
            "l": typing.GroupedCls(
                {
                    "woo": typing.GroupedIterable(
                        typing.GroupedIntersection(
                            (
                                I(dtt.Renderable),
                                typing.GroupedIterable(
                                    (
                                        typing.GroupedCls({"foo": I(dtt.Renderable)}),
                                        I(object),
                                    )
                                ),
                            )
                        )
                    )
                }
            ),
        }
    )
    actual_grouped = typing.group_types(context.types)
    assert isinstance(actual_grouped, dict)
    assert isinstance(expected_grouped, dict)
    assert sorted(actual_grouped.items(), key=repr) == sorted(
        expected_grouped.items(), key=repr
    )


def test_whole_file() -> None:
    for template in ["readme", "header", "sub/name-snippet", "template_0"]:
        t = codegen.convert(
            template_dirs=(TEMPLATES,),
            filter_and_tag_modules=(custom,),
            source=TEMPLATES / f"{template}.html",
        )
        actual = trolskgen.to_source(t)
        (TEMPLATES / f"{template.replace('-', '_')}.py").write_text(actual)

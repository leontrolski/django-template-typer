from pathlib import Path

from django_template_typer import parser

TEMPLATES = Path("tests/templates")


def test_parse_template_str() -> None:
    node = parser.parse_template("{{ a|f:'1'|g:2|h:b }}{{ 3 }}{{ '4' }}")
    assert node == parser.RootNode(
        source="{{ a|f:'1'|g:2|h:b }}{{ 3 }}{{ '4' }}",
        children=(
            parser.ExprNode(
                value=parser.FilterExpression(
                    var=parser.Name(name="a"),
                    filters=[
                        parser.Filter(
                            var=parser.Name(name="f"),
                            arg=parser.Literal(value=parser.LiteralValue("1")),
                        ),
                        parser.Filter(
                            var=parser.Name(name="g"),
                            arg=parser.Literal(value=parser.LiteralValue(2)),
                        ),
                        parser.Filter(
                            var=parser.Name(name="h"), arg=parser.Name(name="b")
                        ),
                    ],
                )
            ),
            parser.ExprNode(
                value=parser.FilterExpression(
                    var=parser.Literal(value=parser.LiteralValue(3)), filters=[]
                )
            ),
            parser.ExprNode(
                value=parser.FilterExpression(
                    var=parser.Literal(value=parser.LiteralValue("4")), filters=[]
                )
            ),
        ),
    )


def test_parse_is_not_none() -> None:
    node = parser.parse_template("{% if x is not None %}{% endif %}")
    assert node == parser.RootNode(
        children=(
            parser.IfNode(
                conditions=[
                    (
                        parser.BinaryOp(
                            op="is not",
                            first=parser.FilterExpression(var=parser.Name(name="x")),
                            second=parser.FilterExpression(
                                var=parser.Name(name="None")
                            ),
                        ),
                        [],
                    )
                ]
            ),
        ),
        source="{% if x is not None %}{% endif %}",
    )


def test_parse_template_from_file() -> None:
    node = parser.parse_template(TEMPLATES / "template_0.html")
    assert node.to_str().strip() == (TEMPLATES / "template_0.html").read_text().strip()

    assert node.children == (
        parser.TagNode(
            name="load",
            args=[parser.FilterExpression(var=parser.Name(name="custom"))],
            kwargs={},
        ),
        parser.TextNode(s="\n\n"),
        parser.TagNode(
            lineno=parser.Lineno(3),
            name="extends",
            args=[
                parser.FilterExpression(
                    var=parser.Literal(value=parser.LiteralValue("header.html"))
                )
            ],
            kwargs={},
        ),
        parser.TextNode(lineno=parser.Lineno(3), s="\n\n"),
        parser.TagNode(
            lineno=parser.Lineno(5),
            children=(
                parser.TextNode(lineno=parser.Lineno(5), s="\n    My Title\n    "),
                parser.ExprNode(
                    lineno=parser.Lineno(7),
                    value=parser.FilterExpression(var=parser.Name(name="a")),
                ),
                parser.TextNode(lineno=parser.Lineno(7), s="\n"),
            ),
            name="block",
            args=[parser.FilterExpression(var=parser.Name(name="title"))],
            kwargs={},
            with_closing=True,
        ),
        parser.TextNode(lineno=parser.Lineno(8), s="\n\nHi "),
        parser.ExprNode(
            lineno=parser.Lineno(10),
            value=parser.FilterExpression(
                var=parser.Name(name="name"),
                filters=[parser.Filter(var=parser.Name(name="brrp"), arg=None)],
            ),
        ),
        parser.TextNode(lineno=parser.Lineno(10), s=" "),
        parser.ExprNode(
            lineno=parser.Lineno(10),
            value=parser.FilterExpression(
                var=parser.Name(name="surname"),
                filters=[
                    parser.Filter(
                        var=parser.Name(name="arg"),
                        arg=parser.Literal(value=parser.LiteralValue(1)),
                    )
                ],
            ),
        ),
        parser.TextNode(lineno=parser.Lineno(10), s="\n\n"),
        parser.ForNode(
            lineno=parser.Lineno(12),
            children=(
                parser.TextNode(lineno=parser.Lineno(12), s="\n    "),
                parser.ExprNode(
                    lineno=parser.Lineno(13),
                    value=parser.FilterExpression(var=parser.Name(name="x")),
                ),
                parser.TextNode(lineno=parser.Lineno(13), s="\n    "),
                parser.ForNode(
                    lineno=parser.Lineno(14),
                    children=(
                        parser.TextNode(lineno=parser.Lineno(14), s="\n        "),
                        parser.ExprNode(
                            lineno=parser.Lineno(15),
                            value=parser.FilterExpression(
                                var=parser.Name(name="y.foo")
                            ),
                        ),
                        parser.TextNode(lineno=parser.Lineno(15), s="\n    "),
                    ),
                    elts=[parser.Name(name="y"), parser.Name(name="z")],
                    iter=parser.FilterExpression(var=parser.Name(name="x")),
                ),
                parser.TextNode(lineno=parser.Lineno(16), s="\n"),
            ),
            elts=[parser.Name(name="x")],
            iter=parser.FilterExpression(var=parser.Name(name="l.woo")),
        ),
        parser.TextNode(lineno=parser.Lineno(17), s="\n\n"),
        parser.ExprNode(
            lineno=parser.Lineno(19),
            value=parser.FilterExpression(
                var=parser.Name(name="a"),
                filters=[
                    parser.Filter(var=parser.Name(name="f"), arg=parser.Name(name="b")),
                    parser.Filter(
                        var=parser.Name(name="g"),
                        arg=parser.Literal(value=parser.LiteralValue("c")),
                    ),
                    parser.Filter(
                        var=parser.Name(name="h"),
                        arg=parser.Literal(value=parser.LiteralValue(1)),
                    ),
                ],
            ),
        ),
        parser.TextNode(lineno=parser.Lineno(19), s="\n\n"),
        parser.TagNode(
            lineno=parser.Lineno(21),
            name="custom_tag",
            args=[
                parser.FilterExpression(var=parser.Name(name="p")),
                parser.FilterExpression(var=parser.Name(name="q")),
            ],
            kwargs={"r": parser.FilterExpression(var=parser.Name(name="d"))},
        ),
        parser.TextNode(lineno=parser.Lineno(21), s=" more args here\n\n"),
        parser.IfNode(
            lineno=parser.Lineno(23),
            conditions=[
                (
                    parser.BinaryOp(
                        op="or",
                        first=parser.FilterExpression(var=parser.Name(name="e")),
                        second=parser.UnaryOp(
                            op="not",
                            first=parser.FilterExpression(var=parser.Name(name="f")),
                        ),
                    ),
                    [parser.TextNode(lineno=parser.Lineno(23), s="\n    Hullo\n")],
                ),
                (
                    parser.FilterExpression(var=parser.Name(name="g.foo")),
                    [
                        parser.TextNode(lineno=parser.Lineno(25), s="\n    "),
                        parser.ExprNode(
                            lineno=parser.Lineno(26),
                            value=parser.FilterExpression(
                                var=parser.Name(name="g.foo")
                            ),
                        ),
                        parser.TextNode(lineno=parser.Lineno(26), s="\n    There\n"),
                    ],
                ),
                (
                    None,
                    [
                        parser.TextNode(lineno=parser.Lineno(28), s="\n    "),
                        parser.ExprNode(
                            lineno=parser.Lineno(29),
                            value=parser.FilterExpression(var=parser.Name(name="e")),
                        ),
                        parser.TextNode(lineno=parser.Lineno(29), s="\n"),
                    ],
                ),
            ],
        ),
        parser.TextNode(lineno=parser.Lineno(30), s="\n\n"),
        parser.TagNode(
            lineno=parser.Lineno(32),
            name="url",
            args=[
                parser.FilterExpression(
                    var=parser.Literal(value=parser.LiteralValue("some-url-name"))
                ),
                parser.FilterExpression(var=parser.Name(name="t")),
                parser.FilterExpression(var=parser.Name(name="some_arg")),
            ],
            kwargs={
                "u": parser.FilterExpression(
                    var=parser.Literal(value=parser.LiteralValue(1))
                ),
                "v": parser.FilterExpression(var=parser.Name(name="some_kw_arg")),
            },
        ),
        parser.TextNode(lineno=parser.Lineno(32), s="\n\n"),
        parser.TagNode(lineno=parser.Lineno(34), name="csrf_token", args=[], kwargs={}),
        parser.TextNode(lineno=parser.Lineno(34), s="\n\n"),
        parser.TagNode(
            lineno=parser.Lineno(36),
            children=(
                parser.TextNode(
                    lineno=parser.Lineno(36), s="\n    <p>Commented out text with "
                ),
                parser.ExprNode(
                    lineno=parser.Lineno(37),
                    value=parser.FilterExpression(
                        var=parser.Name(name="create_date"),
                        filters=[
                            parser.Filter(
                                var=parser.Name(name="date"),
                                arg=parser.Literal(value=parser.LiteralValue("c")),
                            )
                        ],
                    ),
                ),
                parser.TextNode(lineno=parser.Lineno(37), s="</p>\n"),
            ),
            name="comment",
            args=[
                parser.FilterExpression(
                    var=parser.Literal(value=parser.LiteralValue("Optional note"))
                )
            ],
            kwargs={},
            with_closing=True,
        ),
        parser.TextNode(lineno=parser.Lineno(38), s="\n\n"),
        parser.TagNode(
            lineno=parser.Lineno(40),
            name="include",
            args=[
                parser.FilterExpression(
                    var=parser.Literal(
                        value=parser.LiteralValue("sub/name-snippet.html")
                    )
                )
            ],
            kwargs={
                "greeting": parser.FilterExpression(
                    var=parser.Literal(value=parser.LiteralValue("Hi"))
                )
            },
            pre_bools=[parser.Name(name="with")],
            post_bools=[parser.Name(name="only")],
        ),
        parser.TextNode(lineno=parser.Lineno(40), s="\n\n"),
        parser.TagNode(
            lineno=parser.Lineno(42),
            children=(
                parser.TextNode(lineno=parser.Lineno(42), s="\n    "),
                parser.ExprNode(
                    lineno=parser.Lineno(43),
                    value=parser.FilterExpression(var=parser.Name(name="total")),
                ),
                parser.TextNode(lineno=parser.Lineno(43), s=" employee"),
                parser.ExprNode(
                    lineno=parser.Lineno(43),
                    value=parser.FilterExpression(
                        var=parser.Name(name="total"),
                        filters=[
                            parser.Filter(var=parser.Name(name="pluralize"), arg=None)
                        ],
                    ),
                ),
                parser.TextNode(lineno=parser.Lineno(43), s="\n"),
            ),
            name="with",
            args=[],
            kwargs={
                "total": parser.FilterExpression(
                    var=parser.Name(name="business.employees.count")
                )
            },
            with_closing=True,
        ),
        parser.TextNode(lineno=parser.Lineno(44), s="\n"),
    )

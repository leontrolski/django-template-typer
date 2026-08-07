from pathlib import Path

from django_template_typer import parser

TEMPLATES = Path(__file__).parent / "templates"


def test_parse_template_0() -> None:
    node = parser.parse_template(TEMPLATES / "template_0.html")
    assert node.to_str().strip() == (TEMPLATES / "template_0.html").read_text().strip()

    assert node == parser.RootNode(
        children=(
            parser.SimpleTagNode(
                name="load",
                args=[
                    parser.FilterExpression(var=parser.Name(name="custom"), filters=[])
                ],
                kwargs={},
                with_closing=False,
            ),
            parser.TextNode(s="\n\n"),
            parser.SimpleTagNode(
                lineno=3,
                name="extends",
                args=[
                    parser.FilterExpression(
                        var=parser.Literal(value="header.html"), filters=[]
                    )
                ],
                kwargs={},
                with_closing=False,
            ),
            parser.TextNode(lineno=3, s="\n\n"),
            parser.SimpleTagNode(
                lineno=5,
                children=(
                    parser.TextNode(lineno=5, s="\n    My Title\n    "),
                    parser.ExprNode(
                        lineno=7,
                        value=parser.FilterExpression(
                            var=parser.Name(name="a"), filters=[]
                        ),
                    ),
                    parser.TextNode(lineno=7, s="\n"),
                ),
                name="block",
                args=[
                    parser.FilterExpression(var=parser.Name(name="title"), filters=[])
                ],
                kwargs={},
                with_closing=True,
            ),
            parser.TextNode(lineno=8, s="\n\nHi "),
            parser.ExprNode(
                lineno=10,
                value=parser.FilterExpression(
                    var=parser.Name(name="name"),
                    filters=[parser.Filter(var=parser.Name(name="brrp"), arg=None)],
                ),
            ),
            parser.TextNode(lineno=10, s=" "),
            parser.ExprNode(
                lineno=10,
                value=parser.FilterExpression(
                    var=parser.Name(name="surname"),
                    filters=[
                        parser.Filter(
                            var=parser.Name(name="arg"), arg=parser.Name(name="1")
                        )
                    ],
                ),
            ),
            parser.TextNode(lineno=10, s="\n\n"),
            parser.ForNode(
                lineno=12,
                children=(
                    parser.TextNode(lineno=12, s="\n    "),
                    parser.ExprNode(
                        lineno=13,
                        value=parser.FilterExpression(
                            var=parser.Name(name="x"), filters=[]
                        ),
                    ),
                    parser.TextNode(lineno=13, s="\n    "),
                    parser.ForNode(
                        lineno=14,
                        children=(
                            parser.TextNode(lineno=14, s="\n        "),
                            parser.ExprNode(
                                lineno=15,
                                value=parser.FilterExpression(
                                    var=parser.Name(name="y.foo"), filters=[]
                                ),
                            ),
                            parser.TextNode(lineno=15, s="\n    "),
                        ),
                        elts=[parser.Name(name="y"), parser.Name(name="z")],
                        iter=parser.FilterExpression(
                            var=parser.Name(name="x"), filters=[]
                        ),
                    ),
                    parser.TextNode(lineno=16, s="\n"),
                ),
                elts=[parser.Name(name="x")],
                iter=parser.FilterExpression(var=parser.Name(name="l"), filters=[]),
            ),
            parser.TextNode(lineno=17, s="\n\n"),
            parser.ExprNode(
                lineno=19,
                value=parser.FilterExpression(
                    var=parser.Name(name="a"),
                    filters=[
                        parser.Filter(
                            var=parser.Name(name="f"), arg=parser.Name(name="b")
                        ),
                        parser.Filter(
                            var=parser.Name(name="g"), arg=parser.Literal(value="c")
                        ),
                        parser.Filter(
                            var=parser.Name(name="h"), arg=parser.Name(name="1")
                        ),
                    ],
                ),
            ),
            parser.TextNode(lineno=19, s="\n\n"),
            parser.SimpleTagNode(
                lineno=21,
                name="custom_tag",
                args=[
                    parser.FilterExpression(var=parser.Name(name="p"), filters=[]),
                    parser.FilterExpression(var=parser.Name(name="q"), filters=[]),
                ],
                kwargs={
                    "r": parser.FilterExpression(var=parser.Name(name="d"), filters=[])
                },
                with_closing=False,
            ),
            parser.TextNode(lineno=21, s=" more args here\n\n"),
            parser.IfNode(
                lineno=23,
                children=(
                    parser.TextNode(lineno=23, s="\n    Hullo\n"),
                    parser.TextNode(lineno=25, s="\n    There\n"),
                ),
                conditions=[
                    (
                        parser.BinaryOp(
                            op="or",
                            first=parser.FilterExpression(
                                var=parser.Name(name="e"), filters=[]
                            ),
                            second=parser.UnaryOp(
                                op="not",
                                first=parser.FilterExpression(
                                    var=parser.Name(name="f"), filters=[]
                                ),
                            ),
                        ),
                        [parser.TextNode(lineno=23, s="\n    Hullo\n")],
                    ),
                    (
                        parser.FilterExpression(var=parser.Name(name="g"), filters=[]),
                        [parser.TextNode(lineno=25, s="\n    There\n")],
                    ),
                ],
            ),
            parser.TextNode(lineno=27, s="\n\n"),
            parser.SimpleTagNode(
                lineno=29,
                name="url",
                args=[
                    parser.FilterExpression(
                        var=parser.Literal(value="some-url-name"), filters=[]
                    ),
                    parser.FilterExpression(var=parser.Name(name="t"), filters=[]),
                ],
                kwargs={
                    "u": parser.FilterExpression(var=parser.Name(name="1"), filters=[])
                },
                with_closing=False,
            ),
            parser.TextNode(lineno=29, s="\n\n"),
            parser.SimpleTagNode(
                lineno=31, name="csrf_token", args=[], kwargs={}, with_closing=False
            ),
            parser.TextNode(lineno=31, s="\n\n"),
            parser.SimpleTagNode(
                lineno=33,
                children=(
                    parser.TextNode(lineno=33, s="\n    <p>Commented out text with "),
                    parser.ExprNode(
                        lineno=34,
                        value=parser.FilterExpression(
                            var=parser.Name(name="create_date"),
                            filters=[
                                parser.Filter(
                                    var=parser.Name(name="date"),
                                    arg=parser.Literal(value="c"),
                                )
                            ],
                        ),
                    ),
                    parser.TextNode(lineno=34, s="</p>\n"),
                ),
                name="comment",
                args=[
                    parser.FilterExpression(
                        var=parser.Literal(value="Optional note"), filters=[]
                    )
                ],
                kwargs={},
                with_closing=True,
            ),
            parser.TextNode(lineno=35, s="\n\n"),
            parser.SimpleTagNode(
                lineno=37,
                name="include",
                args=[
                    parser.FilterExpression(
                        var=parser.Literal(value="name_snippet.html"), filters=[]
                    )
                ],
                kwargs={
                    "greeting": parser.FilterExpression(
                        var=parser.Literal(value="Hi"), filters=[]
                    )
                },
                with_closing=False,
                include=parser.IncludeSpecialArgs(with_=True, only=True),
            ),
            parser.TextNode(lineno=37, s="\n\n"),
            parser.SimpleTagNode(
                lineno=39,
                children=(
                    parser.TextNode(lineno=39, s="\n    "),
                    parser.ExprNode(
                        lineno=40,
                        value=parser.FilterExpression(
                            var=parser.Name(name="total"), filters=[]
                        ),
                    ),
                    parser.TextNode(lineno=40, s=" employee"),
                    parser.ExprNode(
                        lineno=40,
                        value=parser.FilterExpression(
                            var=parser.Name(name="total"),
                            filters=[
                                parser.Filter(
                                    var=parser.Name(name="pluralize"), arg=None
                                )
                            ],
                        ),
                    ),
                    parser.TextNode(lineno=40, s="\n"),
                ),
                name="with",
                args=[],
                kwargs={
                    "total": parser.FilterExpression(
                        var=parser.Name(name="business.employees.count"), filters=[]
                    )
                },
                with_closing=True,
            ),
            parser.TextNode(lineno=41, s="\n"),
        )
    )

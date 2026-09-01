# Django Template Typer

_Work in progress._

Django templates imply a `Context` protocol type that's required for them to render.

For example, the template:

```html
{% extends 'header.html' %}
{% load custom %}

{% block title %}
    <h1>{{ a }}</h1>
{% endblock %}

Hi {{ b|capitalize_name }}

{% for x in l %}
    {{ x }}
{% endfor %}

{% if c %}
    {{ c }}
{% endif %}
```

Is somewhat equivalent to the Python code:

```python
from django_template_typer import dtt
from somewhere import header
from somewhere_else import custom


def render(context: Context) -> None:
    with header.title():
        dtt.render(context.a)
    dtt.render(custom.capitalize_name(context.b))
    for x in context.l:
        dtt.render(x)
    if context.c:
        dtt.render(context.c)
```

With the implied `Context` protocol type being:

```python
class Context(Protocol, header.Context):
    @property
    def a(self) -> dtt.Renderable: ...
    @property
    def b(self) -> str: ...
    @property
    def l(self) -> Iterable[dtt.Renderable]: ...
    @property
    def c(self) -> dtt.Renderable | None: ...
```

Django Template Typer is a codegen tool that for a given `template.html` will spit out an equivalent `template.py`. See [examples in the tests](./tests/templates/).

Once you've run the codegen, instead of calling:

```python
django.render("template.html", **context)
```

You call:

```python
from templates.somewhere import template

template.render(context)
```

Then running `mypy` will pick up any bugs.

# TODO

- Write and package as a CLI tool.
- Try and use it in anger on a smaller project.

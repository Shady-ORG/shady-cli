"""Hello command for shady CLI."""

import typer


def hello(name: str = "world") -> None:
    """Greet the given NAME."""
    typer.echo(f"Hello {name}!")

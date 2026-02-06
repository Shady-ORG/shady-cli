"""Command line interface for the shady CLI project."""

import typer

from .hello import hello
from .todo import app as todo_app

app = typer.Typer()
app.command()(hello)
app.add_typer(todo_app, name="todo")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()

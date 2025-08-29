"""Command line interface for the shady CLI project."""

import typer

app = typer.Typer()


@app.command()
def hello(name: str = "world") -> None:
    """Greet the given NAME."""
    typer.echo(f"Hello {name}!")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()

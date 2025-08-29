"""Todo command group for shady CLI."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer()
console = Console()
TODO_FILE = Path.home() / ".shady_todos.json"


def _load_todos() -> list:
    if TODO_FILE.exists():
        return json.loads(TODO_FILE.read_text())
    return []


def _save_todos(todos: list) -> None:
    TODO_FILE.write_text(json.dumps(todos, indent=2))


@app.command()
def add(text: str, md: bool = typer.Option(False, "--md", help="Attach Markdown using vi")) -> None:
    """Add a todo with TEXT. Optionally attach Markdown."""
    markdown = ""
    if md:
        editor = os.environ.get("EDITOR", "vi")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        subprocess.call([editor, str(tmp_path)])
        markdown = tmp_path.read_text()
        tmp_path.unlink()
    todos = _load_todos()
    todos.append({"text": text, "markdown": markdown})
    _save_todos(todos)
    typer.echo("Todo added")


@app.command("list")
def list_todos() -> None:
    """List all todos."""
    todos = _load_todos()
    for idx, todo in enumerate(todos, 1):
        typer.echo(f"{idx}. {todo['text']}")
        if todo.get("markdown"):
            console.print(Markdown(todo["markdown"]))

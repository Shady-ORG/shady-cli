# Shady CLI

This repository contains a simple Python command line interface initialized with [Typer](https://typer.tiangolo.com/).

## Installation

To make the `shady` command available globally, install the package:

```bash
pip install .
```

You can also use [pipx](https://pypa.github.io/pipx/) for an isolated install:

```bash
pipx install .
```

## Usage

After installation, run:

```bash
shady --name Alice
```

Without installing, you can invoke the module directly:

```bash
python -m shady_cli --name Alice
```

# Shady CLI

This repository contains a simple Python command line interface initialized with [Typer](https://typer.tiangolo.com/).

## Installation with Make

Use the Makefile to install everything needed for local usage:

```bash
make install
```

`make install` will:

- install/upgrade packaging dependencies (`pip`, `setuptools`, `wheel`)
- install this project as a user CLI tool (`pip install --user -e .`)
- add an alias to both `~/.bashrc` and `~/.zshrc`:

```bash
alias shady="shady-cli"
```

Reload your shell after installation:

```bash
source ~/.bashrc
# or
source ~/.zshrc
```

Then run:

```bash
shady --name Alice
```

## Uninstall

To remove the CLI and clean aliases from shell startup files:

```bash
make uninstall
```

## Without Make

You can also install directly:

```bash
python3 -m pip install --user -e .
```

Run with:

```bash
shady-cli --name Alice
```

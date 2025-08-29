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

Check 
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.profile
source ~/.bashrc
```

Check if installation worked
```bash
echo $PATH | tr ':' '\n' | grep -x "$HOME/.local/bin" || echo "not installed"
ls -l ~/.local/bin
```

Add this line to your ~/.bashrc or ~/.zshrc if you want a shorter cmd:
```bash 
alias shady="shady-cli"
```

Reload your shell config:
```bash
source ~/.bashrc
```

Now you can run:
```bash
shady --name Nolan
```

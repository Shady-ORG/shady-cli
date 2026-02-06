SHELL := /bin/bash

PACKAGE_NAME := shady-cli
ALIAS_NAME := shady
ALIAS_TARGET := shady-cli
ALIAS_LINE := alias $(ALIAS_NAME)="$(ALIAS_TARGET)"
BASHRC := $(HOME)/.bashrc
ZSHRC := $(HOME)/.zshrc

.PHONY: help install deps cli alias uninstall unalias

help:
	@echo "Available targets:"
	@echo "  make install    - Install dependencies, install CLI for current user, and add alias to ~/.bashrc and ~/.zshrc"
	@echo "  make deps       - Install or upgrade packaging dependencies"
	@echo "  make cli        - Install this package as a user CLI tool"
	@echo "  make alias      - Add alias '$(ALIAS_NAME)' to ~/.bashrc and ~/.zshrc (idempotent)"
	@echo "  make uninstall  - Uninstall the CLI and remove alias from ~/.bashrc and ~/.zshrc"
	@echo "  make unalias    - Remove alias from ~/.bashrc and ~/.zshrc"

install: deps cli alias

deps:
	python3 -m pip install --user --upgrade pip setuptools wheel

cli:
	python3 -m pip install --user -e .

alias:
	@for rc in "$(BASHRC)" "$(ZSHRC)"; do \
		touch "$$rc"; \
		if ! grep -Fqx '$(ALIAS_LINE)' "$$rc"; then \
			if [ -s "$$rc" ] && [ -n "$$(tail -c1 "$$rc")" ]; then printf '\n' >> "$$rc"; fi; \
			echo '$(ALIAS_LINE)' >> "$$rc"; \
			echo "Added alias to $$rc"; \
		else \
			echo "Alias already exists in $$rc"; \
		fi; \
	done
	@echo "Run 'source ~/.bashrc' or 'source ~/.zshrc' to load the alias in current shell."

uninstall: unalias
	-python3 -m pip uninstall -y $(PACKAGE_NAME)

unalias:
	@for rc in "$(BASHRC)" "$(ZSHRC)"; do \
		if [ -f "$$rc" ]; then \
			sed -i '/^alias $(ALIAS_NAME)="$(ALIAS_TARGET)"$$/d' "$$rc"; \
			echo "Removed alias from $$rc (if it existed)"; \
		fi; \
	done

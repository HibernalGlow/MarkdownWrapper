"""marku 包入口：默认委托到 Typer CLI。

示例：
    python -m marku plugins
    python -m marku list
    python -m marku pipeline -c marku/marku_pipeline.toml -i ./docs --dry-run
"""
from __future__ import annotations

from .cli import app


def main():
        app()


if __name__ == "__main__":  # pragma: no cover
        main()

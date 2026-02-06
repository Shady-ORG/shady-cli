"""Command line interface for the shady CLI project."""

import asyncio
from pathlib import Path
from typing import Optional

import typer

from shady_cli.mirror import MirrorCrawler

app = typer.Typer(help="Shady CLI: website mirroring + source extraction")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Start URL to crawl"),
    sources: bool = typer.Option(False, "--sources", "-s", help="Enable source extraction metadata output"),
    result: Path = typer.Option(Path("./out"), "--result", help="Output root folder"),
    max_pages: int = typer.Option(200, "--max-pages", help="Maximum number of pages to crawl"),
    scope: str = typer.Option("same-origin", "--scope", help="Scope rule (same-origin|same-host|all)"),
    include_assets: str = typer.Option("js,css,img,font", "--include-assets", help="Comma list: js,css,img,font"),
    respect_robots: bool = typer.Option(False, "--respect-robots", help="Respect robots.txt (reserved)"),
    depth: int = typer.Option(3, "--depth", help="Maximum crawl depth"),
    concurrency: int = typer.Option(10, "--concurrency", help="Concurrent requests"),
    rate: str = typer.Option("5rps", "--rate", help="Rate limit like 5rps"),
    rewrite_links: bool = typer.Option(True, "--rewrite-links", help="Rewrite links for offline browsing"),
    store_raw: bool = typer.Option(False, "--store-raw", help="Store raw responses for debugging"),
) -> None:
    """Run shady mirror mode directly from root command."""
    if ctx.invoked_subcommand:
        return

    if not url:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    rate_rps = 5.0
    if rate.endswith("rps"):
        rate_rps = float(rate[:-3] or "5")

    crawler = MirrorCrawler(
        base_url=url,
        result_dir=result,
        max_pages=max_pages,
        scope=scope,
        include_assets={x.strip() for x in include_assets.split(",") if x.strip()},
        respect_robots=respect_robots,
        max_depth=depth,
        concurrency=concurrency,
        rate_rps=rate_rps,
        rewrite_links=rewrite_links,
        store_raw=store_raw,
    )
    summary = asyncio.run(crawler.crawl())

    typer.echo("\nMirror completed")
    typer.echo(f"- base_url: {summary['base_url']}")
    typer.echo(f"- visited: {summary['visited']}")
    typer.echo(f"- saved_pages: {summary['saved_pages']}")
    typer.echo(f"- saved_assets: {summary['saved_assets']}")
    typer.echo(f"- output_root: {summary['output_root']}")
    if sources:
        typer.echo(f"- sources metadata: {summary['output_root']}/_meta/crawl.jsonl")


if __name__ == "__main__":
    app()

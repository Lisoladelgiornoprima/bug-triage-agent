"""CLI entry point for Bug Triage Agent."""
import json
import sys

import click
from anthropic import Anthropic
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import config
from src.core.coordinator import Coordinator
from src.tools.github_client import GitHubClient


console = Console()


def setup_logging(level: str = "INFO"):
    """Configure loguru logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
    )


def display_dict_as_table(data: dict, title: str) -> None:
    """Display a dict as a rich table, handling nested data."""
    if "raw_response" in data:
        console.print(Panel(data["raw_response"], title=title, border_style="green"))
        return

    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="white")

    for key, value in data.items():
        if isinstance(value, (list, dict)):
            value_str = json.dumps(value, indent=2, default=str)
        elif value is None:
            value_str = "-"
        else:
            value_str = str(value)
        table.add_row(key, value_str)

    console.print(table)


def init_clients():
    """Validate keys and return initialized clients."""
    try:
        config.validate_keys()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Copy .env.example to .env and fill in your keys.[/yellow]")
        sys.exit(1)

    return (
        Anthropic(api_key=config.anthropic_api_key),
        GitHubClient(token=config.github_token),
    )


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
def cli(log_level):
    """Bug Triage Agent - Automated bug analysis and triage."""
    setup_logging(log_level)


@cli.command()
@click.argument("issue_url")
def analyze(issue_url):
    """Analyze a GitHub issue (Phase 1 only).

    Example:
        python -m src.main analyze https://github.com/psf/requests/issues/6234
    """
    console.print(Panel.fit("Bug Triage Agent - Analyze", style="bold blue"))
    anthropic_client, github_client = init_clients()

    coordinator = Coordinator(anthropic_client, github_client)

    with console.status("[bold green]Analyzing issue..."):
        state = coordinator.run(issue_url)

    if state.status.value == "failed":
        console.print("[red]Analysis failed[/red]")
        for error in state.errors:
            console.print(f"  {error['phase']}: {error['error']}")
        sys.exit(1)

    console.print("[green]Analysis completed[/green]\n")
    display_dict_as_table(state.get("issue_analysis", {}), "Issue Analysis")


@cli.command()
@click.argument("issue_url")
@click.option("--repo", required=True, help="Path to local repository clone")
def triage(issue_url, repo):
    """Full bug triage: analyze issue + locate code + reproduce bug.

    Example:
        python -m src.main triage https://github.com/psf/requests/issues/6655 --repo ./requests
    """
    console.print(Panel.fit("Bug Triage Agent - Full Triage", style="bold blue"))
    anthropic_client, github_client = init_clients()

    coordinator = Coordinator(anthropic_client, github_client, repo_path=repo)

    console.print("[bold]Starting full triage pipeline...[/bold]\n")
    state = coordinator.run(issue_url)

    # Display errors (non-fatal ones)
    if state.errors:
        console.print("[yellow]Warnings:[/yellow]")
        for error in state.errors:
            console.print(f"  {error['phase']}: {error['error']}")
        console.print()

    if state.status.value == "failed":
        console.print("[red]Triage failed[/red]")
        sys.exit(1)

    console.print("[green]Triage completed[/green]\n")

    # Phase 1: Issue Analysis
    analysis = state.get("issue_analysis")
    if analysis:
        display_dict_as_table(analysis, "Phase 1: Issue Analysis")
        console.print()

    # Phase 2: Code Location
    code_loc = state.get("code_location")
    if code_loc:
        display_dict_as_table(code_loc, "Phase 2: Code Location")
        console.print()

    # Phase 3: Bug Reproduction
    reproduction = state.get("bug_reproduction")
    if reproduction:
        display_dict_as_table(reproduction, "Phase 3: Bug Reproduction")
        console.print()

    # Phase 4: Fix Generation
    fix_gen = state.get("fix_generation")
    if fix_gen:
        display_dict_as_table(fix_gen, "Phase 4: Fix Generation")


if __name__ == "__main__":
    cli()
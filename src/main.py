"""CLI entry point for Bug Triage Agent."""
import sys

import click
from anthropic import Anthropic
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
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


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
def cli(log_level):
    """Bug Triage Agent - Automated bug analysis and triage."""
    setup_logging(log_level)


@cli.command()
@click.argument("issue_url")
def analyze(issue_url):
    """Analyze a GitHub issue and extract structured bug information.

    Example:
        python -m src.main analyze https://github.com/psf/requests/issues/6234
    """
    console.print(Panel.fit("Bug Triage Agent", style="bold blue"))

    # Validate API keys
    try:
        config.validate_keys()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Please set up your .env file with required API keys.[/yellow]")
        console.print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)

    # Initialize clients
    anthropic_client = Anthropic(api_key=config.anthropic_api_key)
    github_client = GitHubClient(token=config.github_token)

    # Run analysis
    coordinator = Coordinator(anthropic_client, github_client)

    with console.status("[bold green]Analyzing issue..."):
        state = coordinator.run(issue_url)

    # Display results
    if state.status.value == "failed":
        console.print("[red]Analysis failed[/red]")
        for error in state.errors:
            console.print(f"  Phase: {error['phase']}")
            console.print(f"  Error: {error['error']}")
        sys.exit(1)

    console.print("[green]Analysis completed[/green]\n")

    # Display issue analysis
    analysis = state.get("issue_analysis", {})
    if "raw_response" in analysis:
        console.print(Panel(analysis["raw_response"], title="Analysis", border_style="green"))
    else:
        # Create a formatted table
        table = Table(title="Issue Analysis", show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan", width=20)
        table.add_column("Value", style="white")

        for key, value in analysis.items():
            if isinstance(value, (list, dict)):
                import json
                value_str = json.dumps(value, indent=2)
            else:
                value_str = str(value)
            table.add_row(key, value_str)

        console.print(table)


if __name__ == "__main__":
    cli()
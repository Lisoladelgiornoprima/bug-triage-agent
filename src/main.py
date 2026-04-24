"""CLI entry point for Bug Triage Agent."""
import json
import sys

import click
from anthropic import Anthropic
from loguru import logger
from rich.console import Console
from rich.live import Live
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


PHASE_NAMES = {
    "IssueAnalyzer": ("Phase 1", "Analyzing issue"),
    "CodeLocator": ("Phase 2", "Locating code"),
    "BugReproducer": ("Phase 3", "Reproducing bug"),
    "FixGenerator": ("Phase 4", "Generating fix"),
}


def make_progress_table(events: list[tuple[str, str, str]]) -> Table:
    """Build a live progress table from events."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Phase", style="bold cyan", width=10)
    table.add_column("Status", width=60)

    # Track latest state per agent
    agent_state: dict[str, str] = {}
    for agent_name, event, detail in events:
        phase_label, _ = PHASE_NAMES.get(agent_name, ("?", "?"))
        if event == "start":
            agent_state[agent_name] = "[yellow]Running...[/yellow]"
        elif event == "tool_call":
            agent_state[agent_name] = f"[yellow]Calling tool: {detail}[/yellow]"
        elif event == "done":
            agent_state[agent_name] = f"[green]Done[/green] ({detail})"

    for agent_name, (phase_label, desc) in PHASE_NAMES.items():
        status = agent_state.get(agent_name, "[dim]Pending[/dim]")
        table.add_row(phase_label, f"{desc} - {status}")

    return table


@cli.command()
@click.argument("issue_url")
@click.option("--repo", required=True, help="Path to local repository clone")
@click.option("--output", "-o", type=click.Path(), help="Export results to JSON or Markdown file")
def triage(issue_url, repo, output):
    """Full bug triage: analyze issue + locate code + reproduce bug + suggest fix.

    Example:
        python -m src.main triage https://github.com/psf/requests/issues/6655 --repo ./requests
        python -m src.main triage URL --repo ./repo -o report.json
        python -m src.main triage URL --repo ./repo -o report.md
    """
    console.print(Panel.fit("Bug Triage Agent - Full Triage", style="bold blue"))
    anthropic_client, github_client = init_clients()

    # Progress tracking
    events: list[tuple[str, str, str]] = []
    live = Live(make_progress_table(events), console=console, refresh_per_second=4)

    def on_progress(agent_name: str, event: str, detail: str):
        events.append((agent_name, event, detail))
        live.update(make_progress_table(events))

    coordinator = Coordinator(
        anthropic_client, github_client, repo_path=repo, on_progress=on_progress
    )

    console.print()
    with live:
        state = coordinator.run(issue_url)
    console.print()

    # Display errors
    if state.errors:
        console.print("[yellow]Warnings:[/yellow]")
        for error in state.errors:
            console.print(f"  {error['phase']}: {error['error']}")
        console.print()

    if state.status.value == "failed":
        console.print("[red]Triage failed[/red]")
        sys.exit(1)

    console.print("[green]Triage completed[/green]\n")

    # Display results
    for key, title in [
        ("issue_analysis", "Phase 1: Issue Analysis"),
        ("code_location", "Phase 2: Code Location"),
        ("bug_reproduction", "Phase 3: Bug Reproduction"),
        ("fix_generation", "Phase 4: Fix Generation"),
    ]:
        data = state.get(key)
        if data:
            display_dict_as_table(data, title)
            console.print()

    # Export results
    if output:
        export_results(state, output)


def export_results(state, output_path: str) -> None:
    """Export triage results to JSON or Markdown."""
    results = {
        "issue_analysis": state.get("issue_analysis"),
        "code_location": state.get("code_location"),
        "bug_reproduction": state.get("bug_reproduction"),
        "fix_generation": state.get("fix_generation"),
        "errors": state.errors,
    }

    if output_path.endswith(".md"):
        _export_markdown(results, output_path)
    else:
        _export_json(results, output_path)

    console.print(f"[green]Results exported to {output_path}[/green]")


def _export_json(results: dict, path: str) -> None:
    """Export as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)


def _export_markdown(results: dict, path: str) -> None:
    """Export as Markdown report."""
    lines = ["# Bug Triage Report\n"]

    section_titles = {
        "issue_analysis": "Issue Analysis",
        "code_location": "Code Location",
        "bug_reproduction": "Bug Reproduction",
        "fix_generation": "Fix Generation",
    }

    for key, title in section_titles.items():
        data = results.get(key)
        if not data:
            continue
        lines.append(f"\n## {title}\n")
        if "raw_response" in data:
            lines.append(data["raw_response"])
        else:
            for field, value in data.items():
                if isinstance(value, (list, dict)):
                    lines.append(f"**{field}**:\n```json\n{json.dumps(value, indent=2, default=str)}\n```\n")
                else:
                    lines.append(f"**{field}**: {value}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
def web(host, port):
    """Start the Web UI server.

    Example:
        python -m src.main web --port 8000
    """
    try:
        import uvicorn
        from src.web.app import app

        console.print(Panel.fit("Bug Triage Agent - Web UI", style="bold blue"))
        console.print(f"[green]Starting server at http://{host}:{port}[/green]")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

        uvicorn.run(app, host=host, port=port, log_level="info")
    except ImportError:
        console.print("[red]Error: FastAPI and uvicorn are required for Web UI[/red]")
        console.print("[yellow]Install with: pip install fastapi uvicorn[standard][/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    cli()

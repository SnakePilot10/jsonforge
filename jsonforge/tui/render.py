from collections.abc import Sequence

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def render_search_results(
    query: str,
    rows: Sequence[tuple[int, str, str, str]],
) -> None:
    table = Table(box=box.SIMPLE, expand=True, show_header=True)
    table.add_column("#", justify="right", width=3)
    table.add_column("Path", ratio=3, overflow="fold")
    table.add_column("Type", ratio=1)
    table.add_column("Value", ratio=2, overflow="ellipsis")
    for index, path, value_type, preview in rows:
        table.add_row(str(index), path, value_type, preview)
    console.print(Panel(table, title=f'Results for "{query}"', border_style="cyan"))


def render_path_summary(
    path: str,
    value_type: str,
    *,
    storage: str | None = None,
    child_count: int | None = None,
    current_value: str | None = None,
) -> None:
    lines = [Text.assemble(("Path: ", "bold"), path), Text.assemble(("Type: ", "bold"), value_type)]
    if storage is not None:
        lines.append(Text.assemble(("Storage: ", "bold"), storage))
    if child_count is not None:
        lines.append(Text.assemble(("Content: ", "bold"), f"{child_count} child entries"))
    if current_value is not None:
        lines.append(Text.assemble(("Current value: ", "bold"), current_value))
    console.print(Panel(Group(*lines), border_style="blue"))


def render_container_children(
    rows: Sequence[tuple[int, str, str, str]],
    *,
    omitted: int = 0,
) -> None:
    table = Table(box=box.SIMPLE, expand=True, show_header=True)
    table.add_column("#", justify="right", width=3)
    table.add_column("Child", ratio=3, overflow="fold")
    table.add_column("Type", ratio=1)
    table.add_column("Value", ratio=2, overflow="ellipsis")
    for index, child, value_type, preview in rows:
        table.add_row(str(index), child, value_type, preview)
    if omitted:
        table.caption = f"{omitted} more entries"
    console.print(table)


def render_change_preview(
    path: str,
    old_value: str,
    new_value: str,
    old_type: str,
    new_type: str,
) -> None:
    content = Group(
        Text.assemble(("Path: ", "bold"), path),
        Text.assemble(("Old:  ", "bold"), old_value),
        Text.assemble(("New:  ", "bold"), new_value),
        Text.assemble(("Type: ", "bold"), f"{old_type} -> {new_type}"),
    )
    console.print(Panel(content, title="Pending change", border_style="yellow"))


def render_status(message: str, *, kind: str = "info") -> None:
    styles = {
        "error": "bold red",
        "success": "bold green",
        "warning": "bold yellow",
        "info": "",
    }
    console.print(Text(message, style=styles[kind]))

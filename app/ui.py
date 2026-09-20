from __future__ import annotations

import sys

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from app.ooni import CountryVerdict, MIN_RELIABLE_MEASUREMENTS
from app.netinfo import SiteDetails

WHITE = "white"
GREY = "grey62"

LOGO = r"""__   _____ ___ _
\ \ / / __|_ _| |
 \ V /| _| | || |__
  \_/ |___|___|____|
  
  """

console = Console(highlight=False)

def clear_screen() -> None:
    console.clear()


STATUS_STYLE = {
    "blocked": ("BLOCKED", "confirmed by OONI probes"),
    "likely_blocked": ("LIKELY BLOCKED", "high anomaly rate in probe data"),
    "reachable": ("REACHABLE", "no significant blocking signal"),
    "no_data": ("NO DATA", "not enough OONI measurements to judge"),
}

STATUS_PRIORITY = {"blocked": 0, "likely_blocked": 1, "reachable": 2, "no_data": 3}

def print_banner() -> None:
    logo = Text(LOGO, style=f"bold {WHITE}")
    tagline = Text("  ·  an OSINT tool that checks whether a site is blocked in a given country  ·  ", style=GREY)
    console.print()
    console.print(Align.center(logo))
    console.print(Align.center(tagline))
    console.print()


def print_intro_box() -> None:
    body = Text()
    body.append("Type a site to scan it, e.g. ", style=GREY)
    body.append("youtube.com", style=f"bold {WHITE}")
    body.append("\n")
    body.append("Then a country code (or name), e.g. ", style=GREY)
    body.append("PS", style=f"bold {WHITE}")
    body.append(" or ", style=GREY)
    body.append("Palestine", style=f"bold {WHITE}")
    body.append(", leave blank to see all blocked countries.\n\n", style=GREY)
    body.append("Commands: ", style=GREY)
    body.append("help", style=f"bold {WHITE}")
    body.append("  ", style=GREY)
    body.append("exit", style=f"bold {WHITE}")
    panel = Panel(
        body,
        title="[bold]what to do[/bold]",
        title_align="left",
        border_style=GREY,
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()

def prompt_in_box(label: str) -> str:
    width = min(console.width - 4, 70)
    inner_width = width - 2
    top = f"╭{'─' * inner_width}╮"
    bottom = f"╰{'─' * inner_width}╯"

    prefix_visible = f" › {label} "
    padding_len = max(0, inner_width - len(prefix_visible))

    console.print(f"[{GREY}]{top}[/{GREY}]")
    console.print(
        f"[{GREY}]│[/{GREY}][bold {WHITE}] [/bold {WHITE}][{GREY}]› [/{GREY}]"
        f"{label} {' ' * padding_len}[{GREY}]│[/{GREY}]"
    )
    console.print(f"[{GREY}]{bottom}[/{GREY}]")

    input_col = len(prefix_visible) + 2
    sys.stdout.write(f"\x1b[2A\x1b[{input_col}G")
    sys.stdout.flush()

    value = input().strip()

    sys.stdout.write("\n")
    sys.stdout.flush()

    return value

def prompt_site() -> str:
    return prompt_in_box("site to scan = ")


def prompt_country() -> str:
    return prompt_in_box("country (leave it blank to list all) = ")


def status_line(msg: str, style: str = GREY) -> None:
    console.print(f"[{style}]{msg}[/{style}]")


def error_line(msg: str) -> None:
    console.print(f"[bold {WHITE}]✕ {msg}[/bold {WHITE}]")


def spinner(message: str):
    return console.status(f"[{GREY}]{message}[/{GREY}]", spinner="dots")


def render_site_details(details: SiteDetails) -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(style=GREY, justify="right")
    table.add_column(style=WHITE)

    table.add_row("domain", details.domain)
    if details.resolve_error:
        table.add_row("resolve", f"[bold {WHITE}]failed — {details.resolve_error}[/bold {WHITE}]")
        console.print(
            Panel(table, title="[bold]site details[/bold]", title_align="left",
                  border_style=GREY, box=ROUNDED, padding=(1, 2))
        )
        return

    table.add_row("ip", details.ip or "—")
    if details.org or details.isp:
        table.add_row("host", details.org or details.isp or "—")
    if details.asn:
        table.add_row("asn", details.asn)
    if details.host_country:
        table.add_row("hosted in", details.host_country)
    if details.http_status:
        table.add_row("http", f"[bold {WHITE}]{details.http_status}[/bold {WHITE}]"
                               f"  ({details.final_url})")
    elif details.http_error:
        table.add_row("http", f"[{GREY}]unreachable from here[/{GREY}]")
    if details.title:
        table.add_row("title", details.title)

    console.print(
        Panel(table, title="[bold]site details[/bold]", title_align="left",
              border_style=GREY, box=ROUNDED, padding=(1, 2))
    )


def render_country_verdict(verdict: CountryVerdict, country_label: str) -> None:
    label, note = STATUS_STYLE[verdict.status]
    header = Text()
    header.append(f"{country_label} ({verdict.country_code})  ", style=f"bold {WHITE}")
    header.append(label, style=f"bold {WHITE}")

    table = Table.grid(padding=(0, 1))
    table.add_column(style=GREY, justify="right")
    table.add_column(style=WHITE)
    table.add_row("measurements", str(verdict.measurement_count))
    table.add_row("confirmed blocked", str(verdict.confirmed_count))
    table.add_row("anomalous", str(verdict.anomaly_count))
    table.add_row("ok", str(verdict.ok_count))
    table.add_row("note", note)

    console.print(
        Panel(
            Group(header, Text(""), table),
            title="[bold]block status[/bold]",
            title_align="left",
            border_style=GREY,
            box=ROUNDED,
            padding=(1, 2),
        )
    )


def render_country_list(
    verdicts: list[CountryVerdict],
    domain: str,
    days_used: int | None = None,
    page_size: int = 20,
) -> None:
    if not verdicts:
        console.print(Panel(
            f"No OONI measurement data found for [bold {WHITE}]{domain}[/bold {WHITE}].",
            border_style=GREY, box=ROUNDED, padding=(1, 2),
        ))
        return

    counts = {"blocked": 0, "likely_blocked": 0, "reachable": 0, "no_data": 0}
    for v in verdicts:
        counts[v.status] += 1

    ordered = sorted(
        verdicts,
        key=lambda v: (STATUS_PRIORITY[v.status], -v.confirmed_count, -v.anomaly_count, -v.measurement_count),
    )

    pages = [ordered[i:i + page_size] for i in range(0, len(ordered), page_size)]
    window_note = f" (last {days_used} days)" if days_used else ""

    for page_num, page in enumerate(pages, start=1):
        table = Table(
            box=ROUNDED, border_style=GREY, show_lines=False,
            title=f"countries with data for [bold {WHITE}]{domain}[/bold {WHITE}]{window_note}"
                  f"  —  page {page_num}/{len(pages)}",
            title_justify="left",
        )
        table.add_column("country", style=WHITE)
        table.add_column("status", justify="left", style=WHITE)
        table.add_column("confirmed", justify="right", style=GREY)
        table.add_column("anomalous", justify="right", style=GREY)
        table.add_column("measurements", justify="right", style=GREY)

        for v in page:
            label, _ = STATUS_STYLE[v.status]
            table.add_row(
                v.country_code,
                label,
                str(v.confirmed_count),
                str(v.anomaly_count),
                str(v.measurement_count),
            )

        with console.capture() as capture:
            console.print(table)
        rendered = capture.get()
        console.file.write(rendered)
        console.file.flush()
        table_lines = rendered.count("\n")

        if page_num < len(pages):
            console.input(f"[{GREY}]-- press Enter for next page ({page_num}/{len(pages)}) --[/{GREY}] ")
            lines_to_clear = table_lines + 1
            sys.stdout.write(f"\x1b[{lines_to_clear}A\x1b[0J")
            sys.stdout.flush()

    summary = Text()
    summary.append(f"{counts['blocked']} blocked", style=f"bold {WHITE}")
    summary.append("  ·  ", style=GREY)
    summary.append(f"{counts['likely_blocked']} likely blocked", style=f"bold {WHITE}")
    summary.append("  ·  ", style=GREY)
    summary.append(f"{counts['reachable']} reachable", style=GREY)
    summary.append("  ·  ", style=GREY)
    summary.append(f"{counts['no_data']} no data (fewer than {MIN_RELIABLE_MEASUREMENTS} measurements)", style=GREY)
    console.print(Padding(summary, (0, 1)))


def print_help() -> None:
    console.print(Panel(
        f"[bold {WHITE}]veil <site>[/bold {WHITE}] [{GREY}][--country CC] [--list][/{GREY}]\n\n"
        "Run with no arguments to start an interactive session.\n"
        "In the session, just type a domain, then a country (or leave it "
        "blank to see every country with blocking signal).\n\n"
        f"[{GREY}]Data comes from OONI's crowdsourced probe network — treat "
        f"results as a strong signal, not certainty.[/{GREY}]",
        title="[bold]help[/bold]", title_align="left",
        border_style=GREY, box=ROUNDED, padding=(1, 2),
    ))

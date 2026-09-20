from __future__ import annotations

import argparse
import sys

from app import ui
from app.country_table import CANONICAL_NAMES, COUNTRY_CODES
from app.netinfo import gather_site_details
from app.ooni import OoniError, aggregate_by_country, aggregate_for_country

def resolve_country(raw: str) -> tuple[str, str] | None:
    raw = raw.strip()
    if not raw:
        return None
    if len(raw) == 2 and raw.upper() in CANONICAL_NAMES:
        code = raw.upper()
        return code, CANONICAL_NAMES[code]
    for name, code in COUNTRY_CODES.items():
        if name.lower() == raw.lower():
            return code, CANONICAL_NAMES.get(code, name)
    for name, code in COUNTRY_CODES.items():
        if raw.lower() in name.lower():
            return code, CANONICAL_NAMES.get(code, name)
    return None


def run_scan(domain: str, country_raw: str | None) -> None:
    with ui.spinner(f"looking up {domain}..."):
        details = gather_site_details(domain)
    ui.render_site_details(details)

    if details.resolve_error:
        return

    if country_raw:
        resolved = resolve_country(country_raw)
        if not resolved:
            ui.error_line(
                f"couldn't recognize country '{country_raw}' — try a 2-letter "
                f"code like IR, or a full name like Iran."
            )
            return
        code, name = resolved
        try:
            with ui.spinner(f"querying OONI for {domain} in {name} (can take up to a minute)..."):
                verdict = aggregate_for_country(details.domain, code)
        except OoniError as exc:
            ui.error_line(str(exc))
            return
        ui.render_country_verdict(verdict, name)
    else:
        try:
            with ui.spinner(f"querying OONI across all countries for {domain} (can take up to a minute)..."):
                verdicts, days_used = aggregate_by_country(details.domain)
        except OoniError as exc:
            ui.error_line(str(exc))
            return
        ui.render_country_list(verdicts, details.domain, days_used)


def interactive_loop() -> None:
    ui.clear_screen()
    ui.print_banner()
    ui.print_intro_box()
    while True:
        try:
            site = ui.prompt_site()
        except (KeyboardInterrupt, EOFError):
            ui.console.print()
            break

        if not site:
            continue
        if site.lower() in ("exit", "quit", "q"):
            break
        if site.lower() in ("help", "?"):
            ui.print_help()
            continue

        try:
            country = ui.prompt_country()
        except (KeyboardInterrupt, EOFError):
            ui.console.print()
            break

        ui.console.print()
        run_scan(site, country or None)
        ui.console.print()

    ui.status_line("goodbye.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veil",
        description="Check whether a site is blocked in a given country, using OONI data.",
    )
    parser.add_argument("site", nargs="?", help="domain to check, e.g. youtube.com")
    parser.add_argument("--country", "-c", help="country code or name, e.g. IR or Iran")
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="list all countries with blocking signal for this site (ignores --country)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.site:
        interactive_loop()
        return

    ui.print_banner()
    country = None if args.list else args.country
    run_scan(args.site, country)


if __name__ == "__main__":
    main()

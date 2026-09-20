from __future__ import annotations

import datetime as _dt
import time
from dataclasses import dataclass

import requests

API_BASE = "https://api.ooni.io/api/v1/aggregation"
USER_AGENT = "veil-cli/0.1 (+https://ooni.org)"
TIMEOUT = 120

MIN_RELIABLE_MEASUREMENTS = 5
ANOMALY_RATIO_THRESHOLD = 0.3

LIST_WINDOWS_DAYS = [365, 180, 90, 30, 14]


@dataclass
class CountryVerdict:
    country_code: str
    measurement_count: int
    confirmed_count: int
    anomaly_count: int
    ok_count: int
    failure_count: int

    @property
    def anomaly_ratio(self) -> float:
        if self.measurement_count == 0:
            return 0.0
        return (self.anomaly_count + self.confirmed_count) / self.measurement_count

    @property
    def status(self) -> str:
        if self.measurement_count < MIN_RELIABLE_MEASUREMENTS:
            return "no_data"
        if self.confirmed_count > 0:
            return "blocked"
        if self.anomaly_ratio >= ANOMALY_RATIO_THRESHOLD:
            return "likely_blocked"
        return "reachable"


class OoniError(RuntimeError):
    pass


def _default_since_country(years_back: int = 1) -> str:
    d = _dt.date.today() - _dt.timedelta(days=365 * years_back)
    return d.isoformat()


def _since_days_ago(days_back: int) -> str:
    d = _dt.date.today() - _dt.timedelta(days=days_back)
    return d.isoformat()


def _default_until() -> str:
    return _dt.date.today().isoformat()


def _get(params: dict, retries: int = 2) -> dict:
    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                API_BASE,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
            if resp.status_code >= 500:
                last_exc = OoniError(f"OONI's server is overloaded (HTTP {resp.status_code})")
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = OoniError(f"couldn't reach the OONI API: {exc}")
            time.sleep(2 * (attempt + 1))
        except ValueError as exc:
            raise OoniError("OONI API returned a non-JSON response") from exc
    raise last_exc


def aggregate_for_country(
    domain: str,
    country_code: str,
    since: str | None = None,
    until: str | None = None,
) -> CountryVerdict:
    params = {
        "domain": domain,
        "probe_cc": country_code.upper(),
        "test_name": "web_connectivity",
        "since": since or _default_since_country(),
        "until": until or _default_until(),
    }
    data = _get(params)
    result = data.get("result") or {}
    if isinstance(result, list):
        result = result[0] if result else {}
    return CountryVerdict(
        country_code=country_code.upper(),
        measurement_count=result.get("measurement_count", 0) or 0,
        confirmed_count=result.get("confirmed_count", 0) or 0,
        anomaly_count=result.get("anomaly_count", 0) or 0,
        ok_count=result.get("ok_count", 0) or 0,
        failure_count=result.get("failure_count", 0) or 0,
    )


def aggregate_by_country(
    domain: str,
    until: str | None = None,
) -> tuple[list[CountryVerdict], int]:
    """Returns (verdicts, days_used) — tries the widest window first for the
    best data coverage, and only falls back to a narrower window if OONI's
    backend can't complete the query in time."""
    last_exc = None
    for days in LIST_WINDOWS_DAYS:
        params = {
            "domain": domain,
            "axis_x": "probe_cc",
            "test_name": "web_connectivity",
            "since": _since_days_ago(days),
            "until": until or _default_until(),
        }
        try:
            data = _get(params, retries=2)
        except OoniError as exc:
            last_exc = exc
            continue

        rows = data.get("result") or []
        verdicts = []
        for row in rows:
            cc = row.get("probe_cc")
            if not cc or cc == "ZZ":
                continue
            verdicts.append(
                CountryVerdict(
                    country_code=cc,
                    measurement_count=row.get("measurement_count", 0) or 0,
                    confirmed_count=row.get("confirmed_count", 0) or 0,
                    anomaly_count=row.get("anomaly_count", 0) or 0,
                    ok_count=row.get("ok_count", 0) or 0,
                    failure_count=row.get("failure_count", 0) or 0,
                )
            )
        verdicts.sort(
            key=lambda v: (v.confirmed_count, v.anomaly_count, v.measurement_count),
            reverse=True,
        )
        return verdicts, days

    raise last_exc
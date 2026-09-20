from __future__ import annotations

import re
import socket
from dataclasses import dataclass, field

import requests

HTTP_TIMEOUT = 8
GEOIP_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,isp,org,as"
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass
class SiteDetails:
    domain: str
    ip: str | None = None
    resolve_error: str | None = None
    http_status: int | None = None
    http_error: str | None = None
    server_header: str | None = None
    title: str | None = None
    final_url: str | None = None
    isp: str | None = None
    org: str | None = None
    asn: str | None = None
    host_country: str | None = None


def _clean_domain(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^\w+://", "", raw)
    raw = raw.split("/")[0]
    raw = raw.split(":")[0]
    return raw


def resolve(domain: str) -> tuple[str | None, str | None]:
    try:
        ip = socket.gethostbyname(domain)
        return ip, None
    except socket.gaierror as exc:
        return None, str(exc)


def probe_http(domain: str) -> dict:
    out = {"http_status": None, "http_error": None, "server_header": None,
            "title": None, "final_url": None}
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            resp = requests.get(
                url,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 (compatible; veil-cli/0.1)"},
                allow_redirects=True,
            )
            out["http_status"] = resp.status_code
            out["server_header"] = resp.headers.get("Server")
            out["final_url"] = resp.url
            match = TITLE_RE.search(resp.content[:8192])
            if match:
                title = match.group(1).decode("utf-8", errors="ignore")
                out["title"] = re.sub(r"\s+", " ", title).strip()[:120]
            return out
        except requests.RequestException as exc:
            out["http_error"] = str(exc)
            continue
    return out


def geoip_lookup(ip: str) -> dict:
    out = {"isp": None, "org": None, "asn": None, "host_country": None}
    try:
        resp = requests.get(GEOIP_URL.format(ip=ip), timeout=6)
        data = resp.json()
        if data.get("status") == "success":
            out["isp"] = data.get("isp")
            out["org"] = data.get("org")
            out["asn"] = data.get("as")
            out["host_country"] = data.get("country")
    except (requests.RequestException, ValueError):
        pass
    return out


def gather_site_details(raw_domain: str) -> SiteDetails:
    domain = _clean_domain(raw_domain)
    details = SiteDetails(domain=domain)

    ip, err = resolve(domain)
    details.ip = ip
    details.resolve_error = err

    if ip:
        http_info = probe_http(domain)
        details.http_status = http_info["http_status"]
        details.http_error = http_info["http_error"]
        details.server_header = http_info["server_header"]
        details.title = http_info["title"]
        details.final_url = http_info["final_url"]

        geo = geoip_lookup(ip)
        details.isp = geo["isp"]
        details.org = geo["org"]
        details.asn = geo["asn"]
        details.host_country = geo["host_country"]

    return details

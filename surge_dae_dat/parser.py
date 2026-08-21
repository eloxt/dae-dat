"""Parsers for the domain and IP rule formats in SukkaW/Surge."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from pathlib import Path

from .protobuf import Cidr, Domain, GeoIp, GeoSite


@dataclass
class ParseResult:
    domains: list[Domain] = field(default_factory=list)
    cidrs: list[Cidr] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _clean(line: str) -> str:
    line = line.lstrip("\ufeff").strip()
    if not line or line.startswith("#") or line.startswith("#!"):
        return ""
    # Surge uses # for comments in all of the source lists. Keep the common
    # URL/regex values intact; a literal # in a rule is uncommon and can be
    # supplied from a local source if needed.
    if "#" in line:
        line = line.split("#", 1)[0].rstrip()
    return line


def _domain(value: str) -> str:
    value = value.strip().lower().rstrip(".")
    if value.startswith("*."):
        value = value[2:]
    return value


def _wildcard_regex(value: str) -> str:
    escaped = re.escape(value.strip().lower())
    return "^" + escaped.replace(r"\*", ".*").replace(r"\?", ".") + "$"


def parse_domainset(text: str, source: str = "domainset") -> ParseResult:
    result = ParseResult()
    seen: set[tuple[int, str]] = set()
    for number, raw in enumerate(text.splitlines(), 1):
        line = _clean(raw)
        if not line or line.startswith("$") or line.startswith("["):
            continue
        suffix = line.startswith(".")
        value = _domain(line[1:] if suffix else line)
        if not value or "/" in value or "," in value:
            result.warnings.append(f"{source}:{number}: skipped invalid domain {line!r}")
            continue
        item = (2 if suffix else 3, value)
        if item not in seen:
            seen.add(item)
            result.domains.append(Domain(*item))
    return result


_DOMAIN_TYPES = {
    "DOMAIN": 3,
    "DOMAIN-SUFFIX": 2,
    "DOMAIN-KEYWORD": 0,
}


def parse_ruleset(text: str, source: str = "ruleset") -> ParseResult:
    result = ParseResult()
    seen_domains: set[tuple[int, str]] = set()
    seen_cidrs: set[str] = set()
    for number, raw in enumerate(text.splitlines(), 1):
        line = _clean(raw)
        if not line or line.startswith("$") or line.startswith("["):
            continue
        kind, sep, value = line.partition(",")
        if not sep:
            result.warnings.append(f"{source}:{number}: skipped non-rule line {line!r}")
            continue
        kind = kind.strip().upper()
        value = value.strip().split(",", 1)[0].strip()
        if kind in _DOMAIN_TYPES:
            value = _domain(value)
            if not value or "/" in value:
                result.warnings.append(f"{source}:{number}: skipped invalid domain {value!r}")
                continue
            item = (_DOMAIN_TYPES[kind], value)
            if item not in seen_domains:
                seen_domains.add(item)
                result.domains.append(Domain(*item))
        elif kind == "DOMAIN-WILDCARD":
            if value:
                item = (1, _wildcard_regex(value))
                if item not in seen_domains:
                    seen_domains.add(item)
                    result.domains.append(Domain(*item))
        elif kind == "URL-REGEX":
            result.warnings.append(f"{source}:{number}: URL-REGEX cannot be represented as a domain geodata rule; skipped")
        elif kind in ("IP-CIDR", "IP-CIDR6"):
            try:
                network = ipaddress.ip_network(value, strict=False)
            except ValueError:
                result.warnings.append(f"{source}:{number}: skipped invalid CIDR {value!r}")
                continue
            if kind == "IP-CIDR" and network.version != 4:
                result.warnings.append(f"{source}:{number}: IP-CIDR contains IPv6 value; skipped")
                continue
            if kind == "IP-CIDR6" and network.version != 6:
                result.warnings.append(f"{source}:{number}: IP-CIDR6 contains IPv4 value; skipped")
                continue
            normalized = str(network)
            if normalized not in seen_cidrs:
                seen_cidrs.add(normalized)
                result.cidrs.append(Cidr(network))
        elif kind in {"GEOIP", "IP-ASN", "SRC-IP", "SRC-PORT", "DEST-PORT", "PROTOCOL", "PROCESS-NAME", "USER-AGENT"}:
            result.warnings.append(f"{source}:{number}: {kind} is not representable in GeoSite/GeoIP dat; skipped")
        else:
            result.warnings.append(f"{source}:{number}: unsupported Surge rule {kind}; skipped")
    return result


def parse_file(path: Path, kind: str) -> ParseResult:
    text = path.read_text(encoding="utf-8-sig")
    if kind == "domainset":
        return parse_domainset(text, str(path))
    if kind in {"ruleset", "ip"}:
        return parse_ruleset(text, str(path))
    raise ValueError(f"unknown source kind: {kind}")


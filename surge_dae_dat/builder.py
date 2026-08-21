"""Build deterministic dae geodata files from Surge sources."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .github import RemoteSource, fetch_sources
from .parser import parse_domainset, parse_ruleset
from .protobuf import GeoIp, GeoSite, encode_geoip, encode_geosite

DEFAULT_REPO = "SukkaW/Surge"
DEFAULT_REF = "master"


@dataclass
class BuildSummary:
    source: str
    domain_entries: int = 0
    ip_entries: int = 0
    warnings: list[str] | None = None
    files: list[str] | None = None
    entries: list[dict[str, object]] | None = None


def _tag(path: str, used: set[str]) -> str:
    stem = Path(path).with_suffix("").name.lower().replace("_", "-")
    if stem not in used:
        used.add(stem)
        return stem
    parent = Path(path).parent.name.lower().replace("_", "-")
    candidate = f"{parent}-{stem}"
    index = 2
    while candidate in used:
        candidate = f"{parent}-{stem}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _local_sources(root: Path) -> list[RemoteSource]:
    sources: list[RemoteSource] = []
    for path in sorted(root.glob("Source/domainset/*.conf")):
        sources.append(RemoteSource(str(path.relative_to(root)), "domainset", path.read_text(encoding="utf-8-sig")))
    for path in sorted(root.glob("Source/non_ip/*.conf")):
        sources.append(RemoteSource(str(path.relative_to(root)), "ruleset", path.read_text(encoding="utf-8-sig")))
    for path in sorted(root.glob("Source/ip/*.conf")):
        sources.append(RemoteSource(str(path.relative_to(root)), "ip", path.read_text(encoding="utf-8-sig")))
    if not sources:
        raise RuntimeError(f"no Source/* rules found under {root}")
    return sources


def build(output_dir: Path, source_dir: Path | None = None, repo: str = DEFAULT_REPO, ref: str = DEFAULT_REF,
          timeout: float = 30.0) -> BuildSummary:
    sources = _local_sources(source_dir) if source_dir else fetch_sources(repo, ref, timeout)
    sites: list[GeoSite] = []
    ips: list[GeoIp] = []
    warnings: list[str] = []
    used_tags: set[str] = set()
    manifest_entries: list[dict[str, object]] = []
    for source in sources:
        tag = _tag(source.path, used_tags)
        result = parse_domainset(source.text, source.path) if source.kind == "domainset" else parse_ruleset(source.text, source.path)
        warnings.extend(result.warnings)
        manifest_entries.append({
            "source": source.path,
            "kind": source.kind,
            "tag": tag,
            "domain_count": len(result.domains),
            "cidr_count": len(result.cidrs),
        })
        if result.domains:
            sites.append(GeoSite(tag, tuple(sorted(result.domains))))
        if result.cidrs:
            cidrs = tuple(sorted(result.cidrs, key=lambda item: (
                item.network.version,
                int(item.network.network_address),
                item.network.prefixlen,
            )))
            ips.append(GeoIp(tag, cidrs))
    files: list[str] = []
    if sites:
        path = output_dir / "surge-geosite.dat"
        _atomic_write(path, encode_geosite(sorted(sites)))
        files.append(path.name)
    if ips:
        path = output_dir / "surge-geoip.dat"
        _atomic_write(path, encode_geoip(sorted(ips)))
        files.append(path.name)
    summary = BuildSummary(
        source=f"local:{source_dir}" if source_dir else f"github:{repo}@{ref}",
        domain_entries=sum(len(site.domains) for site in sites),
        ip_entries=sum(len(entry.cidrs) for entry in ips),
        warnings=warnings,
        files=files,
        entries=manifest_entries,
    )
    manifest = {**asdict(summary), "sha256": {name: hashlib.sha256((output_dir / name).read_bytes()).hexdigest() for name in files}}
    _atomic_write(output_dir / "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
    return summary

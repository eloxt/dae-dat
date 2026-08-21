"""Download rule sources from a GitHub repository without external packages."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class RemoteSource:
    path: str
    kind: str
    text: str


def _get(url: str, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "surge-dae-dat/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_sources(repo: str, ref: str, timeout: float = 30.0) -> list[RemoteSource]:
    owner, name = repo.rstrip("/").removesuffix(".git").split("/")[-2:]
    tree_url = f"https://api.github.com/repos/{owner}/{name}/git/trees/{ref}?recursive=1"
    tree = json.loads(_get(tree_url, timeout))
    if tree.get("truncated"):
        raise RuntimeError("GitHub tree response was truncated; use --source-dir instead")
    sources: list[RemoteSource] = []
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if item.get("type") != "blob" or not path.endswith(".conf"):
            continue
        if path.startswith("Source/domainset/"):
            kind = "domainset"
        elif path.startswith("Source/non_ip/"):
            kind = "ruleset"
        elif path.startswith("Source/ip/"):
            kind = "ip"
        else:
            continue
        raw_url = f"https://raw.githubusercontent.com/{owner}/{name}/{ref}/{path}"
        sources.append(RemoteSource(path, kind, _get(raw_url, timeout).decode("utf-8-sig")))
    if not sources:
        raise RuntimeError(f"no Surge source rules found in {repo}@{ref}")
    return sorted(sources, key=lambda item: item.path)


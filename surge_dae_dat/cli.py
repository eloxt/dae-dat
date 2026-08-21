from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .builder import DEFAULT_REF, DEFAULT_REPO, build


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate dae-compatible .dat files from SukkaW/Surge rules")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("command", nargs="?", choices=("build",), default="build", help="operation (default: build)")
    p.add_argument("--source-dir", type=Path, help="local Surge checkout; skips GitHub download")
    p.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repository (default: {DEFAULT_REPO})")
    p.add_argument("--ref", default=DEFAULT_REF, help=f"Git ref (default: {DEFAULT_REF})")
    p.add_argument("--output-dir", type=Path, default=Path("dist"), help="output directory (default: dist)")
    p.add_argument("--timeout", type=float, default=30.0, help="network timeout in seconds")
    p.add_argument("--quiet", action="store_true", help="only print errors")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        summary = build(args.output_dir, args.source_dir, args.repo, args.ref, args.timeout)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"source: {summary.source}")
        print(f"domain entries: {summary.domain_entries}")
        print(f"IP entries: {summary.ip_entries}")
        print(f"files: {', '.join(summary.files or [])}")
        if summary.warnings:
            print(f"warnings: {len(summary.warnings)} (see {args.output_dir / 'manifest.json'})", file=sys.stderr)
    return 0

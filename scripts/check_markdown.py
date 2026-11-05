#!/usr/bin/env python3
"""Validate local Markdown links, anchors, and common fence lookalikes."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FENCE_LOOKALIKES = {"｀": "U+FF40 FULLWIDTH GRAVE ACCENT"}


def slugify(value: str) -> str:
    value = re.sub(r"[\x60*_{}\[\]<>]", "", value.strip().lower())
    value = re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", value).strip("-")


def anchors(text: str) -> set[str]:
    found: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        base = slugify(match.group(1))
        if not base:
            continue
        index = counts.get(base, 0)
        counts[base] = index + 1
        found.add(base if index == 0 else f"{base}-{index}")
    return found


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"{path}: invalid UTF-8: {exc}"]

    for char, name in FENCE_LOOKALIKES.items():
        if char in text:
            errors.append(f"{path}: contains {name}; use an ASCII backtick")

    for line_number, line in enumerate(text.splitlines(), 1):
        for match in LINK.finditer(line):
            raw = match.group(1).strip()
            target = raw.split(maxsplit=1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("//"):
                continue

            relative = unquote(parsed.path)
            destination = path if not relative else (path.parent / relative).resolve()
            if relative and not destination.exists():
                errors.append(f"{path}:{line_number}: missing local target {relative!r}")
                continue

            if parsed.fragment:
                if destination.suffix.lower() != ".md":
                    continue
                try:
                    destination_text = destination.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    errors.append(f"{path}:{line_number}: cannot read {destination}: {exc}")
                    continue
                if unquote(parsed.fragment).lower() not in anchors(destination_text):
                    errors.append(
                        f"{path}:{line_number}: missing Markdown anchor #{parsed.fragment}"
                    )
    return errors


def main() -> int:
    markdown_files = sorted(Path(".").glob("**/*.md"))
    errors = [error for path in markdown_files for error in check_file(path)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {len(markdown_files)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

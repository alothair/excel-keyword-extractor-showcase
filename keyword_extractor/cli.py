"""Command-line entry point."""

from __future__ import annotations

import argparse
import csv
from io import StringIO
import json
from pathlib import Path
import sys

from .engine import extract_keywords
from .workbook import WorkbookError, read_rows


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Rank keywords in CSV or XLSX rows.")
    result.add_argument("input", type=Path)
    result.add_argument("--columns", nargs="+", help="Header names to analyze; defaults to every column")
    result.add_argument("--top", type=int, default=20)
    result.add_argument("--stop-word", action="append", default=[])
    result.add_argument("--no-phrases", action="store_true")
    result.add_argument("--format", choices=("json", "csv"), default="json")
    result.add_argument("--output", type=Path, help="Write output to a file instead of stdout")
    return result


def run(arguments: list[str] | None = None) -> int:
    args = parser().parse_args(arguments)
    try:
        rows = read_rows(args.input)
        available = list(rows[0]) if rows else []
        columns = args.columns or available
        missing = [column for column in columns if column not in available]
        if missing:
            raise WorkbookError(f"unknown columns: {', '.join(missing)}")
        documents = [" ".join(row.get(column, "") for column in columns) for row in rows]
        keywords = extract_keywords(documents, top=args.top, stop_words=args.stop_word, include_phrases=not args.no_phrases)
    except (OSError, WorkbookError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        content = json.dumps({"source": args.input.name, "documents": len(rows), "columns": columns, "keywords": [item.to_dict() for item in keywords]}, indent=2, ensure_ascii=False) + "\n"
    else:
        buffer = StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=("keyword", "score", "occurrences", "document_frequency"))
        writer.writeheader()
        writer.writerows(item.to_dict() for item in keywords)
        content = buffer.getvalue()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


def main() -> None:
    raise SystemExit(run())

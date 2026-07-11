#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "adventurer-props" / "adventurer-prop-manifest.jsonl"
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "medium"
DEFAULT_CONCURRENCY = 4
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_FINAL_SIZE = 1024
DEFAULT_REMOVE_KEY = (
    Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    / "skills"
    / ".system"
    / "imagegen"
    / "scripts"
    / "remove_chroma_key.py"
)


def die(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def read_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        die(f"Manifest not found: {path}")
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            die(f"Invalid JSON on line {line_no}: {exc}")
        for key in ("slug", "prompt", "sourcePath", "finalPath"):
            if not record.get(key):
                die(f"Line {line_no} missing required key: {key}")
        refs = record.get("styleReferenceFiles", [])
        if refs is not None and not isinstance(refs, list):
            die(f"Line {line_no} styleReferenceFiles must be a list")
        records.append(record)
    if not records:
        die(f"No records found in {path}")
    return records


def is_pending(record: dict[str, Any], force: bool) -> bool:
    return force or not resolve_path(record["finalPath"]).exists()


def reference_paths(record: dict[str, Any], extra_references: list[str]) -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for raw in [*record.get("styleReferenceFiles", []), *extra_references]:
        path = resolve_path(raw).resolve()
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def validate_environment(
    records: list[dict[str, Any]], args: argparse.Namespace
) -> None:
    if args.dry_run:
        return
    needs_generation = any(
        args.force or not resolve_path(record["sourcePath"]).exists()
        for record in records
    )
    if needs_generation and not os.getenv("OPENAI_API_KEY"):
        die(
            "OPENAI_API_KEY is not set. Activate .venv and export OPENAI_API_KEY before generating."
        )
    remove_key = resolve_path(args.remove_key)
    if not remove_key.exists():
        die(f"Chroma-key helper not found: {remove_key}")


def decode_first_image(result: Any, output: Path) -> None:
    data = getattr(result, "data", None) or []
    if not data:
        die("Image API returned no image data.")
    image_b64 = getattr(data[0], "b64_json", None)
    if not image_b64:
        die("Image API response did not include b64_json.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(image_b64))


def retry_delay(exc: Exception, attempt: int) -> float:
    for attr in ("retry_after", "retry_after_seconds"):
        value = getattr(exc, attr, None)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    if "rate" in name or "rate limit" in message or "429" in message:
        return min(90.0, 5.0 * attempt)
    return min(60.0, 2.0**attempt)


async def generate_source(
    client: AsyncOpenAI,
    record: dict[str, Any],
    *,
    model: str,
    size: str,
    quality: str,
    max_attempts: int,
    extra_references: list[str],
) -> None:
    source_path = resolve_path(record["sourcePath"])
    refs = reference_paths(record, extra_references)
    for ref in refs:
        if not ref.exists():
            die(f"Reference image missing for {record['slug']}: {ref}")

    for attempt in range(1, max_attempts + 1):
        try:
            if refs:
                with ExitStack() as stack:
                    handles = [stack.enter_context(path.open("rb")) for path in refs]
                    result = await client.images.edit(
                        model=model,
                        image=handles,
                        prompt=record["prompt"],
                        size=size,
                        quality=quality,
                        output_format="png",
                    )
            else:
                result = await client.images.generate(
                    model=model,
                    prompt=record["prompt"],
                    size=size,
                    quality=quality,
                    output_format="png",
                )
            decode_first_image(result, source_path)
            return
        except Exception as exc:
            if attempt >= max_attempts:
                raise
            delay = retry_delay(exc, attempt)
            print(
                f"{record['slug']} generation attempt {attempt}/{max_attempts} failed "
                f"({exc.__class__.__name__}); retrying in {delay:.1f}s",
                file=sys.stderr,
            )
            await asyncio.sleep(delay)


def normalize_square(source: Path, output: Path, size: int) -> None:
    img = Image.open(source).convert("RGBA")
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output)


def validate_alpha(output: Path, corner_threshold: int) -> None:
    img = Image.open(output).convert("RGBA")
    corners = [
        img.getpixel((0, 0))[3],
        img.getpixel((img.width - 1, 0))[3],
        img.getpixel((0, img.height - 1))[3],
        img.getpixel((img.width - 1, img.height - 1))[3],
    ]
    if any(alpha > corner_threshold for alpha in corners):
        raise SystemExit(
            f"Transparent-corner validation failed for {output}: {corners}"
        )


def post_process(record: dict[str, Any], args: argparse.Namespace) -> None:
    source_path = resolve_path(record["sourcePath"])
    if not source_path.exists():
        die(f"Cannot post-process missing source for {record['slug']}: {source_path}")

    final_path = resolve_path(record["finalPath"])
    keyed_path = final_path.with_name(f"{final_path.stem}-keyed.png")
    subprocess.run(
        [
            sys.executable,
            str(resolve_path(args.remove_key)),
            "--input",
            str(source_path),
            "--out",
            str(keyed_path),
            "--auto-key",
            "border",
            "--soft-matte",
            "--transparent-threshold",
            str(args.transparent_threshold),
            "--opaque-threshold",
            str(args.opaque_threshold),
            "--despill",
        ],
        check=True,
    )
    normalize_square(keyed_path, final_path, args.final_size)
    keyed_path.unlink()
    validate_alpha(final_path, args.corner_alpha_threshold)


async def process_records(args: argparse.Namespace) -> int:
    records = read_manifest(resolve_path(args.manifest))
    pending = [record for record in records if is_pending(record, args.force)]
    if args.limit is not None:
        pending = pending[: args.limit]

    if args.dry_run:
        for record in pending:
            source = resolve_path(record["sourcePath"])
            refs = reference_paths(record, args.reference)
            action = (
                "post-process existing source"
                if source.exists() and not args.force
                else "generate source and post-process"
            )
            print(
                f"{record['slug']}: {action} -> {resolve_path(record['finalPath'])} ({len(refs)} reference image(s))"
            )
        print(f"{len(pending)} image(s) would be processed.")
        return 0

    if not pending:
        print("No missing prop images.")
        return 0

    validate_environment(pending, args)
    client = AsyncOpenAI()
    semaphore = asyncio.Semaphore(args.concurrency)
    failures: list[tuple[str, str]] = []

    async def run_one(index: int, record: dict[str, Any]) -> None:
        label = f"[{index}/{len(pending)}] {record['slug']}"
        started = time.time()
        try:
            source_path = resolve_path(record["sourcePath"])
            if args.force or not source_path.exists():
                async with semaphore:
                    print(f"{label}: generating", file=sys.stderr)
                    await generate_source(
                        client,
                        record,
                        model=args.model,
                        size=args.size,
                        quality=args.quality,
                        max_attempts=args.max_attempts,
                        extra_references=args.reference,
                    )
            else:
                print(f"{label}: reusing source", file=sys.stderr)
            post_process(record, args)
            elapsed = time.time() - started
            print(
                f"{label}: wrote {resolve_path(record['finalPath'])} in {elapsed:.1f}s",
                file=sys.stderr,
            )
        except Exception as exc:
            failures.append((record["slug"], str(exc)))
            print(f"{label}: failed: {exc}", file=sys.stderr)
            if args.fail_fast:
                raise

    tasks = [
        asyncio.create_task(run_one(i, record))
        for i, record in enumerate(pending, start=1)
    ]
    await asyncio.gather(*tasks)

    if failures:
        print("Failures:", file=sys.stderr)
        for slug, error in failures:
            print(f"- {slug}: {error}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and post-process missing transparent adventurer prop images from a JSONL manifest."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--final-size", type=int, default=DEFAULT_FINAL_SIZE)
    parser.add_argument("--remove-key", default=str(DEFAULT_REMOVE_KEY))
    parser.add_argument("--transparent-threshold", type=int, default=12)
    parser.add_argument("--opaque-threshold", type=int, default=220)
    parser.add_argument("--corner-alpha-threshold", type=int, default=8)
    parser.add_argument(
        "--reference",
        action="append",
        default=[],
        help="Extra style reference image path. Can be repeated.",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate and reprocess even when final images exist.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    if args.concurrency < 1 or args.concurrency > 10:
        die("--concurrency must be between 1 and 10")
    if args.max_attempts < 1 or args.max_attempts > 10:
        die("--max-attempts must be between 1 and 10")
    if args.limit is not None and args.limit < 1:
        die("--limit must be >= 1")
    if args.final_size < 128:
        die("--final-size must be >= 128")

    return asyncio.run(process_records(args))


if __name__ == "__main__":
    raise SystemExit(main())

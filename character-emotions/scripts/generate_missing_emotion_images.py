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
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "medium"
DEFAULT_CONCURRENCY = 4
DEFAULT_MAX_ATTEMPTS = 3


def die(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


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
        for key in ("slug", "prompt", "sourcePath", "finalPath", "referenceFile"):
            if not record.get(key):
                die(f"Line {line_no} missing required key: {key}")
        records.append(record)
    if not records:
        die(f"No records found in {path}")
    return records


def is_missing(record: dict[str, Any], force: bool) -> bool:
    return force or not Path(record["finalPath"]).exists()


def validate_environment(dry_run: bool) -> None:
    if dry_run:
        return
    if not os.getenv("OPENAI_API_KEY"):
        die(
            "OPENAI_API_KEY is not set. Activate .venv and export OPENAI_API_KEY before running."
        )


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
) -> None:
    reference_path = Path(record["referenceFile"])
    if not reference_path.exists():
        die(f"Reference image missing for {record['slug']}: {reference_path}")

    source_path = Path(record["sourcePath"])
    payload = {
        "model": model,
        "prompt": record["prompt"],
        "size": size,
        "quality": quality,
        "output_format": "png",
        "image": None,
    }

    for attempt in range(1, max_attempts + 1):
        try:
            with reference_path.open("rb") as reference:
                payload["image"] = reference
                result = await client.images.edit(**payload)
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


def post_process(record: dict[str, Any], process_script: Path) -> None:
    source_path = Path(record["sourcePath"])
    if not source_path.exists():
        die(f"Cannot post-process missing source for {record['slug']}: {source_path}")
    command = [
        sys.executable,
        str(process_script),
        "--slug",
        record["slug"],
        "--input",
        str(source_path),
        "--source-dir",
        str(source_path.parent),
        "--out-dir",
        str(Path(record["finalPath"]).parent),
    ]
    subprocess.run(command, check=True)


async def process_records(args: argparse.Namespace) -> int:
    records = read_manifest(Path(args.manifest))
    pending = [record for record in records if is_missing(record, args.force)]
    if args.limit is not None:
        pending = pending[: args.limit]

    if args.dry_run:
        for record in pending:
            source = Path(record["sourcePath"])
            action = (
                "post-process existing source"
                if source.exists() and not args.force
                else "generate source and post-process"
            )
            print(f"{record['slug']}: {action} -> {record['finalPath']}")
        print(f"{len(pending)} missing image(s) would be processed.")
        return 0

    if not pending:
        print("No missing images.")
        return 0

    client = AsyncOpenAI()
    process_script = Path(args.process_script)
    if not process_script.exists():
        die(f"Post-processing script not found: {process_script}")

    semaphore = asyncio.Semaphore(args.concurrency)
    failures: list[tuple[str, str]] = []

    async def run_one(index: int, record: dict[str, Any]) -> None:
        label = f"[{index}/{len(pending)}] {record['slug']}"
        started = time.time()
        try:
            source_path = Path(record["sourcePath"])
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
                    )
            else:
                print(f"{label}: reusing source", file=sys.stderr)
            post_process(record, process_script)
            elapsed = time.time() - started
            print(
                f"{label}: wrote {record['finalPath']} in {elapsed:.1f}s",
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
        description="Generate and post-process every missing image listed in the emotion portrait JSONL manifest."
    )
    parser.add_argument(
        "--manifest", default="character-emotions/emotion-portrait-manifest.jsonl"
    )
    parser.add_argument(
        "--process-script",
        default="character-emotions/scripts/process_emotion_asset.py",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
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

    validate_environment(args.dry_run)
    return asyncio.run(process_records(args))


if __name__ == "__main__":
    raise SystemExit(main())

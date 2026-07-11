#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image


def latest_generated_image(root: Path) -> Path:
    files = [p for p in root.rglob("*.png") if p.is_file()]
    if not files:
        raise SystemExit(f"No generated PNG files under {root}")
    return max(files, key=lambda p: p.stat().st_mtime)


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

    check = Image.open(output).convert("RGBA")
    corners = [
        check.getpixel((0, 0))[3],
        check.getpixel((size - 1, 0))[3],
        check.getpixel((0, size - 1))[3],
        check.getpixel((size - 1, size - 1))[3],
    ]
    if any(alpha > 8 for alpha in corners):
        raise SystemExit(f"Transparent-corner validation failed for {output}: {corners}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--input", help="Specific generated source PNG. Defaults to newest generated PNG.")
    parser.add_argument("--generated-root", default=str(Path.home() / ".codex" / "generated_images"))
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument(
        "--remove-key",
        default=str(Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "remove_chroma_key.py"),
    )
    args = parser.parse_args()

    latest = Path(args.input) if args.input else latest_generated_image(Path(args.generated_root))
    if not latest.is_file():
        raise SystemExit(f"Input PNG does not exist: {latest}")
    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    source_dir.mkdir(parents=True, exist_ok=True)
    raw_path = source_dir / f"{args.slug}-source.png"
    raw_path.write_bytes(latest.read_bytes())

    keyed_path = out_dir / f"{args.slug}-keyed.png"
    final_path = out_dir / f"{args.slug}.png"
    subprocess.run(
        [
            sys.executable,
            args.remove_key,
            "--input",
            str(raw_path),
            "--out",
            str(keyed_path),
            "--auto-key",
            "border",
            "--soft-matte",
            "--transparent-threshold",
            "12",
            "--opaque-threshold",
            "220",
            "--despill",
        ],
        check=True,
    )
    normalize_square(keyed_path, final_path, args.size)
    keyed_path.unlink()
    print(final_path)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def format_prompt(template: str, character: dict, emotion: dict) -> str:
    return template.format(
        characterSlug=character["Slug"],
        characterDisplayName=character["DisplayName"],
        characterDescription=character["Description"],
        emotionSlug=emotion["Slug"],
        emotionDisplayName=emotion["DisplayName"],
        emotionExpression=emotion["Expression"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    spec_path = Path(args.spec)
    repo_root = spec_path.resolve().parents[1]
    spec = json.loads(spec_path.read_text())
    template = spec["PromptTemplate"]["Prompt"]
    final_dir = repo_root / spec["Output"]["FinalDirectory"]
    source_dir = repo_root / spec["Output"]["SourceDirectory"]

    records = []
    for character in spec["Characters"]:
        for emotion in spec["Emotions"]:
            slug = f"{character['Slug']}-{emotion['Slug']}"
            records.append(
                {
                    "slug": slug,
                    "character": character["Slug"],
                    "emotion": emotion["Slug"],
                    "referenceFile": str((spec_path.parent / character["ReferenceFile"]).resolve()),
                    "sourcePath": str(source_dir / f"{slug}-source.png"),
                    "finalPath": str(final_dir / f"{slug}.png"),
                    "prompt": format_prompt(template, character, emotion),
                }
            )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n")
    print(f"Wrote {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()

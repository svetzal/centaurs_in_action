# Visual Spec Workspace Notes

## Python Environment and Dependencies

Use the project virtual environment for Python work:

```bash
source .venv/bin/activate
```

When adding or upgrading Python packages in `.venv`, update
`requirements.txt` in the same change. Prefer:

```bash
python -m pip freeze | sort > requirements.txt
```

Do not rely on the bundled Codex Python runtime for repo scripts unless the
project `.venv` is unavailable or broken.

## Transparent Image Chroma-Key Procedure

For generated images that need transparency, use the built-in image generator
first and request a flat chroma-key background. In this project, the working
key color has been bright magenta.

Prompt requirements:

- Ask for a `#ff00ff` chroma-key background.
- State that the background must be one flat uniform color.
- Prohibit shadows, gradients, texture, floor planes, reflections, and lighting
  variation in the background.
- State that `#ff00ff` must not appear anywhere in the subject.
- Ask for crisp edges and generous padding.
- For slide/paste-in assets, also prohibit readable text, labels, watermark,
  and logos unless specifically requested.

After generation, copy the generated source image from the Codex generated
images directory into `tmp/`, then remove the chroma key with the system helper.
Use the project `.venv`, which should have Pillow installed from
`requirements.txt`.

Example:

```bash
source .venv/bin/activate

HELPER="${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py"

python "$HELPER" \
  --input tmp/slide-panels/example-source.png \
  --out slide-panels/example.png \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

The helper samples the actual border color, so it still works when the generated
image returns a near-magenta value instead of exact `#ff00ff` such as `#ea02e7`,
`#ed02ee`, or `#f503f5`.

Validate the output before using it:

```bash
source .venv/bin/activate

python - <<'PY'
from PIL import Image

p = "slide-panels/example.png"
im = Image.open(p)
print(
    f"{p}: mode={im.mode} size={im.size} "
    f"alpha={'A' in im.getbands()} "
    f"corners={[im.getpixel((0, 0))[-1], "
    f"im.getpixel((im.width - 1, 0))[-1], "
    f"im.getpixel((0, im.height - 1))[-1], "
    f"im.getpixel((im.width - 1, im.height - 1))[-1]]}"
)
PY
```

Transparent corners should usually report alpha `0`. A non-transparent corner
is acceptable only when the subject is intentionally cropped to that edge, such
as a right-side slide panel.

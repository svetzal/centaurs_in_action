#!/usr/bin/env python3
"""Prepare generated magenta-key intermediates using the approved system helper."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image, ImageOps, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / 'character-references-2/data/illustrated-assets.json').read_text())
HELPER = Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'skills/.system/imagegen/scripts/remove_chroma_key.py'
def blank_boundary(projection, target, radius=60):
    start = max(0, target-radius)
    stop = min(len(projection), target+radius)
    runs = []
    run = None
    for index in range(start, stop):
        if not projection[index] and run is None:
            run = index
        if projection[index] and run is not None:
            runs.append((run, index)); run = None
    if run is not None:
        runs.append((run, stop))
    if not runs:
        raise ValueError(f'No clear gap near {target}; inspect the source before cropping')
    left, right = max(runs, key=lambda pair: pair[1]-pair[0])
    return (left+right)//2

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kind', choices=['character-pair','prop','expressions'])
args = parser.parse_args()
for asset in DATA['assets']:
    if args.kind and asset['kind'] != args.kind:
        continue
    source = ROOT / asset['source']
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        shutil.copy2(asset['generated_source'], source)
    keyed = source.with_name(asset['slug']+'-keyed.png')
    subprocess.run([sys.executable,str(HELPER),'--input',str(source),'--out',str(keyed),'--auto-key','border','--soft-matte','--transparent-threshold','12','--opaque-threshold','220','--despill','--force'],check=True)
    im = Image.open(keyed).convert('RGBA')
    # The soft magenta matte also interprets burgundy/violet fabric as spill.
    # Restore original opaque subject colours safely inside the silhouette,
    # leaving the soft/despilled edge untouched.
    hard_keyed = source.with_name(asset['slug']+'-foreground.png')
    subprocess.run([sys.executable,str(HELPER),'--input',str(source),'--out',str(hard_keyed),'--auto-key','border','--tolerance','80','--force'],check=True)
    core = Image.open(hard_keyed).getchannel('A').filter(ImageFilter.MinFilter(7))
    im = Image.composite(Image.open(source).convert('RGBA'), im, core)
    im.putalpha(im.getchannel('A').point(lambda value: 0 if value <= 12 else value))
    im.save(keyed)
    if asset['kind'] == 'character-pair':
        split = asset['split_x']
        assert im.getchannel('A').crop((split-2,0,split+2,im.height)).getbbox() is None, f"Split intersects {asset['slug']}"
        parts = [im.crop((0,0,split,im.height)),im.crop((split,0,im.width,im.height))]
        parts = [ImageOps.expand(part.crop(part.getchannel('A').getbbox()),border=20,fill=(0,0,0,0)) for part in parts]
    elif asset['kind'] == 'expressions':
        y = blank_boundary(im.getchannel('A').getprojection()[1], im.height//2)
        parts = []
        for top, bottom in [(0,y),(y,im.height)]:
            row = im.crop((0,top,im.width,bottom))
            projection = row.getchannel('A').getprojection()[0]
            boundaries = [0] + [blank_boundary(projection,round(im.width*i/5),35) for i in range(1,5)] + [im.width]
            for left,right in zip(boundaries,boundaries[1:]):
                part = row.crop((left,0,right,row.height))
                part = ImageOps.expand(part.crop(part.getchannel('A').getbbox()),border=12,fill=(0,0,0,0))
                parts.append(part)
    else:
        parts = [im.resize((1024,1024),Image.Resampling.LANCZOS)]
    for part, output in zip(parts,asset['outputs'],strict=True):
        dest=ROOT/output;dest.parent.mkdir(parents=True,exist_ok=True);part.save(dest)
        corners=[part.getpixel(pt)[3] for pt in [(0,0),(part.width-1,0),(0,part.height-1),(part.width-1,part.height-1)]]
        assert corners == [0,0,0,0]
        print(output,part.mode,part.size,'corner alpha',corners,flush=True)

#!/usr/bin/env python3
"""Build static storytelling dossiers from established cast notes and expansions."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
CAST = (ROOT / 'character-cast.md').read_text()
STORIES = json.loads((ROOT / 'data/storytelling.json').read_text())
NAMES = ['Mateo', 'Celeste', 'Ari', 'Imani', 'Bram', 'Noor', 'Rowan']

def esc(value):
    return html.escape(str(value), quote=True)

def paragraph(text):
    return f'<p>{esc(text)}</p>'

def list_html(items):
    return '<ul>' + ''.join(f'<li>{esc(x)}</li>' for x in items) + '</ul>'

def definition(items):
    return '<dl class="field-list">' + ''.join(f'<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in items) + '</dl>'

def canon(name):
    section = re.search(rf'^## {name}\n(.*?)(?=^## |\Z)', CAST, re.M | re.S).group(1)
    fields = {}
    for match in re.finditer(r'^-? ?\*\*([^*]+):\*\*\s*(.*?)(?=\n(?:- |\*\*|\n)|\Z)', section, re.M | re.S):
        fields[match[1]] = re.sub(r'\s+', ' ', match[2]).strip().strip('`')
    fields['Handwritten phrase'] = fields['Handwritten phrase'].strip('*"')
    bio = re.search(r'\n\n(' + name + r' .*?)(?=\n\n)', section, re.S)
    fields['bio'] = re.sub(r'\s+', ' ', bio[1])
    return fields

def navigation(current):
    return '<nav class="cast-nav" aria-label="Character dossiers">' + '<a href="../../#cast">← The cast</a>' + ''.join(f'<a href="../{n.lower()}/"' + (' aria-current="page"' if n == current else '') + f'>{n}</a>' for n in NAMES) + '</nav>'

for number, (slug, story) in enumerate(STORIES.items(), 2):
    name = slug.title()
    c = canon(name)
    reference = '../' + c['Reference']
    scores = re.findall(r'(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) (\d+)', c['Characteristics'])
    stats = ''.join(f'<div><dt>{label}</dt><dd>{value}<span> / 20</span></dd><meter min="1" max="20" value="{value}" aria-label="{label}">{value}</meter></div>' for label, value in scores)
    relationships = ''.join(f'<article><h3><a href="../{other.lower()}/">With {other}</a></h3>{paragraph(text)}</article>' for other, text in story['relations'])
    scenes = ''
    prompts = []
    for i, (title, form, scene) in enumerate(story['scenes'], 1):
        prompt = f"Character: {name} ({c['Pronouns']}). Use the attached {name} reference sheet as the identity authority. Form: {form}. " + story['continuity'] + ' Scene: ' + scene + ' Style: warm illustrated mythic adventure, expressive ink contours, painterly shading, tactile materials and grounded light. Preserve anatomy: centaur = human head and torso joined to a four-legged horse body; reverse-centaur = horse head on a clothed human body with two human legs. Keep all limbs plausible. Preserve identity, build, clothing and markings across forms. Agency is conveyed through attention, posture and context, never through changing skin tone, body size or gender. No body art, readable text, labels, watermark or logos. Avoid: ' + story['avoid']
        prompts.append({'title': title, 'form': form, 'prompt': prompt})
        scenes += f'<article class="scene"><p class="section-label">Scene {i:02} · {form}</p><h3>{esc(title)}</h3>{paragraph(scene)}<details><summary>Image prompt and continuity notes</summary><p class="prompt-text" id="prompt-{i}">{esc(prompt)}</p><button type="button" data-copy="prompt-{i}" hidden>Copy image prompt</button></details></article>'
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(name)} — complete character dossier, agency states, visual continuity and storytelling image prompts.">
<title>{name} — Character Dossier · Centaurs in Action</title><link rel="stylesheet" href="../dossier.css"></head>
<body><a class="skip-link" href="#main">Skip to dossier</a>{navigation(name)}
<main id="main" class="dossier"><header class="masthead"><p class="section-label">Centaurs in Action · Field dossier {number:02}</p><div class="title-row"><div><p>{esc(c['Role'])}</p><h1>{name}</h1></div><span class="pronouns">{esc(c['Pronouns'])}</span></div><p class="essence">{esc(c['Character essence'])}</p></header>
<nav class="section-nav" aria-label="Dossier sections"><a href="#identity">Identity</a><a href="#personality">Personality</a><a href="#agency">Agency</a><a href="#expressions">Expressions</a><a href="#relationships">Relationships</a><a href="#scenes">Scene briefs</a></nav>
<section id="identity" class="identity"><div><p class="section-label">Visual authority</p><h2>{esc(story['title'])}</h2><a href="{reference}" class="sheet-link"><img src="{reference}" width="1536" height="1024" alt="{name}: full-body centaur and reverse-centaur, with five matching emotional portraits of each form"></a><p class="caption">Centaur at left · reverse-centaur at right. Open the original sheet to inspect details.</p><a class="text-link" href="{reference}" download>Download reference sheet ↓</a></div><aside><blockquote>“{esc(c['Handwritten phrase'])}”</blockquote>{definition([(key, c[key]) for key in ['Physical presence', 'Defining appearance', 'Place in society']])}</aside></section>
<section class="continuity"><p class="section-label">Keep consistent across images</p><h2>Identity in every frame</h2>{paragraph(story['continuity'])}<details><summary>Continuity boundaries and things to avoid</summary>{paragraph(story['avoid'])}<p>Both forms belong to the same person. Neither sadness nor happiness determines the form: a centaur can be worried and act with agency; a reverse-centaur can smile while seeking approval. Keep both forms dignified and fully clothed as shown. Body-art diagrams and added tattoos are excluded.</p><p>The original sheet anchors appearance. Props and scene briefs below extend the storytelling vocabulary; include only what the scene needs.</p></details></section>
<section id="personality"><p class="section-label">Personality and story foundation</p><h2>The person behind the role</h2><div class="two-columns"><div>{paragraph(c['bio'])}{paragraph(story['origin'])}</div><div>{definition([('First impression', c['First impression']), ('Inner engine', c['Inner engine']), ('Voice', c['Voice']), ('Private delight', c['Private delight'])])}</div></div><div class="two-columns">{definition([('Wants', story['want']), ('Fears', story['fear'])])}{definition([('Inner contradiction', story['contradiction']), ('Boundary', story['boundary'])])}</div><aside class="candid"><h3>A quiet moment</h3>{paragraph(story['candid'])}</aside></section>
<section id="agency"><p class="section-label">Two forms · one person</p><h2>Where attention goes</h2><div class="state-grid"><article><span class="state-number">01</span><h3>Centaur · strength-centred</h3>{paragraph(story['centred'])}{definition([('Signature strength', c['Leadership strength']), ('Direction for the image', story['state_cues'][0])])}</article><article><span class="state-number">02</span><h3>Reverse-centaur · pressure-captured</h3>{paragraph(story['captured'])}{definition([('Shadow', c['Shadow']), ('Direction for the image', story['state_cues'][1])])}</article></div><h3>Recognizable pressure points</h3>{list_html(story['triggers'])}<div class="return-path"><h3>The return to agency</h3><ol>{''.join(f'<li><strong>{label}</strong><span>{esc(text)}</span></li>' for label, text in zip(['Notice', 'Name', 'Centre', 'Act'], story['return']))}</ol></div></section>
<section><p class="section-label">D&amp;D-style characteristics · 1–20</p><h2>How {name} moves</h2><dl class="stats">{stats}</dl><p class="caption">A storytelling shorthand for this character. Scores remain the same in both forms.</p></section>
<section id="expressions"><p class="section-label">Emotional range</p><h2>Small gestures, clear feelings</h2>{paragraph(c['Emotional tells'])}<p>The reference sheet shows neutral, curious, happy, worried and thoughtful portraits in each form. Use these direction notes to carry the same feeling into a scene.</p><div class="emotion-grid">{''.join(f'<article><h3>{esc(t.split(": ",1)[0])}</h3>{paragraph(t.split(": ",1)[1])}</article>' for t in story['emotions'])}</div></section>
<section><p class="section-label">Objects with a purpose</p><h2>What {name} carries</h2><div class="prop-grid">{''.join(f'<article><h3>{esc(title)}</h3>{paragraph(text)}</article>' for title, text in story['props'])}</div><p class="caption">Motifs: {esc(c['Motifs'])}. Props support an action; they need not all appear at once.</p></section>
<section id="relationships"><p class="section-label">The ensemble</p><h2>Strengths in conversation</h2><div class="relationship-grid">{relationships}</div><p class="caption">These are complementary tensions. Any character can lead, be mistaken, change their mind or need support.</p></section>
<section id="scenes"><p class="section-label">Ready for storytelling images</p><h2>Three scenes to begin with</h2><p>Attach the original character sheet with a prompt. For ensemble scenes, attach each named character’s sheet as well. The brief fixes identity and intent while leaving room for composition.</p><div class="scenes">{scenes}</div><p><a class="text-link" href="reference.json" download>Download complete dossier and prompts (JSON) ↓</a></p><p class="copy-status" role="status" aria-live="polite"></p></section>
<footer><p>Centaurs in Action · {name} field dossier</p><a href="../../#cast">Return to the cast →</a></footer></main><script src="../dossier.js"></script></body></html>'''
    dest = ROOT / slug
    dest.mkdir(exist_ok=True)
    (dest / 'index.html').write_text(page)
    (dest / 'reference.json').write_text(json.dumps({'name': name, 'established_profile': c, 'storytelling': story, 'image_prompts': prompts, 'reference_sheet': reference}, indent=2, ensure_ascii=False) + '\n')
    print(f'Built {slug}/index.html and reference.json')

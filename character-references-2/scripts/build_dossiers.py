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
    return '<nav class="cast-navigation" aria-label="Character dossiers">' + '<a href="../../#cast">← The cast</a>' + ''.join(f'<a href="../{n.lower()}/"' + (' aria-current="page"' if n == current else '') + f'>{n}</a>' for n in NAMES) + '</nav>'

PACK_ART = json.loads((ROOT / 'data/pack-art.json').read_text())
TEMPLATE = (ROOT / 'templates/dossier.html').read_text()
ROLES = ['Cartographer', 'Researcher', 'Hearthkeeper', 'Builder', 'Pattern-reader', 'Response lead']
ABBREVIATIONS = {'Strength': 'STR', 'Dexterity': 'DEX', 'Constitution': 'CON', 'Intelligence': 'INT', 'Wisdom': 'WIS', 'Charisma': 'CHA'}
for number, (slug, story) in enumerate(STORIES.items(), 2):
    name = slug.title()
    c = canon(name)
    reference = '../' + c['Reference']
    scores = re.findall(r'(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma) (\d+)', c['Characteristics'])
    highest = max(int(value) for _, value in scores)
    stats = ''.join(
        f'<div class="stat{" stat--signature" if int(value) == highest else ""}" role="listitem" style="--score: {int(value)*5}%">'
        f'<span class="stat__abbr">{ABBREVIATIONS[label]}</span><strong>{value}</strong><span class="stat__name">{label}</span></div>'
        for label, value in scores
    )
    props = ''
    for (title, description), (asset, meaning, alt) in zip(story['props'], PACK_ART[slug], strict=True):
        props += f'''<figure class="tool-card"><a class="tool-card__image" href="../../adventurer-props/transparent-1024/{asset}.png" download aria-label="Download {esc(title)} artwork"><img src="../../adventurer-props/transparent-1024/{asset}.png" alt="{esc(alt)}" loading="lazy"></a><figcaption><span>{meaning}</span><strong>{esc(title)}</strong><p>{esc(description)}</p></figcaption></figure>'''
    relationships = ''.join(f'<article><h3><a href="../{other.lower()}/">With {other}</a></h3>{paragraph(text)}</article>' for other, text in story['relations'])
    scenes = ''
    prompts = []
    for i, (title, form, scene) in enumerate(story['scenes'], 1):
        prompt = f"Character: {name} ({c['Pronouns']}). Use the attached {name} reference sheet as the identity authority. Form: {form}. " + story['continuity'] + ' Scene: ' + scene + ' Style: warm illustrated mythic adventure, expressive ink contours, painterly shading, tactile materials and grounded light. Preserve anatomy: centaur = human head and torso joined to a four-legged horse body; reverse-centaur = horse head on a clothed human body with two human legs. Keep all limbs plausible. Preserve identity, build, clothing and markings across forms. Agency is conveyed through attention, posture and context, never through changing skin tone, body size or gender. No body art, readable text, labels, watermark or logos. Avoid: ' + story['avoid']
        prompts.append({'title': title, 'form': form, 'prompt': prompt})
        scenes += f'<article class="scene"><p class="section-label">Scene {i:02} · {form}</p><h3>{esc(title)}</h3>{paragraph(scene)}<details><summary>Image prompt and continuity notes</summary><p class="prompt-text" id="prompt-{i}">{esc(prompt)}</p><button type="button" data-copy="prompt-{i}" hidden>Copy image prompt</button></details></article>'
    expressions = ''
    for key, emotion in zip(['neutral','curious','happy','worried','thoughtful'],story['emotions'],strict=True):
        label = emotion.split(': ', 1)[0]
        expressions += f'<figure class="expression"><div class="expression__portrait"><img src="assets/human-{key}.png" alt="{name} {label.lower()} in centaur form" data-emotion="{label.lower()}" data-expression="{key}" loading="lazy"></div><figcaption>{label}</figcaption></figure>'
    values = {key: esc(story[key]) for key in ['title','centred','captured','continuity','avoid','origin','candid']}
    values.update({
        'centred_thought': esc(story['inner_thoughts']['centred']),
        'captured_thought': esc(story['inner_thoughts']['captured']),
        'subject_pronoun': 'she' if slug in ['celeste','imani'] else 'he' if slug == 'bram' else 'they',
        'possessive': 'her' if slug in ['celeste','imani'] else 'his' if slug == 'bram' else 'their',
        'name': name, 'number': f'{number:02}', 'role_short': ROLES[number-2],
        'role': esc(c['Role']), 'pronouns': esc(c['Pronouns']), 'essence': esc(c['Character essence']),
        'navigation': navigation(name), 'impression': esc(c['First impression']), 'society': esc(c['Place in society']),
        'phrase': esc(c['Handwritten phrase']), 'strength': esc(c['Leadership strength']), 'shadow': esc(c['Shadow']),
        'reference': reference, 'centred_cue': esc(story['state_cues'][0]), 'captured_cue': esc(story['state_cues'][1]),
        'return_steps': ''.join(f'<li><strong>{label}</strong><span>{esc(text)}</span></li>' for label,text in zip(['Notice','Name','Centre','Act'],story['return'])),
        'triggers': list_html(story['triggers']), 'stats': stats, 'props': props, 'motifs': esc(c['Motifs']),
        'expressions': expressions, 'emotional_tells': esc(c['Emotional tells']),
        'emotion_notes': ''.join(f'<article><h3>{esc(t.split(": ",1)[0])}</h3>{paragraph(t.split(": ",1)[1])}</article>' for t in story['emotions']),
        'appearance': definition([(key,c[key]) for key in ['Physical presence','Defining appearance']]),
        'bio': esc(c['bio']), 'personality': definition([(key,c[key]) for key in ['First impression','Inner engine','Voice','Private delight']]),
        'motivation': definition([('Wants',story['want']),('Fears',story['fear'])]),
        'boundaries': definition([('Inner contradiction',story['contradiction']),('Boundary',story['boundary'])]),
        'relationships': relationships, 'scenes': scenes,
    })
    dest = ROOT / slug
    dest.mkdir(exist_ok=True)
    (dest / 'index.html').write_text(TEMPLATE.format(**values))
    (dest / 'reference.json').write_text(json.dumps({'name':name,'established_profile':c,'storytelling':story,'image_prompts':prompts,'reference_sheet':reference,'pack_art':[{'title':p[0],'image':'../../adventurer-props/transparent-1024/'+a[0]+'.png','alt':a[2]} for p,a in zip(story['props'],PACK_ART[slug],strict=True)]},indent=2,ensure_ascii=False)+'\n')
    print(f'Built {slug}/index.html and reference.json')

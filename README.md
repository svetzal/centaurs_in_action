# Centaurs in Action

Centaurs in Action is an evolving visual language for recognizing personal
agency. The centaur represents a person centred in their strengths and able to
create positive effects in the world. The reverse-centaur represents a person
whose attention has been captured by pressure and weakness, leaving them
reactive or diminished.

The site combines:

- character reference sheets and transparent character components;
- personality, social-role, strength, and shadow profiles;
- interactive HTML character dossiers;
- reusable mythic-adventure tools and props;
- compositions for workshops, presentations, and reflective exercises.

## Current Featured Character

[Mateo's interactive dossier](character-references-2/mateo/index.html) explores
the two forms as states of agency and introduces a four-step return path:
Notice, Name, Centre, and Act.

## Local Preview

Run a local static server from the repository root:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8765/`.

## Publishing

The site is published through GitHub Pages from the root of the `main` branch.

## Storytelling Dossiers

The cast now includes complete dossiers for
[Celeste](character-references-2/celeste/),
[Ari](character-references-2/ari/),
[Imani](character-references-2/imani/),
[Bram](character-references-2/bram/),
[Noor](character-references-2/noor/), and
[Rowan](character-references-2/rowan/).
Each contains visual continuity notes, personality and story foundations,
agency states, a return path, emotional direction, relationships, props, and
three image prompts. Each page offers its original reference sheet and a
complete JSON dossier for download.

Established identities remain in `character-references-2/character-cast.md`.
The expanded storytelling material is in
`character-references-2/data/storytelling.json`. Rebuild the six static pages
and their JSON exports after editing either source:

```bash
source .venv/bin/activate
python character-references-2/scripts/build_dossiers.py
```

Attach the relevant character sheets when using the image prompts. The sheets
anchor appearance; the written dossiers guide personality, action, and scene
continuity. The pages remain readable without JavaScript; JavaScript adds
prompt copying with a manual-selection fallback.

Mateo's home-page and dossier figures use the `*-full-body-clean.png` assets in
`character-references-2/mateo/assets/`. These replacements were generated with
the built-in image tool on a uniform magenta background, then extracted with
the system chroma-key helper. Their generation and extraction details are in
`character-references-2/data/mateo-cutouts.json`. Original assets are retained.

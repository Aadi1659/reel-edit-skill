# reel-edit: a Claude skill that edits your face-cam reels

Record yourself talking to the camera. Drop the clips into Claude Code, say **"edit this reel"**, and get a finished
1080x1920 reel: dead air cut, colour graded, every word animated on screen, screenshots and sound effects added, rendered.

What it does, step by step:

- **prep**: iPhone HDR (HLG) to normal SDR, 30 fps, a cinematic grade, voice cleanup and loudness
- **cut**: removes dead air and micro pauses, speeds up slightly, adds jump-cut punch-ins
- **words**: Whisper word timings, so every word on screen lands exactly when you say it
- **edit**: big serif kinetic type over your face, plus cutaways (real screenshots in a card, logo statements)
- **check, snap, render**: catches overlap errors, shows a cheap preview strip, then one final render

Built on [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML to video, Apache-2.0).

## Install

You need: **macOS** (the HDR step uses Swift), **Claude Code**, **ffmpeg**, **Node 18+**, **Python 3**.

```bash
brew install ffmpeg node
git clone https://github.com/Aadi1659/reel-edit-skill
mkdir -p ~/.claude/skills && cp -R reel-edit-skill/skills/reel-edit ~/.claude/skills/
```

Then open Claude Code in any folder and say:

> edit this reel: /path/to/IMG_1234.MOV. Here's my script: ...

Claude follows `SKILL.md`: it creates `reels/reel-01/`, runs the pipeline, builds the edit, shows you frames, and renders
`reels/reel-01/renders/reel-01.mp4`.

You can also run the steps yourself:

```bash
R=~/.claude/skills/reel-edit/scripts/reel.py
python3 $R new    reels/reel-01
python3 $R prep   reels/reel-01 /path/IMG_1234.MOV
python3 $R cut    reels/reel-01
python3 $R words  reels/reel-01
python3 $R render reels/reel-01 reel-01
```

## Assets and licences

- **Code and templates**: MIT (see `LICENSE`).
- **Font**: Instrument Serif, SIL Open Font License 1.1 (`template/assets/fonts/OFL.txt`).
- **Sound effects** are not in this repo. `new` copies them from HyperFrames' bundled library (Pixabay Content License).
- **Logos** are not in this repo. `new` downloads them from [simple-icons](https://simpleicons.org) (CC0). The marks belong
  to their owners. Only use them to refer to the product.
- Use only footage, screenshots and music you have the rights to.

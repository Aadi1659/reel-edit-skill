---
name: reel-edit
description: Edit a recorded face-cam reel (Instagram Reels / Shorts / TikTok, 1080x1920) in an editorial style - HDR->SDR, grade, dead-air cut, word-synced Instrument Serif kinetic type, real-screenshot cutaways, SFX, render. Use when the user drops new clips/.MOV files to edit, says "edit reel N", "edit this reel", "make the video", or wants a reel rendered from footage and a script.
---

# Reel edit (editorial style, cheap path)

A repeatable face-cam reel pipeline. **Do not rebuild anything the script or template already does.**

```
R=~/.claude/skills/reel-edit/scripts/reel.py
P=./reels/reel-NN                              # one project per reel
```

## Token rules (why this skill exists)

- Do NOT load the `hyperframes` / `hyperframes-cli` / `media-use` skills unless something here fails or the user wants a look that isn't covered below. The template already follows the render contract.
- Never `cat` the big reference files. Copy a pattern from `~/.claude/skills/reel-edit/examples/<scene>.html` only when you need that exact scene (see list below), and read just that one file.
- Look at frames with `reel.py snap` (a 270 px-wide strip), never full 1080x1920 PNGs, never by rendering.
- Render the full reel **once** at the end. For music, give the user mp3 previews (`beds`), not renders.
- Use the transcript only for **timing**. Its spelling is wrong for Hinglish (gunna, Chatjee); on-screen words come from the script.

## Pipeline

```bash
python3 $R new   $P                                  # template: index.html, type/card/statement scenes, fonts; downloads logos + sfx
python3 $R prep  $P "/path/IMG_1.MOV" [more clips]   # HLG->SDR (swift), 1080x1920 30fps, cinematic grade, bright voice
python3 $R cut   $P                                  # remove dead air + micro pauses, speed 1.12x; patches index.html
python3 $R words $P                                  # Whisper on the CUT voice, onset-snapped -> edit/words.json (prints phrases)
```

- Pass raw clips from wherever they are. Several clips = joined in the order given.
- **Words.** Whisper usually returns good word times (use them as they are). For mixed-language speech such as Hinglish it sometimes *translates* to English instead; `words` then prints a WARNING. In that case write what was actually said (e.g. Roman Hinglish, with punctuation at each phrase break; the English shows you what was said) to `edit/script.txt` and run `words $P --script $P/edit/script.txt`. That aligns the script to the real pauses and onsets, accurate to about 0.1 s on most phrases but up to about 0.6 s on rapid lists ("caption, reply, DMs"). Snap those moments and nudge `data-t` by hand.
- **Flubbed take / repeated line:** read the `words` output, then `cut $P --drop 3.1-5.4` with the times **as printed** (drops add up across runs; `--reset` clears them). Then rerun `words`.
- **Retakes hide inside one clip.** People repeat a line without stopping the recording, and Whisper often merges or skips the repeat. Slice the CUT `assets/voice.wav` into 1-2 s bursts and transcribe each one (`-l en --prompt "<script>"` keeps Hinglish in Roman script), then drop the weaker say of each repeated line.
- `cut` options: `--speed` (1.12 default; 1.0 for a slow talker), `--th` (speech dB), `--gap` (pauses shorter than this stay inside a phrase, 0.14), `--pre` / `--post` (kept around each phrase, 0.05 / 0.07), `--dip` (micro-pause cut, dB above `--th`, default 0), `--tail` (hold after last word).
- The auto threshold is `max(-30.5, noise floor + 4, speech level - 10)`, so room noise in the pauses is not mistaken for speech. After `cut`, look at the energy envelope: any stretch longer than ~0.15 s that sits well below speech level is a pause the viewer will feel. Tighten with `--th` rather than a higher `--speed`.
- After `cut`, every element with `data-full` gets the reel length, and the jump-cut punch toggles are written between `// CUTS:BEGIN/END`.

## Build the edit (the creative part)

Work from `edit/words.json` + the script/beat sheet.

1. **type.html** - one `.grp` per phrase while the face is on screen. Small lowercase Inter line + one huge Instrument Serif *italic* keyword (170-240 px; shorter word = bigger). Each `.w` gets `data-t` = its word start. Group start = first word, group end = next group's start. Bottom of text at y 1290. `g1` is the cover frame: visible at frame 0 with no reveal. Last group `id="gLast"` (no fade, loops).
   Extras already styled: `.acc` (coral word), `.badge` (white logo tile), `.pair` (logo × logo), `.strike` (coral strike-through).
2. **Cutaways** (graphics over the face, 1.5-6 s each, while a proof is being said). Host div in index.html with root-timeline start/duration; inside, times are LOCAL. Duplicate a scene file + host for each use and give each a unique `data-composition-id`, ids and timeline key.
   - `card.html` - paper `#f3efe8`, REAL screenshot in a white card, 3D tilt in, push-in, coral ellipse draws around the proof.
   - `statement.html` - black `#0e0e0e`, real logo, 2-3 stacked serif words, coral tag line.
   - Patterns in `examples/`: `viral.html` IG reel grid → ranking row + counter rolling to 157x · `hooks.html` three hook cards dealt + score bar to 100 · `skills.html` grid of skill tiles · `human.html` robotic text crossed out · `github.html` = card · `trio.html` = statement · `type.html` incl. the typed "Add a comment… SKILL" box.
3. **Face motion** in index.html: `drift(t, d, 1.0, 1.06)` on every face stretch between cutaways; `punch(t, 1.06, 1.16)` on 1-2 key words; flash + shutter for "screenshot".
4. **SFX** (in `assets/sfx`): whoosh 0.22 at each cutaway entry (−0.05 s), pop 0.35-0.4 on badges/cards, tick 0.45 on counters, sfx_003 0.45 on clicks/cards, shutter 0.6 on flash. Same track index can't overlap - alternate 7-10.

## Optional layout: face-down window

For proof-heavy reels, keep the hook full-frame, then slide the face video down into a rounded window in the lower half and put
titles + proof cards above it. A cut-out of the speaker on top lets the hair or hands break over the window edge.

- Cut-out: `npx --yes hyperframes@0.9.46 remove-background assets/face.mp4 -o assets/face_cut.webm --quality best`
  (runs locally, roughly 6 min for 14 s on Apple silicon). Give the cut-out clip `data-start="0" data-media-start="0"` so it decodes in sync.
- Layers, bottom to top: dark stage background < face window (base video inside a `clip-path: inset(...) round ...` wrapper)
  < proof cards < cut-out < captions. Two face groups (window, cut-out) get the same slide/scale tweens; keep the cut-out hidden while
  the face is full-frame and fade its top ~80 source px with a `mask-image` gradient so a head cropped by the camera does not show a hard edge.
- Close-up footage needs the window small (scale ~0.6, centred, top of the window around y 870) so the whole head and shoulders fit.
  Don't punch-zoom inside the window; jump-cut punches only while full-frame.
- Captions become titles above the cards (bottom of text ~y 410) while the face is down, and go back to y 1290 when full-frame.

## Real assets only

- Logos: `npx --yes hyperframes@0.9.46 media-use resolve --type logo --entity "<Name>"` (thesvg). If it returns a low-res .ico (ChatGPT did), use simple-icons: `https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/<slug>.svg`. `new` downloads claude/instagram/openai/github from simple-icons.
- Web pages (GitHub, docs, product sites): screenshot with the cached chrome-headless-shell at deviceScaleFactor 2.7 → `assets/shots/`. Delete the placeholder `shot.png`.
- Instagram thumbnails / view counts: read from the logged-in built-in browser. Blur other creators' handles.
- Never invent numbers on screen; every stat must match a real screenshot.

## Check, look, render

```bash
cd $P && npx --yes hyperframes@0.9.46 check          # must pass; fix overlap/occlusion errors it lists
python3 $R snap $P 0.5,4.2,7.9,13.4                  # strip of key moments -> edit/snap.jpg (Read it)
python3 $R render $P reel-NN                         # -> renders/reel-NN.mp4 (SDR, 30 fps, high)
```

Snap the cover frame, one moment per cutaway, and the end. Fix, re-snap only what changed.

## Music & delivery

- Default delivery: **voice + SFX only** (music line commented out). Add a trending track in the Instagram app when posting.
- If they want a baked bed: upbeat lo-fi / chill tech. Use tracks you have the rights to (CC0 / CC BY). `python3 $R beds $P track1.mp3 track2.mp3 ...` → mp3 previews to pick from; then `python3 $R music $P <track> [--start S]` → `assets/music.wav` (ducked under voice), uncomment the `<audio id="music">` line, and put the CC BY credit in the caption.

## Gotchas

- iPhone clips are HLG HDR: `prep` tone-maps them; if a render comes out HDR/washed, the face file lost its bt709 tags.
- Phone voice is often dull (little energy at 3-10 kHz). `prep` reads the audio straight from the original clip and uses de-mud + presence (+7 dB at 3.6 kHz) + an air shelf + de-ess, with no FFT denoise (it removes the highs that make speech crisp). The cut removes the pauses, so room noise between words never reaches the reel.
- A GSAP `fromTo` placed later on an element that is visible earlier needs `immediateRender: false`, or its from-state shows from frame 0.
- Inter loads from the system; Instrument Serif from `assets/fonts` (each scene declares its own `@font-face`).
- Every timed element needs `class="clip"`; a scene's timeline must be registered as `window.__timelines["<composition-id>"]`.
- Text safe zone: y 230-1440, keep the right 230 px clear of key text (IG buttons).

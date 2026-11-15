#!/usr/bin/env python3
"""Reel pipeline: edit a face-cam reel in the editorial kinetic-type style, repeatably.

  reel.py new    <reels_dir>/<name>                 copy the template project
  reel.py prep   <project> <clip.MOV> [clip2 ...]   HLG->SDR, grade, clean voice  -> edit/face_src.mp4, edit/voice_src.wav
  reel.py cut    <project> [--speed 1.12] [--drop 3.1-5.4,...] [--reset] [--th -30.5]
                                                    dead air + micro pauses out, speed up -> assets/face.mp4, assets/voice.wav
                                                    and patches index.html (durations, jump-cut punches)
  reel.py words  <project> [--script edit/script.txt] Whisper (or script alignment) on the CUT voice -> edit/words.json
  reel.py music  <project> <track> [--start auto|S] duck a bed under the voice -> assets/music.wav (+ edit/preview.mp3)
  reel.py beds   <project> <track> [track ...]      30 s mixed previews of several beds for the user to pick
  reel.py snap   <project> <t1,t2,...>              small contact strip of frames -> edit/snap.jpg (cheap visual check)
  reel.py render <project> [name]                   SDR 30 fps high quality -> renders/<name>.mp4

Only stdlib + ffmpeg/ffprobe + swift (macOS) + Node (npx hyperframes). Run from anywhere.
"""
import argparse, array, glob, json, math, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(os.path.dirname(HERE), "template")
HF = ["npx", "--yes", "hyperframes@0.9.46"]

GRADE = ("eq=contrast=1.06:saturation=0.88,"
         "curves=all='0/0.02 0.25/0.22 0.75/0.79 1/0.98',"
         "colorbalance=rs=-0.015:bs=0.025:rh=0.025:bh=-0.015,vignette=angle=PI/5")
VOICE = ("highpass=f=80,afftdn=nr=10:nf=-40,"
         "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5:LRA=9")
X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-g", "30", "-movflags", "+faststart"]


def run(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))[:300]}")
    return r


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def energy_db(path, rate=16000, win=160):
    """dB per 10 ms window of a mono 16 kHz render of `path`."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2])
    out = []
    for i in range(0, len(a) - win, win):
        s = 0
        for x in a[i:i + win]:
            s += x * x
        out.append(10 * math.log10(s / win / 32768 ** 2 + 1e-12))
    return out


def fmt(v):
    s = f"{max(0.0, v):.3f}".rstrip("0").rstrip(".")
    return s or "0"


# ---------------------------------------------------------------- new
def cmd_new(a):
    dst = os.path.abspath(a.project)
    if os.path.exists(dst):
        sys.exit(f"{dst} already exists")
    shutil.copytree(TEMPLATE, dst)
    name = os.path.basename(dst)
    for d in ("edit", "renders", "assets/shots", "assets/ig"):
        os.makedirs(os.path.join(dst, d), exist_ok=True)
    json.dump({"name": name, "private": True, "type": "module", "scripts": {
        "dev": "npx --yes hyperframes@0.9.46 preview", "check": "npx --yes hyperframes@0.9.46 check",
        "render": "npx --yes hyperframes@0.9.46 render"}}, open(os.path.join(dst, "package.json"), "w"), indent=2)
    json.dump({"id": name, "name": name}, open(os.path.join(dst, "meta.json"), "w"), indent=2)
    fetch_assets(dst)
    print("created", dst)


# Logos: simple-icons (CC0 icon data; the marks are their owners' trademarks), with a brand fill added.
LOGOS = {"claude": "D97757", "github": "181717", "instagram": "FF0069", "openai": "412991"}
# Template SFX names -> HyperFrames' bundled library (Pixabay Content License; fetched, not redistributed here).
SFX = {"whoosh": "whoosh", "pop": "pop", "sfx_002": "pop", "tick": "key-press", "sfx_003": "click", "shutter": "click-soft"}


def fetch_assets(dst):
    import urllib.request
    logos = os.path.join(dst, "assets", "logos"); os.makedirs(logos, exist_ok=True)
    for slug, hexc in LOGOS.items():
        url = f"https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{slug}.svg"
        try:
            svg = urllib.request.urlopen(url, timeout=20).read().decode()
            open(os.path.join(logos, f"{slug}.svg"), "w").write(svg.replace("<svg ", f'<svg fill="#{hexc}" ', 1))
        except Exception as e:
            print(f"warning: logo {slug} not fetched ({e}); add assets/logos/{slug}.svg yourself")
    sfx = os.path.join(dst, "assets", "sfx"); os.makedirs(sfx, exist_ok=True)
    got = {}
    for name, key in SFX.items():
        if key not in got:
            r = subprocess.run(HF + ["media-use", "resolve", "--type", "sfx", "--intent", key, "--local-only",
                                     "-p", dst, "--json"], capture_output=True, text=True)
            try:
                got[key] = os.path.join(dst, json.loads(r.stdout.strip().splitlines()[-1])["path"])
            except Exception:
                print(f"warning: sfx '{key}' not fetched; put an mp3 at assets/sfx/{name}.mp3")
                continue
        shutil.copy(got[key], os.path.join(sfx, f"{name}.mp3"))


# ---------------------------------------------------------------- prep
def sdr_binary():
    b = os.path.join(HERE, "sdr")
    if not os.path.exists(b):
        run(["swiftc", "-O", os.path.join(HERE, "sdr.swift"), "-o", b])
    return b


def cmd_prep(a):
    P = os.path.abspath(a.project); E = os.path.join(P, "edit"); os.makedirs(E, exist_ok=True)
    srcs = []
    for i, clip in enumerate(a.clips):
        trc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=color_transfer", "-of", "csv=p=0", clip], capture_output=True, text=True).stdout.strip().strip(",")
        if trc in ("arib-std-b67", "smpte2084"):
            out = os.path.join(E, f"sdr_{i}.mov")
            print(f"[{i}] {os.path.basename(clip)} is HDR ({trc}) -> tone-mapping to BT.709")
            run([sdr_binary(), clip, out], stdout=subprocess.DEVNULL)
            srcs.append(out)
        else:
            srcs.append(clip)
    ins = sum([["-i", s] for s in srcs], [])
    n = len(srcs)
    fc = []
    for i in range(n):
        fc.append(f"[{i}:v]fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v{i}]")
        fc.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
    fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]{GRADE},setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709[vo]"); fc.append(f"[ac]{VOICE}[ao]")
    run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc),
         "-map", "[vo]", *X264, os.path.join(E, "face_src.mp4"),
         "-map", "[ao]", "-c:a", "pcm_s16le", "-ar", "48000", os.path.join(E, "voice_src.wav")])
    for f in glob.glob(os.path.join(E, "sdr_*.mov")):
        os.remove(f)
    print(f"face_src.mp4 + voice_src.wav  ({dur(os.path.join(E, 'voice_src.wav')):.2f}s)")


# ---------------------------------------------------------------- cut
def speech_segments(db, th, min_gap=0.14, min_len=0.08):
    sm = [sum(db[max(0, k - 2):k + 3]) / len(db[max(0, k - 2):k + 3]) for k in range(len(db))]
    segs, st = [], None
    for k, v in enumerate(sm):
        t = k * 0.01
        if v >= th and st is None: st = t
        if v < th and st is not None: segs.append([st, t]); st = None
    if st is not None: segs.append([st, len(sm) * 0.01])
    m = []
    for s in segs:
        if m and s[0] - m[-1][1] < min_gap: m[-1][1] = s[1]
        else: m.append(s)
    return [s for s in m if s[1] - s[0] >= min_len]


def cmd_cut(a):
    P = os.path.abspath(a.project); E = os.path.join(P, "edit")
    face, voice = os.path.join(E, "face_src.mp4"), os.path.join(E, "voice_src.wav")
    db = energy_db(voice); END = len(db) * 0.01
    srt = sorted(db); floor, loud = srt[len(srt) // 10], srt[len(srt) * 9 // 10]
    th = a.th if a.th is not None else max(-30.5, floor + 4)
    print(f"noise floor {floor:.1f} dB, speech {loud:.1f} dB, threshold {th:.1f} dB")
    segs = speech_segments(db, th)
    # --drop uses CUT times (as printed by `words`); mapped back to source through the last cuts.json.
    # Drops accumulate in edit/drops.json; `--reset` clears them.
    dj = os.path.join(E, "drops.json")
    drops = [] if a.reset or not os.path.exists(dj) else json.load(open(dj))
    if a.drop:
        prev = json.load(open(os.path.join(E, "cuts.json")))
        def src(t):
            acc = 0
            for s0, e0 in prev["spans"]:
                L = (e0 - s0) / prev["speed"]
                if t <= acc + L: return s0 + (t - acc) * prev["speed"]
                acc += L
            return prev["spans"][-1][1]
        for r in a.drop.split(","):
            x, y = map(float, r.split("-")); drops.append([round(src(x), 3), round(src(y), 3)])
    json.dump(drops, open(dj, "w"))
    if drops: print("dropping source ranges", drops)
    for x, y in drops:
        out = []
        for s0, e0 in segs:
            if e0 <= x or s0 >= y: out.append([s0, e0])
            else:
                if s0 < x - 0.08: out.append([s0, x])
                if e0 > y + 0.08: out.append([y, e0])
        segs = out
    PRE, POST = 0.06, 0.08
    keep = []
    for s, e in segs:
        x, y = max(0, s - PRE), min(END, e + POST)
        if keep and x <= keep[-1][1]: keep[-1][1] = y
        else: keep.append([x, y])
    if keep: keep[-1][1] = min(END, keep[-1][1] + a.tail)
    # micro pauses inside kept spans (breaths, "uh" gaps): >= 0.12 s below th+3.5
    dip_th, PAD, spans = th + 3.5, 0.035, []
    for s, e in keep:
        cur, st = s, None
        for k in range(int(s * 100) + 8, int(e * 100) - 8):
            if db[k] < dip_th: st = k if st is None else st
            else:
                if st is not None and k - st >= 12:
                    spans.append([cur, st / 100 + PAD]); cur = k / 100 - PAD
                st = None
        spans.append([cur, e])
    sp = a.speed
    v, au = [], []
    for i, (s, e) in enumerate(spans):
        v.append(f"[0:v]trim=start={s:.4f}:end={e:.4f},setpts=PTS-STARTPTS[v{i}]")
        au.append(f"[1:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,"
                  f"afade=t=out:st={max(0, e - s - 0.012):.4f}:d=0.012[a{i}]")
    n = len(spans)
    fc = ";".join(v + au + ["".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]",
                            f"[vc]setpts=PTS/{sp},fps=30[vo]", f"[ac]atempo={sp}[ao]"])
    open(os.path.join(E, "cut_fc.txt"), "w").write(fc)
    A = os.path.join(P, "assets"); os.makedirs(A, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-i", face, "-i", voice, "-filter_complex_script", os.path.join(E, "cut_fc.txt"),
         "-map", "[vo]", *X264, os.path.join(A, "face.mp4"),
         "-map", "[ao]", "-c:a", "pcm_s16le", "-ar", "48000", os.path.join(A, "voice.wav")])
    total = round(dur(os.path.join(A, "voice.wav")), 3)
    acc, bounds = 0, []
    for s, e in spans[:-1]:
        acc += e - s; bounds.append(round(acc / sp, 3))
    json.dump({"speed": sp, "total": total, "spans": spans, "cuts": bounds, "source_len": END, "th": th},
              open(os.path.join(E, "cuts.json"), "w"), indent=1)
    print(f"{len(segs)} phrases, {n} spans, {END:.1f}s -> {total:.2f}s, {len(bounds)} jump cuts")
    patch_index(P, total, bounds)


def patch_index(P, total, bounds):
    f = os.path.join(P, "index.html")
    if not os.path.exists(f): return
    s = open(f).read()
    s = re.sub(r'(<[^>]*\bdata-full\b[^>]*?data-duration=")[\d.]+(")', lambda m: m.group(1) + fmt(total) + m.group(2), s)
    s = re.sub(r'(<[^>]*?data-duration=")[\d.]+("[^>]*\bdata-full\b)', lambda m: m.group(1) + fmt(total) + m.group(2), s)
    toggles = "\n".join(f'      tl.set("#facewrap", {{ scale: {1.07 if i % 2 == 0 else 1} }}, {b});' for i, b in enumerate(bounds))
    s = re.sub(r"(// CUTS:BEGIN).*?(\n\s*// CUTS:END)", lambda m: m.group(1) + "\n" + toggles + m.group(2), s, flags=re.S)
    open(f, "w").write(s)
    print(f"index.html: full-length clips -> {total}s, {len(bounds)} punch toggles")


# ---------------------------------------------------------------- words
def cmd_words(a):
    P = os.path.abspath(a.project); E = os.path.join(P, "edit"); V = os.path.join(P, "assets", "voice.wav")
    tmp = os.path.join(E, "tx"); os.makedirs(tmp, exist_ok=True); shutil.copy(V, os.path.join(tmp, "voice.wav"))
    HING = {"hai", "hain", "ka", "ki", "ke", "se", "nahi", "ko", "karo", "ab", "bhai", "kya", "mein", "aur", "ye", "jo", "ek"}

    def tx(lang):
        r = subprocess.run(HF + ["transcribe", os.path.join(tmp, "voice.wav"), "--engine", "whisper", "--model", a.model,
                                 "--language", lang, "--json"], cwd=P, capture_output=True, text=True)
        path = None
        for line in r.stdout.splitlines()[::-1]:
            try:
                o = json.loads(line)
                if o.get("transcriptPath"): path = o["transcriptPath"]; break
            except Exception: pass
        path = path or os.path.join(tmp, "transcript.json")
        if not os.path.exists(path): sys.exit("transcribe failed:\n" + (r.stdout + r.stderr)[-800:])
        w = json.load(open(path)); return w if isinstance(w, list) else w["words"]

    if a.script:
        return words_from_script(P, E, V, a.script)
    w = tx(a.language)
    translated = a.language == "en" and sum(re.sub(r"[^a-z]", "", x["text"].lower()) in HING for x in w) < max(2, len(w) * 0.04)
    db = energy_db(V)
    ons = []
    for k in range(8, len(db)):
        if db[k] >= -24 and db[k - 1] < -24 and min(db[k - 8:k]) < -28:
            if not ons or k / 100 - ons[-1] > 0.08: ons.append(k / 100)
    out = []
    for x in w:
        t = x["start"]; near = [o for o in ons if abs(o - t) <= 0.12]
        if near: t = min(near, key=lambda o: abs(o - t))
        out.append({"t": round(t, 3), "e": round(x["end"], 3), "w": x["text"].strip()})
    for i in range(1, len(out)):
        if out[i]["t"] < out[i - 1]["t"] + 0.04: out[i]["t"] = round(out[i - 1]["t"] + 0.04, 3)
    json.dump(out, open(os.path.join(E, "words.json"), "w"), indent=0)
    # compact print: one phrase per line (break after punctuation, a long gap, or 9 words)
    line, prev = [], None
    for x in out:
        if line and (prev["w"][-1:] in ".,?!" or x["t"] - prev["t"] > 0.5 or len(line) >= 9):
            print("  ".join(line)); line = []
        line.append(f'{x["t"]:.2f} {x["w"]}'); prev = x
    if line: print("  ".join(line))
    print(f"-> edit/words.json ({len(out)} words, voice {dur(V):.2f}s)")
    if translated:
        print("WARNING: Whisper TRANSLATED the Hinglish to English (it does this at random). Phrase start times above are still "
              "right, word times inside a phrase are not. Write the spoken lines to edit/script.txt and rerun: words --script edit/script.txt")


def onsets_of(db):
    ons = []
    for k in range(8, len(db)):
        if db[k] >= -24 and db[k - 1] < -24 and min(db[k - 8:k]) < -28:
            if not ons or k / 100 - ons[-1] > 0.08: ons.append(k / 100)
    return ons


def syl(word):
    return max(1, len(re.findall(r"[aeiouy]+", word.lower()))) + 0.4 + (0.6 if re.search(r"\d", word) else 0)


def words_from_script(P, E, V, script_path):
    """Place the KNOWN script words on the cut voice. Phrases (split at punctuation) are aligned to pauses with a
    small DP (steady speaking rate, phrase starts prefer real pauses); words inside a phrase are spread by
    syllables over voiced time and snapped to energy onsets. ASR text is never trusted (it translates Hinglish)."""
    toks = [t for t in re.split(r"\s+", open(script_path).read()) if re.search(r"\w", t)]
    db = energy_db(V)
    cj = os.path.join(E, "cuts.json")
    th = json.load(open(cj)).get("th", -30.5) if os.path.exists(cj) else -30.5
    segs = speech_segments(db, th, min_gap=0.06)
    # voiced-time axis (pauses removed)
    seg_v, acc = [], 0
    for s0, e0 in segs: seg_v.append(acc); acc += e0 - s0
    voiced = acc
    def at(v):
        for (s0, e0), sv in zip(segs, seg_v):
            if v <= sv + (e0 - s0): return s0 + (v - sv)
        return segs[-1][1]
    # phrases
    units, cur = [], []
    for i, t in enumerate(toks):
        cur.append(i)
        if t[-1] in ".,?!:;" or i == len(toks) - 1: units.append(cur); cur = []
    W = [syl(t) for t in toks]; UW = [sum(W[i] for i in u) for u in units]
    rate = voiced / sum(UW)
    # candidate phrase starts: every pause (cost 0) + a 0.1 s grid of voiced time (cost GRIDP)
    GRIDP = 0.6
    cd = {round(v, 3): 0.0 for v in seg_v}
    cand = sorted(cd.items())
    have = {c for c, _ in cand}
    cand += [(round(g * 0.1, 3), GRIDP) for g in range(1, int(voiced * 10)) if all(abs(g * 0.1 - h) > 0.08 for h in have)]
    cand.sort(); C = [c for c, _ in cand]; PEN = [p for _, p in cand]; N = len(C)
    INF = float("inf"); U = len(units)
    best = [[INF] * N for _ in range(U)]; back = [[-1] * N for _ in range(U)]
    best[0][0] = 0.0
    def cost(j, a_, b_):
        d = b_ - a_; exp = UW[j] * rate
        return ((d - exp) / max(0.25, exp)) ** 2 * 3
    for j in range(1, U):
        for k in range(N):
            for i in range(k):
                if best[j - 1][i] == INF: continue
                c = best[j - 1][i] + cost(j - 1, C[i], C[k]) + PEN[k]
                if c < best[j][k]: best[j][k] = c; back[j][k] = i
    end = min(range(N), key=lambda k: best[U - 1][k] + cost(U - 1, C[k], voiced) if best[U - 1][k] < INF else INF)
    ust = [0.0] * U; k = end
    for j in range(U - 1, -1, -1):
        ust[j] = C[k]; k = back[j][k] if j else 0
    starts = {}
    for j, u in enumerate(units):
        v0, v1 = ust[j], (ust[j + 1] if j + 1 < U else voiced)
        span = UW[j]; acc = 0
        for i in u: starts[i] = v0 + (v1 - v0) * acc / span; acc += W[i]
    ons = onsets_of(db); out = []
    for i, t in enumerate(toks):
        r = at(starts[i] + 1e-4)
        if any(i == u[0] for u in units) and any(abs(r - s0) < 0.02 for s0, _ in segs):
            pass  # phrase start on a pause boundary: keep
        else:
            near = [o for o in ons if abs(o - r) <= 0.15]
            if near: r = min(near, key=lambda o: abs(o - r))
        out.append({"t": round(r, 3), "w": t})
    for i in range(len(out)):
        if i and out[i]["t"] < out[i - 1]["t"] + 0.06: out[i]["t"] = round(out[i - 1]["t"] + 0.06, 3)
    for i in range(len(out)):
        out[i]["e"] = out[i + 1]["t"] if i + 1 < len(out) else round(segs[-1][1], 3)
    json.dump(out, open(os.path.join(E, "words.json"), "w"), indent=0)
    for u in units: print("  ".join(f'{out[i]["t"]:.2f} {out[i]["w"]}' for i in u))
    print(f"-> edit/words.json ({len(out)} script words, {U} phrases on {len(segs)} speech segments, voice {dur(V):.2f}s)")


# ---------------------------------------------------------------- music
def best_start(track, length):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", track, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2]); W = 4000
    e = [10 * math.log10(sum(x * x for x in a[i * W:(i + 1) * W]) / W / 32768 ** 2 + 1e-12) for i in range(len(a) // W)]
    n = int(length * 2); best = (None, 0)
    for s in range(0, max(1, len(e) - n - 4)):
        win = e[s:s + n] or [-90]; m = sum(win) / len(win); rise = e[s] - (e[s - 2] if s >= 2 else -60)
        sc = m + 0.2 * min(win) + 0.15 * max(0, rise)
        if best[0] is None or sc > best[0]: best = (sc, s / 2)
    return best[1]


def make_bed(P, track, start, out):
    V = os.path.join(P, "assets", "voice.wav"); T = dur(V)
    if start == "auto": start = best_start(track, T)
    start = float(start)
    fc = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-21:TP=-2:LRA=11,"
          f"equalizer=f=2800:t=q:w=1.2:g=-4,afade=t=in:d=0.04,afade=t=out:st={max(0, T - 1.3):.3f}:d=1.3[m];"
          f"[1:a]aresample=48000,aformat=channel_layouts=stereo[k];"
          f"[m][k]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=300:makeup=1,volume=3.5dB,alimiter=limit=0.7[out]")
    run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-ss", f"{start}", "-t", f"{T}", "-i", track, "-i", V,
         "-filter_complex", fc, "-map", "[out]", "-c:a", "pcm_s16le", out])
    return start


def preview(P, bed, out):
    V = os.path.join(P, "assets", "voice.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", V, "-i", bed, "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0[o]",
         "-map", "[o]", "-c:a", "libmp3lame", "-b:a", "160k", out])


def cmd_music(a):
    P = os.path.abspath(a.project); out = os.path.join(P, "assets", "music.wav")
    st = make_bed(P, a.track, a.start, out)
    preview(P, out, os.path.join(P, "edit", "preview.mp3"))
    print(f"assets/music.wav from {os.path.basename(a.track)} @ {st}s; listen: {os.path.join(P, 'edit', 'preview.mp3')}")
    print('set <audio id="music" ... data-volume="1"> in index.html; credit CC BY tracks in the caption')


def cmd_beds(a):
    P = os.path.abspath(a.project); D = os.path.join(P, "edit", "beds"); os.makedirs(D, exist_ok=True)
    for i, t in enumerate(a.tracks):
        b = os.path.join(D, f"bed{i}.wav"); st = make_bed(P, t, "auto", b)
        o = os.path.join(D, f"{i} - {os.path.splitext(os.path.basename(t))[0]}.mp3"); preview(P, b, o); os.remove(b)
        print(f"{o}  (start {st}s)")


# ---------------------------------------------------------------- snap / render
def cmd_snap(a):
    P = os.path.abspath(a.project); D = os.path.join(P, "edit", "snaps")
    shutil.rmtree(D, ignore_errors=True)
    run(HF + ["snapshot", "--at", a.times, "--no-end", "-o", D], cwd=P, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pngs = sorted(glob.glob(os.path.join(D, "*.png")))
    if not pngs: sys.exit("no snapshots written")
    ins = sum([["-i", p] for p in pngs], [])
    fc = ";".join(f"[{i}:v]scale={a.width}:-1[s{i}]" for i in range(len(pngs)))
    fc += ";" + "".join(f"[s{i}]" for i in range(len(pngs))) + (f"hstack=inputs={len(pngs)}" if len(pngs) > 1 else "null")
    out = os.path.join(P, "edit", "snap.jpg")
    run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-frames:v", "1", out])
    print(out)


def cmd_render(a):
    P = os.path.abspath(a.project); name = a.name or os.path.basename(P)
    os.makedirs(os.path.join(P, "renders"), exist_ok=True)
    out = os.path.join("renders", f"{name}.mp4")
    r = subprocess.run(HF + ["render", "--sdr", "--fps", "30", "--quality", "high", "-o", out], cwd=P, capture_output=True, text=True)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if re.search(r"MB|rror|arn", l)]
    print("\n".join(tail[-6:]))
    print(os.path.join(P, out) if r.returncode == 0 else "render failed")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new"); s.add_argument("project"); s.set_defaults(f=cmd_new)
    s = sub.add_parser("prep"); s.add_argument("project"); s.add_argument("clips", nargs="+"); s.set_defaults(f=cmd_prep)
    s = sub.add_parser("cut"); s.add_argument("project"); s.add_argument("--speed", type=float, default=1.12)
    s.add_argument("--drop", help="ranges to remove in CURRENT cut time (from `words`), e.g. 3.1-5.4,20-22.5")
    s.add_argument("--reset", action="store_true", help="forget earlier drops")
    s.add_argument("--th", type=float, help="speech threshold dB (default: auto, about -30.5)")
    s.add_argument("--tail", type=float, default=0.35, help="extra hold after the last word"); s.set_defaults(f=cmd_cut)
    s = sub.add_parser("words"); s.add_argument("project"); s.add_argument("--model", default="medium")
    s.add_argument("--language", default="en")
    s.add_argument("--script", help="text file with the spoken lines as recorded (e.g. Roman Hinglish); aligns these words instead of trusting ASR text")
    s.set_defaults(f=cmd_words)
    s = sub.add_parser("music"); s.add_argument("project"); s.add_argument("track"); s.add_argument("--start", default="auto"); s.set_defaults(f=cmd_music)
    s = sub.add_parser("beds"); s.add_argument("project"); s.add_argument("tracks", nargs="+"); s.set_defaults(f=cmd_beds)
    s = sub.add_parser("snap"); s.add_argument("project"); s.add_argument("times"); s.add_argument("--width", type=int, default=270); s.set_defaults(f=cmd_snap)
    s = sub.add_parser("render"); s.add_argument("project"); s.add_argument("name", nargs="?"); s.set_defaults(f=cmd_render)
    a = p.parse_args(); a.f(a)


if __name__ == "__main__":
    main()

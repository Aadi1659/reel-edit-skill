"""Gentle re-cut (17 Nov): whole sentences, no micro-pause cuts, soft fades, raw voice (gain + limiter only).

python3 recut.py <project> [--th -29] [--merge 0.6] [--pre 0.12] [--post 0.3] [--speed 1.05]

Speech = 10 ms energy of edit/voice_nat.wav above --th (set above the level of any background audio).
Phrases closer than --merge are one sentence (the pause stays). Which takes are kept is read from the CURRENT
edit/cuts.json (a new phrase is kept if it overlaps a kept span), so earlier take choices carry over.
Writes edit/cuts.json (old one -> cuts_prev.json), edit/cut_fc.txt, assets/face.mp4, assets/voice.wav.
"""
import argparse, array, json, math, os, shutil, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("project"); ap.add_argument("--th", type=float, default=-29); ap.add_argument("--merge", type=float, default=0.6)
ap.add_argument("--pre", type=float, default=0.12); ap.add_argument("--post", type=float, default=0.3)
ap.add_argument("--speed", type=float, default=1.05); ap.add_argument("--minlen", type=float, default=0.25)
ap.add_argument("--add", default="", help="extra source ranges to keep, a-b,c-d"); ap.add_argument("--drop", default="", help="source ranges to remove")
ap.add_argument("--cut", default="", help="source ranges cut out of kept spans, even mid-span")
ap.add_argument("--maxtail", type=float, default=0.0, help="smart tail: hold up to this long after a phrase until silence")
ap.add_argument("--silence", type=float, default=-37.0, help="level counted as silence for the smart tail")
a = ap.parse_args()
P = os.path.abspath(a.project); E = os.path.join(P, "edit"); A = os.path.join(P, "assets")
# raw voice: edit/voice_nat.wav if present (older projects), else edit/voice_src.wav (prep keeps it raw since 17 Nov)
VSRC = os.path.join(E, "voice_nat.wav")
if not os.path.exists(VSRC): VSRC = os.path.join(E, "voice_src.wav")

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VSRC, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True).stdout
x = array.array("h", raw); n = 160
db = []
for i in range(0, len(x), n):
    seg = x[i:i + n]; r = math.sqrt(sum(v * v for v in seg) / max(1, len(seg))) / 32768
    db.append(20 * math.log10(r + 1e-9))
END = len(db) * 0.01
sm = [sum(db[max(0, k - 3):k + 4]) / len(db[max(0, k - 3):k + 4]) for k in range(len(db))]
segs, st = [], None
for k, v in enumerate(sm):
    if v >= a.th and st is None: st = k * 0.01
    if v < a.th and st is not None: segs.append([st, k * 0.01]); st = None
if st is not None: segs.append([st, END])
segs = [s for s in segs if s[1] - s[0] >= 0.06]
merged = []
for s in segs:
    if merged and s[0] - merged[-1][1] < a.merge: merged[-1][1] = s[1]
    else: merged.append(list(s))
merged = [s for s in merged if s[1] - s[0] >= a.minlen]

CJ = os.path.join(E, "cuts.json")
prev = json.load(open(CJ)) if os.path.exists(CJ) else None   # first run: no earlier cut -> keep every sentence
if prev: shutil.copy(CJ, os.path.join(E, "cuts_prev.json"))
def overlaps(s, e, spans): return any(min(e, y) - max(s, x0) > 0.15 for x0, y in spans)
keep = [s for s in merged if prev is None or overlaps(s[0], s[1], prev["spans"])]
for r in filter(None, a.add.split(",")):
    p, q = map(float, r.split("-")); keep.append([p, q])
for r in filter(None, a.drop.split(",")):
    p, q = map(float, r.split("-")); keep = [s for s in keep if not (s[0] >= p - 0.05 and s[1] <= q + 0.05)]
keep.sort()


def smart_tail(e):
    """Hold after a phrase until the voice has died to silence; stop early if a NEW sound starts (e.g. a background video)."""
    k, lim, quiet = int(e * 100), min(len(db), int((e + a.maxtail) * 100)), False
    while k < lim:
        if db[k] < a.silence: quiet = True
        elif quiet and sm[k] > a.silence + 3: return k / 100 - 0.03
        k += 1
    return k / 100


spans = []
for s, e in keep:
    x0, y = max(0, s - a.pre), min(END, max(e + a.post, smart_tail(e)) if a.maxtail else e + a.post)
    if spans and x0 <= spans[-1][1]: spans[-1][1] = max(spans[-1][1], y)
    else: spans.append([round(x0, 3), round(y, 3)])

for r in filter(None, a.cut.split(",")):   # subtract source ranges from the padded spans (trims inside a sentence)
    p, q = map(float, r.split("-")); out = []
    for s, e in spans:
        if e <= p or s >= q: out.append([s, e]); continue
        if s < p - 0.05: out.append([s, p])
        if e > q + 0.05: out.append([q, e])
    spans = out
sp = a.speed
v, au = [], []
for i, (s, e) in enumerate(spans):
    v.append(f"[0:v]trim=start={s:.4f}:end={e:.4f},setpts=PTS-STARTPTS[v{i}]")
    au.append(f"[1:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,"
              f"afade=t=out:st={max(0, e - s - 0.08):.4f}:d=0.08[a{i}]")
k = len(spans)
fc = ";".join(v + au + ["".join(f"[v{i}][a{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=1[vc][ac]",
                        f"[vc]setpts=PTS/{sp},fps=30[vo]", f"[ac]atempo={sp}[ao]"])
open(os.path.join(E, "cut_fc.txt"), "w").write(fc)
X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-colorspace", "bt709", "-g", "30", "-movflags", "+faststart"]
cutraw = os.path.join(E, "voice_cut_raw.wav")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(E, "face_src.mp4"), "-i", VSRC,
                "-filter_complex_script", os.path.join(E, "cut_fc.txt"), "-map", "[vo]", *X264, os.path.join(A, "face.mp4"),
                "-map", "[ao]", "-c:a", "pcm_s16le", "-ar", "48000", cutraw], check=True)
lu = subprocess.run(["ffmpeg", "-v", "info", "-i", cutraw, "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float([l for l in lu.splitlines() if l.strip().startswith("I:")][-1].split()[1])
g = round(-14 - I, 2)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", cutraw, "-af", f"volume={g}dB,alimiter=limit=0.89:attack=5:release=50:level=disabled",
                "-c:a", "pcm_s16le", "-ar", "48000", os.path.join(A, "voice.wav")], check=True)
total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(A, "voice.wav")],
                             capture_output=True, text=True).stdout)
acc, cuts = 0, []
for s, e in spans[:-1]:
    acc += (e - s) / sp; cuts.append(round(acc, 3))
json.dump({"speed": sp, "total": round(total, 3), "spans": spans, "cuts": cuts, "source_len": END, "th": a.th}, open(os.path.join(E, "cuts.json"), "w"), indent=1)
print(f"{len(spans)} spans, {total:.2f}s, gain +{g} dB")
acc = 0
for s, e in spans:
    print(f"  out {acc:6.2f}-{acc + (e - s) / sp:6.2f}  src {s:7.2f}-{e:7.2f}"); acc += (e - s) / sp

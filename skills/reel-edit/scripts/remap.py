"""Re-time a finished edit/build_index.py after a re-cut: every time literal is mapped old cut -> source -> new cut.

    cp edit/cuts.json edit/cuts_old.json   # BEFORE running `reel.py cut` again
    python3 reel.py cut ...                # writes the new edit/cuts.json
    python3 remap.py <project> edit/cuts_old.json      # rewrites edit/build_index.py (backup: build_index_pre_remap.py)

A time that falls in removed audio snaps to the start of the next kept span. Durations (duration:, stagger:, the 3rd arg
of draw(), offsets like `t + 0.1`) are never touched. All patterns run in ONE pass (separate passes double-mapped
W() word times on reel 5). Check the printed section boundaries, then rebuild, `check`, and `snap`.
"""
import json, os, re, shutil, sys

P, OLD = sys.argv[1], sys.argv[2]
o = json.load(open(OLD if os.path.isabs(OLD) else os.path.join(P, OLD)))
n = json.load(open(os.path.join(P, "edit/cuts.json")))


def to_src(t, c):
    acc = 0
    for s, e in c["spans"]:
        L = (e - s) / c["speed"]
        if t <= acc + L + 1e-9: return s + (t - acc) * c["speed"]
        acc += L
    return c["spans"][-1][1]


def from_src(x, c):
    acc = 0
    for s, e in c["spans"]:
        L = (e - s) / c["speed"]
        if x < s: return acc
        if x <= e: return acc + (x - s) / c["speed"]
        acc += L
    return acc


M = lambda t: round(from_src(to_src(t, o), n), 3)
f = os.path.join(P, "edit/build_index.py")
shutil.copy(f, os.path.join(P, "edit/build_index_pre_remap.py"))
s = open(f).read()
pats = [r'\}\}?, (?P<t>\d+\.\d+)\)',                                   # gsap position param
        r'(?:scene_in|scene_out|enter|draw|chip|fade)\("[^"]+", (?P<t>\d+\.\d+)',
        r'W\((?P<t>\d+\.\d+),', r'data-t="\{(?P<t>\d+\.\d+)\}"',
        r'(?<![W\w])\((?P<t>\d+\.\d+), (?:None|")',                    # CAP tuples
        r'\("\w+", (?P<t>\d+\.\d+), \d',                               # sfx tuples
        r'(?P<t>\d+\.\d+) \+ k \*',                                    # sfx ranges
        r'data-start="(?P<t>\d+\.\d+)"',
        r'^(?:FULL_END|GO_FULL) = (?P<t>\d+\.\d+)']
big = "|".join(f"(?:{p.replace('(?P<t>', '(?P<t%d>' % i)})" for i, p in enumerate(pats))


def R(m):
    for i in range(len(pats)):
        g = m.group(f"t{i}")
        if g is not None:
            a, b = m.span(f"t{i}")
            return m.group(0)[:a - m.start()] + str(M(float(g))) + m.group(0)[b - m.start():]
    return m.group(0)


s = re.sub(big, R, s, flags=re.M)
# multi-time calls: every number in the match is a time (kept out of the one-pass regex because they overlap)
num = lambda m: re.sub(r'\d+\.\d+', lambda x: str(M(float(x.group(0)))), m.group(0))
s = re.sub(r'cbox_js\(\d+\.\d+, \d+\.\d+, \d+\.\d+\)', num, s)
s = re.sub(r"'(?:top|)', (?:FULL_END|GO_FULL|\d+\.\d+), (?:GO_FULL|TOTAL|\d+\.\d+),", num, s)
# tuples of 3 times (e.g. `for t_in, t_hit, t_rdy in [(..), ..]`) and header rows ("01", "cat", "name", a, b, tn, tname, size)
s = re.sub(r'\((\d+\.\d+), (\d+\.\d+), (\d+\.\d+)\)(?=[,\]])', lambda m: f'({M(float(m[1]))}, {M(float(m[2]))}, {M(float(m[3]))})', s)
s = re.sub(r'("[^"]+", )(\d+\.\d+), (\d+\.\d+), (\d+\.\d+), (\d+\.\d+), (\d+\))',
           lambda m: m[1] + ", ".join(str(M(float(m[i]))) for i in range(2, 6)) + ", " + m[6], s)
open(f, "w").write(s)
print("remapped", f)
for c in [0.5, 1.0, 2.0, 5.0, 10.0, o["total"] - 0.5]:
    print(f"  old {c:6.2f} -> new {M(c):6.2f}")
print("  old cut boundaries -> new:", [M(b) for b in o["cuts"]])

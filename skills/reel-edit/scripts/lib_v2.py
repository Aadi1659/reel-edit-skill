# Shared pieces of house style v2 (reel 4 onward): face-down window + cut-out, header type, live caption, SFX, punches.
# Each reel's edit/build_index.py imports this and supplies its own scenes (HTML + GSAP js) and type groups.
import json, os, re

S_, X_, CUT, Y_ = 0.62, 205, 150, 780
WIN = round(Y_ + CUT * S_)
RAD = round(44 / S_)
CREAM, CORAL = "#f3efe8", "#d97757"


def load_cuts(P):
    return json.load(open(os.path.join(P, "edit/cuts.json")))


def svg_logo(P, f, size, col=None):
    svg = open(os.path.join(P, "assets/logos", f)).read()
    svg = re.sub(r'<svg ', f'<svg width="{size}" height="{size}" ', svg, count=1)
    if col:
        svg = svg.replace("<path ", f'<path fill="{col}" ')
    return svg


def W(t, txt, cls=""):
    c = f' {cls}' if cls else ""
    return f'<span class="w{c}" data-t="{round(t, 3)}">{txt}</span>'


BASE_CSS = f'''
      @font-face {{ font-family: "Instrument Serif"; font-style: italic; font-weight: 400; src: url("assets/fonts/InstrumentSerif-Italic.woff2") format("woff2"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #0e0e0e; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #0e0e0e; }}
      .fill {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }}
      .hide0 {{ opacity: 0; visibility: hidden; }}
      #stage {{ background: radial-gradient(90% 40% at 50% 26%, rgba(217,119,87,0.15) 0%, rgba(217,119,87,0) 70%), linear-gradient(180deg, #121010 0%, #0e0e0e 55%, #0b0b0b 100%); }}
      #grid {{ opacity: 0.55; background-image: linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
        background-size: 72px 72px; -webkit-mask-image: linear-gradient(180deg, #000 0%, #000 40%, transparent 70%); mask-image: linear-gradient(180deg, #000 0%, #000 40%, transparent 70%); }}
      .facegrp {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; transform-origin: 0 0; }}
      #faceA {{ z-index: 2; }} #faceB {{ z-index: 4; opacity: 0; }}
      #punchA, #punchB, #driftA, #driftB {{ transform-origin: 50% 38%; }}
      #winclip {{ overflow: hidden; clip-path: inset(0px 0px 0px 0px round 0px); }}
      #face, #facecut {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }}
      #winshadow {{ position: absolute; left: 0; top: {CUT}px; width: 1080px; height: {1920 - CUT}px; border-radius: {RAD}px; opacity: 0;
        box-shadow: 0 -18px 90px rgba(0,0,0,0.7), 0 0 0 1px rgba(0,0,0,0.4); background: #000; }}
      #winborder {{ position: absolute; left: 0; top: {CUT}px; width: 1080px; height: {1920 - CUT}px; border-radius: {RAD}px; opacity: 0;
        border: 3.2px solid rgba(243,239,232,0.22); }}
      #cutwrap {{ -webkit-mask-image: linear-gradient(180deg, transparent 0px, #000 80px); mask-image: linear-gradient(180deg, transparent 0px, #000 80px); }}
      #scrim {{ z-index: 4; pointer-events: none;
        background: linear-gradient(180deg, rgba(0,0,0,0) 45%, rgba(0,0,0,0.38) 62%, rgba(0,0,0,0.55) 78%, rgba(0,0,0,0.25) 100%); }}
      #content {{ z-index: 3; }}
      .mono {{ font-family: "SF Mono", Menlo, monospace; }}
      .tile {{ position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; box-shadow: 0 18px 44px rgba(0,0,0,0.5); }}
      .tile.paid {{ background: #fff; }}
      .tile.free {{ background: {CREAM}; outline: 4px solid {CORAL}; outline-offset: -4px; }}
      .tile img {{ display: block; }}
      .conn {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: visible; }}
      .conn path {{ fill: none; stroke: {CORAL}; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }}
      .chip {{ position: absolute; transform: translate(-50%, -50%); font-family: "Instrument Serif", serif; font-style: italic; font-size: 46px; line-height: 1;
        color: #0e0e0e; background: {CORAL}; padding: 8px 22px 10px; border-radius: 30px; white-space: nowrap; }}
      .src {{ position: absolute; left: 0; right: 0; text-align: center; font-family: "SF Mono", Menlo, monospace; font-size: 20px; color: rgba(243,239,232,0.6); }}
      .cap {{ position: absolute; left: 0; right: 0; top: 708px; text-align: center; font-family: "Inter", sans-serif; font-weight: 700; font-size: 46px;
        color: #fff; letter-spacing: -0.01em; text-shadow: 0 2px 14px rgba(0,0,0,0.7); opacity: 0; visibility: hidden; z-index: 6; }}
      .cap.acc {{ color: {CORAL}; }}
      #cbox {{ position: absolute; left: 110px; top: 470px; width: 860px; height: 124px; border-radius: 62px; background: rgba(28,28,28,0.92);
        border: 2px solid rgba(255,255,255,0.22); display: flex; align-items: center; padding: 0 26px; gap: 24px;
        font-family: "Inter", sans-serif; font-size: 50px; color: #fff; box-shadow: 0 24px 60px rgba(0,0,0,0.5); }}
      #cbox .av {{ width: 78px; height: 78px; border-radius: 50%; background: linear-gradient(135deg, #f58529, #dd2a7b 50%, #8134af); flex: none; }}
      #cbox .field {{ position: relative; flex: 1; height: 62px; }}
      #cbox .ph {{ position: absolute; left: 0; top: 0; color: rgba(255,255,255,0.5); }}
      #cbox .typed {{ position: absolute; left: 0; top: 0; font-weight: 700; letter-spacing: 0.05em; }}
      #cbox .typed span {{ opacity: 0; }}
      #cbox .post {{ font-weight: 700; color: #4f9bff; opacity: 0.4; }}
'''


def cbox_html(word):
    letters = "".join(f"<span>{c}</span>" for c in word)
    return f'''<div id="cbox" class="hide0">
          <div class="av"></div>
          <div class="field"><span class="ph" id="ph">Add a comment…</span><span class="typed">{letters}</span></div>
          <div class="post" id="post">Post</div>
        </div>'''


def cbox_js(t_in, t_type, t_out, step=0.05):
    return f'''
      tl.fromTo("#cbox", {{ autoAlpha: 0, y: 40, scale: 0.94 }}, {{ autoAlpha: 1, y: 0, scale: 1, duration: 0.28, ease: "expo.out" }}, {t_in});
      document.querySelectorAll("#cbox .typed span").forEach((sp, i) => tl.to(sp, {{ opacity: 1, duration: 0.01 }}, {t_type} + i * {step}));
      tl.set("#ph", {{ opacity: 0 }}, {t_type - 0.01});
      tl.to("#post", {{ opacity: 1, duration: 0.1 }}, {t_type + 0.2});
      tl.to("#cbox", {{ autoAlpha: 0, y: -40, duration: 0.12, ease: "power2.in" }}, {t_out - 0.12});'''


def caps(CAP, acc=lambda w: False):
    h, j = [], []
    for k in range(len(CAP) - 1):
        t, w = CAP[k]; t2 = CAP[k + 1][0]
        if w is None:
            continue
        a = " acc" if acc(w) else ""
        h.append(f'<div class="cap{a}" id="cap{k}">{w}</div>')
        j.append(f'      tl.fromTo("#cap{k}", {{ autoAlpha: 0, y: 14 }}, {{ autoAlpha: 1, y: 0, duration: 0.14, ease: "power2.out" }}, {round(t - 0.02, 3)});\n'
                 f'      tl.set("#cap{k}", {{ autoAlpha: 0 }}, {round(t2 - 0.02, 3)});')
    return "".join(h), "\n".join(j)


DUR = {"whoosh": 0.9, "pop": 0.15, "tick": 0.25, "sfx_003": 0.25, "shutter": 0.7}


def sfx_html(sfx):
    sfx = sorted(sfx, key=lambda x: x[1])
    free = {k: 0 for k in (7, 8, 9, 10, 12, 13, 14, 15)}
    out = []
    for i, (n, t, v) in enumerate(sfx):
        d = DUR[n]; tr = next(k for k in sorted(free) if free[k] <= t + 1e-6); free[tr] = t + d + 0.01
        out.append(f'      <audio id="sfx{i}" src="assets/sfx/{n}.mp3" data-start="{round(t, 3)}" data-duration="{d}" data-track-index="{tr}" data-volume="{v}"></audio>')
    return "\n".join(out), len(sfx)


def toggles(cj, FULL_END, GO_FULL):
    tog, k = [], 0
    for b in cj["cuts"]:
        if b < FULL_END - 0.05 or b > GO_FULL + 0.5:
            tog.append(f'      tl.set(P2, {{ scale: {1.06 if k % 2 == 0 else 1} }}, {b});'); k += 1
    tog.append(f'      tl.set(P2, {{ scale: 1 }}, {FULL_END});')
    return "\n".join(tog)


def face_js(FULL_END, GO_FULL, TOTAL):
    s = f'''
      tl.fromTo(D, {{ scale: 1 }}, {{ scale: 1.04, duration: {FULL_END}, ease: "none" }}, 0);
      tl.to(D, {{ scale: 1, duration: 0.45, ease: "power2.inOut" }}, {FULL_END});
      tl.fromTo(F, {{ x: 0, y: 0, scale: 1 }}, {{ x: {X_}, y: {Y_}, scale: {S_}, duration: 0.5, ease: "power3.inOut" }}, {FULL_END});
      tl.fromTo("#winclip", {{ clipPath: "inset(0px 0px 0px 0px round 0px)" }}, {{ clipPath: "inset({CUT}px 0px 0px 0px round {RAD}px)", duration: 0.5, ease: "power3.inOut" }}, {FULL_END});
      tl.to("#scrim", {{ opacity: 0, duration: 0.3 }}, {FULL_END});
      tl.to(["#winshadow", "#winborder"], {{ opacity: 1, duration: 0.15 }}, {FULL_END + 0.36});
      tl.to("#faceB", {{ opacity: 1, duration: 0.1 }}, {FULL_END + 0.46});'''
    if GO_FULL is not None:
        s += f'''
      tl.to(F, {{ x: 0, y: 0, scale: 1, duration: 0.5, ease: "power3.inOut" }}, {GO_FULL});
      tl.to("#winclip", {{ clipPath: "inset(0px 0px 0px 0px round 0px)", duration: 0.5, ease: "power3.inOut" }}, {GO_FULL});
      tl.to(["#winshadow", "#winborder"], {{ opacity: 0, duration: 0.2 }}, {GO_FULL});
      tl.to("#faceB", {{ opacity: 0, duration: 0.1 }}, {GO_FULL + 0.45});
      tl.to("#scrim", {{ opacity: 1, duration: 0.3 }}, {GO_FULL + 0.2});
      tl.fromTo(D, {{ scale: 1 }}, {{ scale: 1.03, duration: {round(TOTAL - GO_FULL - 0.5, 3)}, ease: "none", immediateRender: false }}, {GO_FULL + 0.5});'''
    return s


def index_html(TOTAL, css, content, overlay, js, sfx):
    return f'''<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>{BASE_CSS}{css}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-full data-width="1080" data-height="1920">
      <div id="stage" class="fill"></div>
      <div id="grid" class="fill"></div>

      <div id="faceA" class="facegrp"><div id="punchA" class="fill"><div id="driftA" class="fill">
        <div id="winshadow"></div>
        <div id="winclip" class="fill">
          <video id="face" class="clip" src="assets/face.mp4" data-start="0" data-duration="{TOTAL}" data-full data-track-index="0" muted playsinline></video>
        </div>
        <div id="winborder"></div>
      </div></div></div>

      <div id="content" class="fill" data-layout-allow-overlap>
{content}
      </div>

      <div id="faceB" class="facegrp"><div id="punchB" class="fill"><div id="driftB" class="fill">
        <div id="cutwrap" class="fill">
          <video id="facecut" class="clip" src="assets/face_cut.webm" data-start="0" data-media-start="0" data-duration="{TOTAL}" data-full data-track-index="20" muted playsinline></video>
        </div>
      </div></div></div>
      <div id="scrim" class="fill"></div>
{overlay}

      <div id="type-host" class="clip scene" data-composition-id="type" data-composition-src="compositions/type.html"
        data-start="0" data-duration="{TOTAL}" data-full data-track-index="1" data-track-kind="captions" style="z-index: 5"></div>

      <!-- Sound. Music off: add a trending IG track in-app. -->
      <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{TOTAL}" data-full data-track-index="6" data-volume="1"></audio>
{sfx}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      const F = ["#faceA", "#faceB"], D = ["#driftA", "#driftB"], P2 = ["#punchA", "#punchB"];
{js}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''


def type_html(groups, extra_js=""):
    gh = "\n".join(f'    <div id="{gid}" class="clip grp {cls}" data-start="{round(a, 3)}" data-duration="{round(b - a, 3)}">{body}</div>'
                   for gid, cls, a, b, body in groups)
    return f'''<template>
  <!-- house style v2 kinetic type. FULL face groups: bottom at y 1290. Window phase: header at the top (bottom y 408). -->
  <style>
    @font-face {{ font-family: "Instrument Serif"; font-style: italic; font-weight: 400; src: url("assets/fonts/InstrumentSerif-Italic.woff2") format("woff2"); }}
    #root {{ position: absolute; inset: 0; overflow: visible; background: transparent; }}
    .grp {{ position: absolute; left: 0; right: 0; top: 0; height: 1290px; display: flex; flex-direction: column; justify-content: flex-end;
      align-items: center; text-align: center; padding: 0 70px; color: #fff; }}
    .grp.top {{ height: 408px; }}
    .sm {{ font-family: "Inter", sans-serif; font-weight: 600; font-size: 64px; line-height: 1.12; letter-spacing: -0.01em;
      text-shadow: 0 2px 18px rgba(0,0,0,0.7), 0 1px 3px rgba(0,0,0,0.5); margin-bottom: 8px;
      display: flex; align-items: center; justify-content: center; gap: 0 14px; flex-wrap: wrap; }}
    .top .sm {{ font-size: 50px; margin-bottom: 2px; color: rgba(243,239,232,0.92); }}
    .sm .n {{ font-family: "SF Mono", Menlo, monospace; font-weight: 700; font-size: 30px; color: #0e0e0e; background: {CORAL}; padding: 4px 12px; border-radius: 10px; vertical-align: middle; }}
    .bg {{ font-family: "Instrument Serif", serif; font-style: italic; font-weight: 400; line-height: 0.92; letter-spacing: -0.02em;
      text-shadow: 0 4px 30px rgba(0,0,0,0.5), 0 2px 6px rgba(0,0,0,0.3); max-width: 980px; }}
    .top .bg {{ color: {CREAM}; }}
    .w {{ display: inline-block; }}
    .per {{ font-family: "Inter", sans-serif; font-style: normal; font-weight: 600; font-size: 0.26em; color: rgba(243,239,232,0.55); letter-spacing: 0; }}
    .arr {{ color: rgba(243,239,232,0.45); }}
    .acc {{ color: {CORAL} !important; }}
  </style>
  <div id="root" data-composition-id="type" data-width="1080" data-height="1920" data-layout-allow-overflow>
{gh}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const root = document.querySelector('[data-composition-id="type"]');
    root.querySelectorAll(".w[data-t]").forEach((el) => {{
      const t = parseFloat(el.dataset.t), big = el.closest(".bg");
      tl.fromTo(el, {{ opacity: 0, y: big ? 40 : 18, filter: "blur(12px)" }},
        {{ opacity: 1, y: 0, filter: "blur(0px)", duration: big ? 0.36 : 0.26, ease: "power3.out" }}, Math.max(0, t - 0.04));
    }});
    tl.fromTo("#g1-big", {{ scale: 1.05 }}, {{ scale: 1, duration: 1.3, ease: "power2.out" }}, 0);
    root.querySelectorAll(".grp").forEach((g) => {{
      if (g.id === "gLast") return;
      const e = parseFloat(g.dataset.start) + parseFloat(g.dataset.duration);
      tl.to(g, {{ opacity: 0, duration: 0.08, ease: "power2.in" }}, e - 0.08);
      tl.set(g, {{ opacity: 0 }}, e);
    }});{extra_js}
    window.__timelines["type"] = tl;
  </script>
</template>
'''


def write(P, html, type_h):
    open(os.path.join(P, "index.html"), "w").write(html)
    open(os.path.join(P, "compositions/type.html"), "w").write(type_h)

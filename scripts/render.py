#!/usr/bin/env python3
"""data/DATE.json → pages/DATE.html + index.html 재생성.

디자인은 이 스크립트가 고정한다(매번 동일). 콘텐츠만 매일 바뀐다.
2026 트렌드: 오버사이즈 타이포 / 극단적 여백 / 절제된 팔레트 / 날씨 기반 accent / 다크모드.
"""
import html
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(os.environ.get(
    "ONEUL_PROJECT", "/Users/tom.kim/personal/sunwoo-jamcoding"))
DATA = PROJECT / "data"
PAGES = PROJECT / "pages"
ASSETS = PROJECT / "assets"

WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]

# 대표 컨디션별 accent + 글리프. 절제된 단색.
CONDITION = {
    "clear": {"accent": "#D98A2B", "glyph": "○", "word": "맑음"},
    "cloud": {"accent": "#8C8073", "glyph": "◍", "word": "흐림"},
    "rain":  {"accent": "#4E7290", "glyph": "◐", "word": "비"},
    "snow":  {"accent": "#7AA0C2", "glyph": "❋", "word": "눈"},
    "hot":   {"accent": "#D85A38", "glyph": "●", "word": "더위"},
    "cold":  {"accent": "#5E86AE", "glyph": "◇", "word": "추위"},
}


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def kdate(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d, WEEKDAY[d.weekday()]


def temp(v):
    if v is None:
        return "–"
    return f"{v:g}°"


STYLE = """
:root{
  --bg:#F5F3EE; --ink:#191713; --muted:#7A756C; --line:#E1DDD3;
  --card:#FbFAF6; --accent:#D98A2B;
}
@media (prefers-color-scheme:dark){
  :root{ --bg:#111010; --ink:#EDEAE3; --muted:#8E887D; --line:#262320;
         --card:#191715; }
}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg); color:var(--ink);
  font-family:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,
    'Apple SD Gothic Neo','Segoe UI',Roboto,sans-serif;
  line-height:1.6; letter-spacing:-.01em;
  font-feature-settings:'ss01','cv01';
  -webkit-font-smoothing:antialiased;
  word-break:keep-all;  /* 한글은 어절 단위로만 줄바꿈 */
}
.wrap{max-width:720px;margin:0 auto;padding:0 24px}
a{color:inherit;text-decoration:none}

/* ── hero ── */
.hero{padding:16vh 0 7vh}
.kicker{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);display:flex;gap:.6em;flex-wrap:wrap;align-items:center}
.kicker .dot{color:var(--accent)}
.mood{font-size:clamp(2.6rem,8.5vw,5.2rem);font-weight:800;line-height:1.02;
  letter-spacing:-.045em;margin:.32em 0 .5em;text-wrap:balance}
.summary{font-size:1.15rem;color:var(--muted);max-width:34ch;text-wrap:pretty}

/* ── weather strip ── */
.weather{display:grid;grid-template-columns:repeat(4,1fr);
  border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.weather .cell{padding:22px 0;border-right:1px solid var(--line)}
.weather .cell:last-child{border-right:0}
.weather .lab{font-size:.72rem;letter-spacing:.06em;color:var(--muted);
  text-transform:uppercase}
.weather .val{font-size:1.5rem;font-weight:700;margin-top:6px;letter-spacing:-.02em}
.weather .val .glyph{color:var(--accent);margin-right:.15em}

/* ── recs ── */
.recs{padding:6vh 0 2vh}
.recs-h{font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);margin-bottom:8px}
.rec{display:grid;grid-template-columns:auto 1fr;gap:22px;
  padding:34px 0;border-top:1px solid var(--line)}
.rec .num{font-size:.95rem;font-weight:700;color:var(--accent);
  font-variant-numeric:tabular-nums;padding-top:.35em}
.rec .meta{font-size:.76rem;letter-spacing:.05em;color:var(--muted);
  text-transform:uppercase;display:flex;gap:.7em;flex-wrap:wrap}
.rec h2{font-size:clamp(1.5rem,4.5vw,2rem);font-weight:750;line-height:1.15;
  letter-spacing:-.03em;margin:.28em 0 .3em}
.rec .place{font-size:.98rem;color:var(--accent);font-weight:600;margin-bottom:.5em}
.rec .why{color:var(--muted);font-size:1.02rem;text-wrap:pretty}

/* ── tip ── */
.tip{margin:4vh 0;padding:26px 28px;background:var(--card);
  border:1px solid var(--line);border-radius:18px}
.tip .lab{font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;
  color:var(--accent);font-weight:700}
.tip p{margin-top:8px;font-size:1.05rem}

/* ── footer ── */
footer{padding:6vh 0 12vh;border-top:1px solid var(--line);
  display:flex;justify-content:space-between;align-items:center;
  font-size:.82rem;color:var(--muted);flex-wrap:wrap;gap:12px}
footer a{color:var(--accent);font-weight:600}

/* ── index ── */
.idx-hero{padding:15vh 0 6vh}
.idx-hero h1{font-size:clamp(3rem,11vw,6rem);font-weight:850;letter-spacing:-.05em;
  line-height:.98}
.idx-hero p{color:var(--muted);font-size:1.15rem;margin-top:1.1em}
.days{padding-bottom:14vh}
.day{display:grid;grid-template-columns:auto 1fr auto;gap:20px;align-items:baseline;
  padding:30px 0;border-top:1px solid var(--line);transition:padding-left .25s ease}
.day:hover{padding-left:10px}
.day .d{font-variant-numeric:tabular-nums;font-weight:750;font-size:1.15rem;
  letter-spacing:-.02em;min-width:5.5ch}
.day .d small{color:var(--muted);font-weight:500;margin-left:.3em}
.day .m{font-size:1.25rem;font-weight:650;letter-spacing:-.02em;text-wrap:balance}
.day .w{color:var(--accent);font-weight:700;white-space:nowrap;
  font-variant-numeric:tabular-nums}
.empty{padding:20vh 0;color:var(--muted);text-align:center}
"""

HEAD = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
<link rel="stylesheet" href="{css}">
<title>{title}</title>"""


def render_day(payload):
    date_str = payload["date"]
    d, wd = kdate(date_str)
    w = payload.get("weather", {})
    today = w.get("today", {})
    now = w.get("now", {})
    cond = CONDITION.get(today.get("condition", "clear"), CONDITION["clear"])
    accent = cond["accent"]

    kicker = (f'<span>{d.strftime("%Y.%m.%d")}</span>'
              f'<span class="dot">·</span><span>{wd}요일</span>'
              f'<span class="dot">·</span><span>{esc(w.get("location","분당 서현동"))}</span>')

    # 정적 페이지이므로 '지금'이 아니라 '업데이트 시각 기준'으로 고정 표기.
    gen = payload.get("generated_at", w.get("fetched_at", ""))
    upd_label = (gen.split(" ")[1] + " 기준") if " " in gen else "기온"
    now_temp = temp(now.get("temp"))
    cells = [
        (upd_label, f'<span class="glyph">{cond["glyph"]}</span>{now_temp}'),
        ("최고 / 최저", f'{temp(today.get("tmx"))}<span style="color:var(--muted)"> / {temp(today.get("tmn"))}</span>'),
        ("강수확률", f'{today.get("rain_prob_max") if today.get("rain_prob_max") is not None else "–"}%'),
        ("하늘", esc(today.get("sky_summary") or cond["word"])),
    ]
    weather_html = "".join(
        f'<div class="cell"><div class="lab">{lab}</div>'
        f'<div class="val">{val}</div></div>' for lab, val in cells)

    recs = payload.get("recommendations", [])
    rec_html = []
    for i, r in enumerate(recs, 1):
        io = "실내" if r.get("indoor") else "실외"
        meta = " · ".join(filter(None, [esc(r.get("time")), esc(r.get("tag")), io]))
        rec_html.append(
            f'<article class="rec"><div class="num">{i:02d}</div><div>'
            f'<div class="meta">{meta}</div>'
            f'<h2>{esc(r.get("title"))}</h2>'
            f'<div class="place">↳ {esc(r.get("place"))}</div>'
            f'<p class="why">{esc(r.get("why"))}</p></div></article>')

    tip = payload.get("tip")
    tip_html = (f'<div class="tip"><div class="lab">오늘의 팁</div>'
                f'<p>{esc(tip)}</p></div>') if tip else ""

    body = f"""<div class="wrap" style="--accent:{accent}">
<header class="hero">
  <div class="kicker">{kicker}</div>
  <h1 class="mood">{esc(payload.get("mood"))}</h1>
  <p class="summary">{esc(payload.get("summary"))}</p>
</header>
<section class="weather">{weather_html}</section>
<section class="recs">
  <div class="recs-h">오늘 뭐하지</div>
  {"".join(rec_html)}
</section>
{tip_html}
<footer>
  <span>{esc(gen)} · 기상청 단기예보 기반</span>
  <a href="../index.html">← 전체 보기</a>
</footer>
</div>"""
    head = HEAD.format(css="../assets/style.css",
                       title=f'{d.strftime("%m.%d")} {wd} · 오늘 뭐하지')
    return f"<!doctype html><html lang='ko'><head>{head}</head><body>{body}</body></html>"


def render_index(payloads):
    payloads.sort(key=lambda p: p["date"], reverse=True)
    rows = []
    for p in payloads:
        d, wd = kdate(p["date"])
        today = p.get("weather", {}).get("today", {})
        cond = CONDITION.get(today.get("condition", "clear"), CONDITION["clear"])
        rows.append(
            f'<a class="day" href="pages/{p["date"]}.html" style="--accent:{cond["accent"]}">'
            f'<div class="d">{d.strftime("%m.%d")}<small>{wd}</small></div>'
            f'<div class="m">{esc(p.get("mood"))}</div>'
            f'<div class="w">{cond["glyph"]} {temp(today.get("tmx"))}</div></a>')
    if not rows:
        body_rows = '<div class="empty">아직 큐레이션된 날이 없어요.</div>'
    else:
        body_rows = "".join(rows)
    head = HEAD.format(css="assets/style.css", title="오늘 뭐하지 · 분당 서현동")
    body = f"""<div class="wrap">
<header class="idx-hero">
  <h1>오늘<br>뭐하지</h1>
  <p>분당 서현동 · 매일 새로 큐레이션되는 하루</p>
</header>
<section class="days">{body_rows}</section>
</div>"""
    return f"<!doctype html><html lang='ko'><head>{head}</head><body>{body}</body></html>"


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    (ASSETS / "style.css").write_text(STYLE, encoding="utf-8")

    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        payload = json.loads((DATA / f"{date_str}.json").read_text("utf-8"))
        (PAGES / f"{date_str}.html").write_text(render_day(payload), encoding="utf-8")

    all_payloads = []
    for f in DATA.glob("*.json"):
        try:
            all_payloads.append(json.loads(f.read_text("utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    (PROJECT / "index.html").write_text(render_index(all_payloads), encoding="utf-8")
    print(f"rendered {len(all_payloads)} day(s) → {PROJECT/'index.html'}")


if __name__ == "__main__":
    main()

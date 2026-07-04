#!/usr/bin/env python3
"""기상청 날씨 fetch — 분당 서현동(nx=62, ny=123).

왜 두 API를 쓰나:
- 단기예보(getVilageFcst): 오늘 하루 최고/최저기온 + 3시간별 하늘/강수 → '오늘 뭐하지'는 하루 전체를 봐야 함.
- 초단기실황(getUltraSrtNcst): 지금 이 순간 기온/강수 → '지금' 감각.
사용자가 준 초단기예보(getUltraSrtFcst)는 +6시간만 커버해서 하루 큐레이션엔 부족하므로,
같은 서비스(VilageFcstInfoService_2.0)의 단기예보로 하루를 잡고 실황으로 현재를 보강한다.

stdout으로 정제된 JSON을 뱉는다. 콘텐츠 창작은 이 데이터를 받아 Claude가 한다.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path


def _service_key():
    """공공데이터포털 기상청 서비스키. 공개 레포에 키를 넣지 않으려고 밖으로 뺐다.
    우선순위: 환경변수 KMA_SERVICE_KEY → 프로젝트 루트의 .env(gitignore됨).
    data.go.kr에서 VilageFcstInfoService_2.0 활용신청 후 발급받은 키를 쓴다."""
    key = os.environ.get("KMA_SERVICE_KEY", "").strip()
    if key:
        return key
    root = Path(__file__).resolve().parent.parent  # scripts/ 의 부모 = 프로젝트 루트
    for base in (root, Path.cwd()):
        env = base / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("KMA_SERVICE_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


SERVICE_KEY = _service_key()
BASE = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
NX, NY = 62, 123  # 경기 성남시 분당구 서현동
LOCATION = "분당 서현동"

SKY = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기",
       "5": "빗방울", "6": "빗방울눈날림", "7": "눈날림"}


def _get(endpoint, params):
    q = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "XML",
        "nx": NX,
        "ny": NY,
        **params,
    }
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=15) as r:
        raw = r.read().decode("utf-8")
    root = ET.fromstring(raw)
    code = root.findtext(".//resultCode")
    if code != "00":
        return None
    items = []
    for it in root.findall(".//item"):
        items.append({c.tag: (c.text or "") for c in it})
    return items or None


def fetch_vilage(now):
    """단기예보: now 이전의 가장 최근 발표시각을 역순으로 시도."""
    slots = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
    # 발표 후 약 10분 뒤 제공. 안전하게 후보를 시간 역순으로 훑는다.
    candidates = []
    for back in range(0, 2):  # 오늘, 어제
        day = now - timedelta(days=back)
        for s in slots:
            slot_dt = day.replace(hour=int(s[:2]), minute=int(s[2:]),
                                  second=0, microsecond=0)
            if slot_dt <= now - timedelta(minutes=15):
                candidates.append((day.strftime("%Y%m%d"), s))
    seen = set()
    for base_date, base_time in candidates:
        if (base_date, base_time) in seen:
            continue
        seen.add((base_date, base_time))
        items = _get("getVilageFcst",
                     {"base_date": base_date, "base_time": base_time})
        if items:
            return items
    return None


def fetch_ncst(now):
    """초단기실황: 매시 정시 발표, 약 40분 뒤 제공."""
    for back in range(0, 4):
        t = now - timedelta(hours=back)
        base_date = t.strftime("%Y%m%d")
        base_time = t.strftime("%H") + "00"
        if t.replace(minute=0) > now - timedelta(minutes=40):
            continue
        items = _get("getUltraSrtNcst",
                     {"base_date": base_date, "base_time": base_time})
        if items:
            return items
    return None


def build(target_date, now):
    ymd = target_date.strftime("%Y%m%d")
    vilage = fetch_vilage(now) or []
    ncst = fetch_ncst(now) or []

    # --- 오늘 하루 타임라인 (단기예보에서 target_date만) ---
    by_time = {}
    tmn = tmx = None
    for it in vilage:
        if it.get("fcstDate") != ymd:
            continue
        cat, val, ft = it.get("category"), it.get("fcstValue"), it.get("fcstTime")
        if cat == "TMN":
            tmn = _num(val)
        elif cat == "TMX":
            tmx = _num(val)
        elif cat in ("TMP", "SKY", "PTY", "POP", "REH", "WSD", "PCP"):
            by_time.setdefault(ft, {})[cat] = val

    timeline = []
    for ft in sorted(by_time):
        d = by_time[ft]
        timeline.append({
            "time": ft,
            "temp": _num(d.get("TMP")),
            "sky": SKY.get(d.get("SKY", ""), ""),
            "pty": PTY.get(d.get("PTY", ""), ""),
            "pop": _num(d.get("POP")),
            "humidity": _num(d.get("REH")),
            "wind": _num(d.get("WSD")),
            "pcp": d.get("PCP", ""),
        })

    # TMN/TMX는 새벽 발표에만 담긴다. 오후에 돌리면 없으므로 남은 타임라인 기온으로 폴백.
    temps = [t["temp"] for t in timeline if t["temp"] is not None]
    if tmn is None and temps:
        tmn = min(temps)
    if tmx is None and temps:
        tmx = max(temps)

    pops = [t["pop"] for t in timeline if t["pop"] is not None]
    rain_slots = [t for t in timeline if t["pty"] and t["pty"] != "없음"]
    sky_counts = {}
    for t in timeline:
        if t["sky"]:
            sky_counts[t["sky"]] = sky_counts.get(t["sky"], 0) + 1
    sky_summary = max(sky_counts, key=sky_counts.get) if sky_counts else ""

    # --- 지금 실황 ---
    now_obs = {}
    NCAT = {"T1H": "temp", "RN1": "rain1h", "REH": "humidity",
            "WSD": "wind", "PTY": "pty"}
    obs_time = ""
    for it in ncst:
        cat = it.get("category")
        obs_time = it.get("baseTime", obs_time)
        if cat in NCAT:
            v = it.get("obsrValue")
            if cat == "PTY":
                now_obs["pty"] = PTY.get(v, "없음")
            elif cat == "RN1":
                now_obs["rain1h"] = v  # mm, "강수없음" or number
            else:
                now_obs[NCAT[cat]] = _num(v)
    now_obs["observed_at"] = obs_time

    # --- 대표 컨디션 (렌더 accent 결정에 쓰임) ---
    if rain_slots:
        condition = "snow" if any("눈" in s["pty"] for s in rain_slots) else "rain"
    elif tmx is not None and tmx >= 30:
        condition = "hot"
    elif tmn is not None and tmn <= 0:
        condition = "cold"
    elif sky_summary == "흐림":
        condition = "cloud"
    else:
        condition = "clear"

    return {
        "location": LOCATION,
        "nx": NX, "ny": NY,
        "date": target_date.strftime("%Y-%m-%d"),
        "fetched_at": now.strftime("%Y-%m-%d %H:%M"),
        "now": now_obs,
        "today": {
            "tmn": tmn, "tmx": tmx,
            "sky_summary": sky_summary,
            "rain_prob_max": max(pops) if pops else None,
            "will_rain": bool(rain_slots),
            "condition": condition,
            "timeline": timeline,
        },
        "ok": bool(timeline or now_obs),
    }


def _num(v):
    if v in (None, "", "강수없음", "-", "null"):
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except ValueError:
        return None


if __name__ == "__main__":
    if not SERVICE_KEY:
        sys.stderr.write(
            "환경변수 KMA_SERVICE_KEY가 없습니다. "
            "data.go.kr에서 기상청 단기예보 키를 발급받아 설정하세요.\n"
            "예: KMA_SERVICE_KEY='발급받은키' python3 fetch_weather.py 2026-07-04\n")
        sys.exit(1)
    now = datetime.now()
    if len(sys.argv) > 1:
        target = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        # 과거/오늘 날짜여도 now 기준으로 발표시각을 잡되, 대상일 데이터만 추출
        target = target.replace(hour=now.hour, minute=now.minute)
    else:
        target = now
    print(json.dumps(build(target, now), ensure_ascii=False, indent=2))

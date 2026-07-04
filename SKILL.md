---
name: oneul-mwohaji
description: 기상청 날씨를 받아 분당 서현동의 '오늘 뭐하지'를 매일 새로 큐레이션하고 로컬 HTML 사이트로 렌더링한다. "/oneul-mwohaji" 또는 "오늘 뭐하지"로 호출.
disable-model-invocation: true
allowed-tools: Bash(python3*) Bash(open*) Bash(ls*) Bash(test*) Read Write
---

# oneul-mwohaji — 오늘 뭐하지 (분당 서현동)

기상청 단기예보로 **오늘 하루 날씨**를 받아, 그 날씨와 **서현동 로컬 지식**을 엮어
매일 다른 큐레이션을 만들고, 모던·극심플 HTML 사이트로 남긴다.

**핵심 원칙**: 날씨→활동 기계 매핑(핫바지) 금지. 오늘의 날씨 흐름을 읽고,
서현동에서 실제로 갈 만한 곳을 이유와 함께 고른다. 매일 결과가 달라야 한다.

> 이 스킬은 `/Users/tom.kim/personal/sunwoo-jamcoding` 레포 그 자체다.
> `~/.claude/skills/oneul-mwohaji`는 이 레포로의 심링크. 스크립트·사이트가 한 곳에 있다.

## 사전 준비 (최초 1회)

기상청 서비스키가 필요하다. 레포 루트에 `.env`(gitignore됨)를 만들고:
```
KMA_SERVICE_KEY=data.go.kr에서_발급받은_키
```
`fetch_weather.py`가 환경변수 → `.env` 순으로 키를 읽는다. 공개 레포엔 키가 안 들어간다.

## 경로

- 루트(레포): `/Users/tom.kim/personal/sunwoo-jamcoding/`
  - `SKILL.md` — 이 파일
  - `scripts/fetch_weather.py`, `scripts/render.py` — 실행 로직
  - `index.html` — 날짜별 목록 (최신순)
  - `pages/YYYY-MM-DD.html` — 하루 페이지
  - `data/YYYY-MM-DD.json` — 그날 원본(날씨+콘텐츠). 재렌더/기록용.
  - `assets/style.css` — 공유 디자인 (render.py가 매번 다시 씀)
  - `.env` — 서비스키 (gitignore)

## 실행 순서

### 0. 오늘 날짜 확인 + 멱등성 체크
오늘 날짜를 `YYYY-MM-DD`로 잡는다(환경의 currentDate 사용).

```bash
DATE=<오늘>
test -f /Users/tom.kim/personal/sunwoo-jamcoding/pages/$DATE.html && echo EXISTS || echo NEW
```
`EXISTS`면 **여기서 멈춘다**. "오늘 큐레이션은 이미 있어요"라고 알리고,
`open /Users/tom.kim/personal/sunwoo-jamcoding/pages/$DATE.html` 로 열어준다.
(다시 만들라는 명시 요청이 있을 때만 아래를 진행)

### 1. 날씨 가져오기
```bash
python3 /Users/tom.kim/personal/sunwoo-jamcoding/scripts/fetch_weather.py $DATE
```
stdout의 JSON을 읽는다. `today.condition`(clear/cloud/rain/snow/hot/cold),
`today.tmx/tmn`, `today.rain_prob_max`, `today.timeline`(3시간별), `now`(현재 실황)를 본다.
`ok:false`거나 timeline이 비면 Tom에게 알리고 중단(최근 3일만 제공되는 API 특성).

### 2. 오늘 콘텐츠 창작 (이 스킬의 본체)
날씨 흐름을 **하루의 이야기**로 해석한다. 예: "오후 소나기 → 저녁 갬"이면
낮은 실내, 저녁은 야외. "종일 맑고 더움"이면 이른 아침·해질녘 야외 + 한낮 실내.

아래 스키마로 콘텐츠를 만든다. 문체는 `~요`체, 친근하되 담백하게(과장·이모지 금지).

```json
{
  "mood": "오늘을 한 줄로. 오버사이즈 헤드라인에 박히는 문장. (예: '소나기 지나간 저녁, 걷기 좋은 하루')",
  "summary": "날씨를 사람 말로 2~3문장. 숫자(기온/강수확률/시간대)를 녹여서.",
  "recommendations": [
    {
      "time": "낮 | 오후 3–5시 | 저녁 7시 | 밤 | 하루종일 등 구체 시간대",
      "title": "활동 제목 (짧고 감각적으로)",
      "place": "서현동/분당 실제 장소 + 접근 힌트",
      "why": "왜 하필 오늘 이걸? 날씨 수치와 연결해 2~3문장. 이게 큐레이션의 핵심.",
      "indoor": true,
      "tag": "활동 종류. 산책 | 카페 | 문화 | 맛집 | 쇼핑 | 액티비티 중 하나. (실내/실외는 indoor로 자동 표기되니 tag에 넣지 말 것)"
    }
  ],
  "tip": "오늘의 실용 팁 한 줄 (우산/자외선/미세먼지/일교차 등 날씨 근거)"
}
```

**서현동 로컬 레퍼런스** (활용하되 이걸로만 채우지 말 것 — 상황에 맞게 취사):
- 실내/쇼핑/식사: AK플라자 분당점(서현역 직결), 이마트 분당점, 서현 지하상가
- 카페/거리: 서현역 로데오 카페거리, 정자동 카페거리(한 정거장)
- 공원/산책: 분당중앙공원(서현역 도보 10분, 호수), 율동공원(책테마파크·호수), 낙생대공원
- 액티비티/운동: 탄천 산책로·자전거길, 성남종합운동장
- 문화: 서현 문화의집, CGV/롯데시네마 분당, 성남아트센터(야탑)
- 맛집 밀집: 서현 로데오, 정자동 먹자골목

추천은 **3~5개**. 시간대가 겹치지 않게, 실내/실외를 날씨에 맞게 배분한다.

만든 콘텐츠 JSON은 **반드시 `data/_content.json`으로 Write** 해둔다(3단계 병합이 이 파일을 읽는다).

### 3. 저장 + 렌더
콘텐츠 JSON을 임시 파일로 쓰고, 날씨와 병합해 `data/$DATE.json`을 만든 뒤 렌더한다.

```bash
cd /Users/tom.kim/personal/sunwoo-jamcoding
mkdir -p data pages   # 최초 실행(빈 프로젝트) 대비. bash 리다이렉트는 폴더를 안 만든다.
# (2)에서 콘텐츠를 반드시 data/_content.json 으로 Write 해둔 상태여야 한다
python3 scripts/fetch_weather.py $DATE > data/_weather.json
python3 - "$DATE" <<'PY'
import json, sys
from datetime import datetime
date = sys.argv[1]
weather = json.load(open("data/_weather.json"))
content = json.load(open("data/_content.json"))
merged = {"date": date,
          "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
          "weather": weather, **content}
json.dump(merged, open(f"data/{date}.json", "w"), ensure_ascii=False, indent=2)
PY
rm -f data/_weather.json data/_content.json
python3 scripts/render.py $DATE
open pages/$DATE.html
```

### 4. 마무리 보고
mood 한 줄과 추천 개수를 Tom에게 짧게 전하고, 열린 페이지를 안내한다.

## 디자인 (render.py가 고정 — 손대지 말 것)
2026 트렌드: 오버사이즈 타이포 / 극단적 여백 / 절제된 팔레트 / 날씨 기반 accent /
다크모드 / Pretendard. 콘텐츠만 매일 바뀌고 디자인은 일관되게 유지한다.

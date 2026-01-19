# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

Meta 광고 라이브러리에서 **일반 상업 광고**를 자동 수집하여 웹 UI로 탐색하고 관리하는 도구.

## 기술 스택

- Python 3.11+ (백엔드 수집)
- `playwright` (웹 스크래핑)
- `requests` (이미지 다운로드)
- Next.js 14 (웹 UI)

## 프로젝트 구조

```
src/
  config.py             # 환경 설정 로드
  01_collect_ads.py     # Playwright로 광고 수집 (웹 스크래핑)
  02_fetch_creatives.py # 이미지 다운로드
  07_run_weekly.py      # 파이프라인 orchestration
  08_scheduler.py       # 자동 스케줄링
  collect_ads_api.py    # 호환성 래퍼

webapp-next/            # Next.js 웹 UI
  src/app/
    page.tsx            # 메인 페이지
    api/                # API 라우트
      ads/              # 광고 조회
      keywords/         # 키워드 관리
      highlights/       # 즐겨찾기
      collect/          # 수집 트리거

data/
  raw/                  # 수집된 광고 JSON
  images/               # 광고 이미지
  keywords.json         # 등록된 키워드
  highlights.json       # 즐겨찾기 데이터
```

## 실행 방법

### Python 수집 스크립트

```bash
# 환경 설정
python -m venv venv
pip install -r requirements.txt
playwright install chromium

# 광고 수집
python -m src.07_run_weekly --query "ai course" --limit 50

# 브라우저 표시 모드 (디버깅용)
python -m src.01_collect_ads --query "ai course" --limit 10 --no-headless
```

### 웹 UI

```bash
cd webapp-next
npm install
npm run dev
```

## 환경 변수 (.env)

- `COUNTRY`: 국가 코드 (예: KR)
- `QUERY`: 검색 키워드

## 아키텍처 결정사항

- **Playwright 웹 스크래핑**: 일반 상업 광고 수집 (Meta API는 정치/사회 이슈 광고만 지원)
- **JSON 기반 로컬 저장소**: 웹 UI는 `data/` 폴더의 JSON 파일들로 데이터 관리
- 수집 데이터: 광고주명, 광고 문구, 이미지 URL, 비디오 URL

## 코딩 규칙

- 응답, 주석, 커밋 메시지, 문서화: 한국어
- 변수명, 함수명: 영어 (코드 표준)

---

# GPTers AI Toolkit 연동

## 스킬 자동 활성화 (필수)

새로운 유형의 작업 시작 시 **반드시** 관련 스킬을 검색하세요:

1. 작업 키워드로 검색
2. 결과가 있으면 get_plugin_content로 내용 확인
3. 스킬 지침에 따라 작업 수행

```
gpters-ai-toolkit search_plugins("키워드")
gpters-ai-toolkit get_plugin_content("스킬ID")
```

**이 규칙은 SKIP 불가.**

### 검색 키워드 예시

| 작업 유형 | 검색어 |
|----------|--------|
| 개발 로그, 사례글 작성 | devlog, writing |
| 코드 리팩토링 | refactor |
| PDF 변환 | pdf |
| Airtable 연동 | airtable |
| Hook 설정 | hooks |
| 배포/도메인 | deploy, domain |
| DB 접근 | database, postgresql |

## 플러그인 배포

만든 스킬을 팀과 공유하려면:

```
gpters-ai-toolkit deploy_skill(type="skill", name="스킬명", content="...")
```

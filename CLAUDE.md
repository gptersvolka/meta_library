# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

Meta 광고 라이브러리에서 **일반 상업 광고**를 자동 수집하여 구글 시트에 정리하고, OCR로 텍스트를 추출한 뒤 광고 소재 아이디어를 생성하는 주간 자동화 파이프라인.

## 기술 스택

- Python 3.11+
- `playwright` (웹 스크래핑 - 메인 수집 방식)
- `requests` (이미지 다운로드)
- `Pillow`, `pytesseract` (OCR)
- `gspread` 또는 `google-api-python-client` (Google Sheets/Drive)

## 프로젝트 구조

```
src/
  config.py             # 환경 설정 로드
  01_collect_ads.py     # Playwright로 광고 수집 (웹 스크래핑)
  02_fetch_creatives.py # 이미지/비디오 다운로드
  03_upload_drive.py    # Drive 업로드
  04_write_sheets.py    # Sheets 기록
  05_ocr.py             # OCR 처리
  06_generate_ideas.py  # 아이디어 생성
  07_run_weekly.py      # 전체 파이프라인 orchestration
  collect_ads_api.py    # 호환성 래퍼 (파이프라인 연동용)
data/
  raw/     # 수집된 광고 JSON
  images/  # 광고 이미지
  ocr/     # OCR 결과
```

## 실행 방법

```bash
# 환경 설정
python -m venv venv
pip install -r requirements.txt
playwright install chromium  # 브라우저 설치

# 개별 스크립트 실행 예시
python -m src.01_collect_ads --query "ai course" --country KR --limit 50

# 브라우저 표시 모드 (디버깅용)
python -m src.01_collect_ads --query "ai course" --limit 10 --no-headless

# 전체 파이프라인 실행
python -m src.07_run_weekly --query "ai course" --limit 50
```

## 환경 변수 (.env)

- `GOOGLE_APPLICATION_CREDENTIALS`: 서비스 계정 JSON 경로
- `SHEET_ID`: 구글 시트 ID
- `DRIVE_FOLDER_ID`: Drive 폴더 ID
- `COUNTRY`: 국가 코드 (예: KR)
- `QUERY`: 검색 키워드

## 아키텍처 결정사항

- **Playwright 웹 스크래핑**: 일반 상업 광고 수집 (Meta API는 정치/사회 이슈 광고만 지원)
- 수집 데이터: 광고주명, 광고 문구, 이미지 URL, 비디오 URL
- 시트에 이미지는 `=IMAGE()` 수식으로 삽입 (AddImageRequest 대신)
- 각 스크립트는 CLI 인자로 단독 실행 가능하게 구현

## 코딩 규칙

- 응답, 주석, 커밋 메시지, 문서화: 한국어
- 변수명, 함수명: 영어 (코드 표준)

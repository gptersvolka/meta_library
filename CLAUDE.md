# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

Meta 광고 라이브러리에서 레퍼런스 광고를 자동 수집하여 구글 시트에 정리하고, OCR로 텍스트를 추출한 뒤 광고 소재 아이디어를 생성하는 주간 자동화 파이프라인.

## 기술 스택

- Python 3.11+
- `requests` (API 호출), `playwright` (Fallback 캡처)
- `Pillow`, `pytesseract` (OCR)
- `gspread` 또는 `google-api-python-client` (Google Sheets/Drive)

## 프로젝트 구조

```
src/
  00_config.py          # 환경 설정 로드
  01_collect_ads_api.py # Ads Library API로 광고 수집
  02_fetch_creatives.py # 이미지 다운로드/캡처
  03_upload_drive.py    # Drive 업로드
  04_write_sheets.py    # Sheets 기록
  05_ocr.py             # OCR 처리
  06_generate_ideas.py  # 아이디어 생성
  07_run_weekly.py      # 전체 파이프라인 orchestration
data/
  raw/     # API 응답 JSON
  images/  # 광고 이미지
  ocr/     # OCR 결과
```

## 실행 방법

```bash
# 환경 설정
python -m venv venv
pip install -r requirements.txt
playwright install  # Fallback용

# 개별 스크립트 실행 예시
python src/01_collect_ads_api.py --query "ai course" --country KR --limit 50

# 전체 파이프라인 실행
python src/07_run_weekly.py
```

## 환경 변수 (.env)

- `META_ACCESS_TOKEN`: Meta API 토큰
- `GOOGLE_APPLICATION_CREDENTIALS`: 서비스 계정 JSON 경로
- `SHEET_ID`: 구글 시트 ID
- `DRIVE_FOLDER_ID`: Drive 폴더 ID
- `COUNTRY`: 국가 코드 (예: KR)
- `QUERY`: 검색 키워드

## 아키텍처 결정사항

- **1차: Meta Ads Library API**, Fallback: Playwright 웹 캡처
- 시트에 이미지는 `=IMAGE()` 수식으로 삽입 (AddImageRequest 대신)
- 각 스크립트는 CLI 인자로 단독 실행 가능하게 구현

## 코딩 규칙

- 응답, 주석, 커밋 메시지, 문서화: 한국어
- 변수명, 함수명: 영어 (코드 표준)

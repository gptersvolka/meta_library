"""
Meta 광고 라이브러리 수집 파이프라인

각 모듈 실행 순서:
1. 01_collect_ads_api.py - 광고 수집
2. 02_fetch_creatives.py - 이미지 수집
3. 03_upload_drive.py - Drive 업로드
4. 04_write_sheets.py - Sheets 기록
5. 05_ocr.py - OCR 처리
6. 06_generate_ideas.py - 아이디어 생성
7. 07_run_weekly.py - 전체 파이프라인
"""

from src.config import (
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DIR,
    IMAGES_DIR,
    OCR_DIR,
    LOGS_DIR,
    COUNTRY,
    QUERY,
    ensure_dirs,
)

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DIR",
    "IMAGES_DIR",
    "OCR_DIR",
    "LOGS_DIR",
    "COUNTRY",
    "QUERY",
    "ensure_dirs",
]

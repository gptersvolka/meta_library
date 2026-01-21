"""
Meta 광고 라이브러리 수집 파이프라인 (현행 모듈 구성)

1) 01_collect_ads.py       - Playwright로 광고 메타데이터 수집 (raw JSON 생성)
2) 02_fetch_creatives.py   - raw JSON에서 이미지 다운로드 (중복 해시 체크)
3) 03_upload_images.py     - 수집 이미지 imgbb 업로드 및 영구 URL 기록
4) 07_run_weekly.py        - 1,3단계를 묶어 실행하고 Supabase에 upsert
5) 08_scheduler.py         - 키워드 스케줄 실행/관리 CLI
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

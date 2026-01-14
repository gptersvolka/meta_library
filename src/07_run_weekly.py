"""
주간 파이프라인 실행 모듈
전체 수집-다운로드-업로드-기록 파이프라인을 orchestration (Playwright 스크래핑 방식)
"""

import asyncio
import importlib
from datetime import datetime
from pathlib import Path

import click
from loguru import logger

from src.config import (
    QUERY,
    COUNTRY,
    RAW_DIR,
    get_sheet_id,
    ensure_dirs
)


def run_full_pipeline(
    query: str,
    country: str,
    limit: int,
    headless: bool = True,
    image_only: bool = False,
    skip_download: bool = False,
    skip_upload: bool = False,
    skip_sheets: bool = False
):
    """
    전체 파이프라인 실행 (Playwright 스크래핑 방식)

    Steps:
    1. Playwright로 Meta Ads Library에서 광고 수집
    2. 이미지 다운로드 (로컬 저장)
    3. Google Drive 업로드 (영구 보관용)
    4. Google Sheets에 키워드별 탭으로 기록 (Drive URL, OCR 텍스트 포함)
    """
    logger.info("=" * 50)
    logger.info(f"주간 파이프라인 시작: {datetime.now().isoformat()}")
    logger.info(f"검색 조건 - 키워드: {query}, 국가: {country}, 최대: {limit}개")
    logger.info("=" * 50)

    ensure_dirs()

    # Step 1: Playwright로 광고 수집
    logger.info("\n[Step 1/4] 광고 수집 시작 (Playwright 스크래핑)")
    collect_ads_module = importlib.import_module("src.01_collect_ads")
    collect_ads_playwright = collect_ads_module.collect_ads_playwright
    save_raw_data = collect_ads_module.save_raw_data

    ads = asyncio.run(collect_ads_playwright(
        query=query,
        country=country,
        limit=limit,
        headless=headless,
        image_only=image_only
    ))

    if not ads:
        logger.error("수집된 광고가 없습니다. 파이프라인 중단")
        return False

    raw_file = save_raw_data(ads, query)
    logger.info(f"[Step 1/4] 완료 - {len(ads)}개 광고 수집, 저장: {raw_file}")

    # Step 2: 이미지 다운로드
    fetch_results = []
    if not skip_download:
        logger.info("\n[Step 2/4] 이미지 다운로드 시작")
        fetch_module = importlib.import_module("src.02_fetch_creatives")
        fetch_creatives_from_raw = fetch_module.fetch_creatives_from_raw

        fetch_results = fetch_creatives_from_raw(raw_file)
        success_count = sum(1 for r in fetch_results if r["status"] in ["success", "exists"])
        logger.info(f"[Step 2/4] 완료 - {success_count}/{len(fetch_results)}개 이미지 다운로드")
    else:
        logger.info("\n[Step 2/4] 이미지 다운로드 건너뜀")

    # Step 3: Drive 업로드 (키워드 > 날짜 폴더 구조)
    upload_results = []
    if not skip_upload and fetch_results:
        logger.info("\n[Step 3/4] Drive 업로드 시작")
        upload_module = importlib.import_module("src.03_upload_drive")
        upload_all_images = upload_module.upload_all_images

        # 날짜 문자열 생성 (YYMMDD 형식)
        date_str = datetime.now().strftime("%y%m%d")

        upload_results = upload_all_images(
            fetch_results=fetch_results,
            query=query,
            date_str=date_str
        )
        success_count = sum(1 for r in upload_results if r["status"] == "success")
        logger.info(f"[Step 3/4] 완료 - {success_count}/{len(upload_results)}개 업로드")
    else:
        logger.info("\n[Step 3/4] Drive 업로드 건너뜀")

    # Step 4: Sheets 기록 (키워드별 탭, Drive URL 사용, OCR 포함)
    if not skip_sheets:
        logger.info("\n[Step 4/4] Sheets 기록 시작 (키워드별 탭)")
        sheets_module = importlib.import_module("src.04_write_sheets")
        get_sheets_client = sheets_module.get_sheets_client
        write_ads_by_keyword = sheets_module.write_ads_by_keyword

        client = get_sheets_client()
        spreadsheet = client.open_by_key(get_sheet_id())
        write_ads_by_keyword(spreadsheet, raw_file, upload_results=upload_results)
        logger.info("[Step 4/4] 완료")
    else:
        logger.info("\n[Step 4/4] Sheets 기록 건너뜀")

    logger.info("\n" + "=" * 50)
    logger.info(f"주간 파이프라인 완료: {datetime.now().isoformat()}")
    logger.info("=" * 50)

    return True


@click.command()
@click.option("--query", "-q", default=QUERY, help="검색 키워드")
@click.option("--country", "-c", default=COUNTRY, help="국가 코드")
@click.option("--limit", "-l", default=50, help="최대 수집 개수")
@click.option("--headless/--no-headless", default=True, help="헤드리스 모드 (기본: True)")
@click.option("--image-only", "-i", is_flag=True, help="이미지 광고만 수집 (비디오 제외)")
@click.option("--skip-download", is_flag=True, help="이미지 다운로드 건너뛰기")
@click.option("--skip-upload", is_flag=True, help="Drive 업로드 건너뛰기")
@click.option("--skip-sheets", is_flag=True, help="Sheets 기록 건너뛰기")
def main(
    query: str,
    country: str,
    limit: int,
    headless: bool,
    image_only: bool,
    skip_download: bool,
    skip_upload: bool,
    skip_sheets: bool
):
    """주간 광고 수집 파이프라인을 실행합니다 (Playwright 스크래핑 방식)."""
    if not query:
        logger.error("검색 키워드가 필요합니다. --query 옵션을 사용하세요.")
        return

    run_full_pipeline(
        query=query,
        country=country,
        limit=limit,
        headless=headless,
        image_only=image_only,
        skip_download=skip_download,
        skip_upload=skip_upload,
        skip_sheets=skip_sheets
    )


if __name__ == "__main__":
    main()

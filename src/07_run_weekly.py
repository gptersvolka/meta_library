"""
주간 파이프라인 실행 모듈
전체 수집-처리-기록-생성 파이프라인을 orchestration
"""

import json
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
    skip_capture: bool = False,
    skip_upload: bool = False,
    skip_sheets: bool = False,
    skip_ocr: bool = False,
    skip_ideas: bool = False
):
    """
    전체 파이프라인 실행

    Steps:
    1. Meta Ads Library API로 광고 수집
    2. 크리에이티브(이미지) 다운로드/캡처
    3. Google Drive 업로드
    4. Google Sheets 기록
    5. OCR 처리
    6. 아이디어 생성
    """
    logger.info("=" * 50)
    logger.info(f"주간 파이프라인 시작: {datetime.now().isoformat()}")
    logger.info(f"검색 조건 - 키워드: {query}, 국가: {country}, 최대: {limit}개")
    logger.info("=" * 50)

    ensure_dirs()

    # Step 1: 광고 수집
    logger.info("\n[Step 1/6] 광고 수집 시작")
    from src.collect_ads_api import collect_ads, save_raw_data

    ads = collect_ads(query=query, country=country, limit=limit)
    if not ads:
        logger.error("수집된 광고가 없습니다. 파이프라인 중단")
        return False

    raw_file = save_raw_data(ads, query)
    logger.info(f"[Step 1/6] 완료 - {len(ads)}개 광고 수집")

    # Step 2: 크리에이티브 수집
    upload_results = []
    if not skip_capture:
        logger.info("\n[Step 2/6] 크리에이티브 수집 시작")
        from src.fetch_creatives import fetch_creatives_from_raw

        fetch_results = fetch_creatives_from_raw(raw_file)
        success_count = sum(1 for r in fetch_results if r["status"] == "success")
        logger.info(f"[Step 2/6] 완료 - {success_count}/{len(fetch_results)}개 이미지 수집")
    else:
        logger.info("\n[Step 2/6] 크리에이티브 수집 건너뜀")

    # Step 3: Drive 업로드
    if not skip_upload:
        logger.info("\n[Step 3/6] Drive 업로드 시작")
        from src.upload_drive import upload_all_images

        upload_results = upload_all_images()
        success_count = sum(1 for r in upload_results if r["status"] == "success")
        logger.info(f"[Step 3/6] 완료 - {success_count}/{len(upload_results)}개 업로드")
    else:
        logger.info("\n[Step 3/6] Drive 업로드 건너뜀")

    # Step 4: Sheets 기록
    if not skip_sheets:
        logger.info("\n[Step 4/6] Sheets 기록 시작")
        from src.write_sheets import get_sheets_client, write_ads_raw
        import gspread

        client = get_sheets_client()
        spreadsheet = client.open_by_key(get_sheet_id())
        write_ads_raw(spreadsheet, raw_file, upload_results)
        logger.info("[Step 4/6] 완료")
    else:
        logger.info("\n[Step 4/6] Sheets 기록 건너뜀")

    # Step 5: OCR 처리
    ocr_results = []
    if not skip_ocr:
        logger.info("\n[Step 5/6] OCR 처리 시작")
        from src.ocr import process_all_images

        ocr_results = process_all_images()
        logger.info(f"[Step 5/6] 완료 - {len(ocr_results)}개 이미지 처리")

        # OCR 결과 Sheets에 기록
        if not skip_sheets and ocr_results:
            from src.write_sheets import write_ocr_text, get_sheets_client
            client = get_sheets_client()
            spreadsheet = client.open_by_key(get_sheet_id())
            write_ocr_text(spreadsheet, ocr_results)
    else:
        logger.info("\n[Step 5/6] OCR 처리 건너뜀")

    # Step 6: 아이디어 생성
    if not skip_ideas:
        logger.info("\n[Step 6/6] 아이디어 생성 시작")
        from src.generate_ideas import generate_all_ideas

        ideas = generate_all_ideas()
        logger.info(f"[Step 6/6] 완료 - {len(ideas)}개 아이디어 생성")

        # 아이디어 Sheets에 기록
        if not skip_sheets and ideas:
            from src.write_sheets import write_ideas, get_sheets_client
            client = get_sheets_client()
            spreadsheet = client.open_by_key(get_sheet_id())
            write_ideas(spreadsheet, ideas)
    else:
        logger.info("\n[Step 6/6] 아이디어 생성 건너뜀")

    logger.info("\n" + "=" * 50)
    logger.info(f"주간 파이프라인 완료: {datetime.now().isoformat()}")
    logger.info("=" * 50)

    return True


@click.command()
@click.option("--query", "-q", default=QUERY, help="검색 키워드")
@click.option("--country", "-c", default=COUNTRY, help="국가 코드")
@click.option("--limit", "-l", default=50, help="최대 수집 개수")
@click.option("--skip-capture", is_flag=True, help="크리에이티브 수집 건너뛰기")
@click.option("--skip-upload", is_flag=True, help="Drive 업로드 건너뛰기")
@click.option("--skip-sheets", is_flag=True, help="Sheets 기록 건너뛰기")
@click.option("--skip-ocr", is_flag=True, help="OCR 처리 건너뛰기")
@click.option("--skip-ideas", is_flag=True, help="아이디어 생성 건너뛰기")
def main(
    query: str,
    country: str,
    limit: int,
    skip_capture: bool,
    skip_upload: bool,
    skip_sheets: bool,
    skip_ocr: bool,
    skip_ideas: bool
):
    """주간 광고 수집 파이프라인을 실행합니다."""
    if not query:
        logger.error("검색 키워드가 필요합니다. --query 옵션을 사용하세요.")
        return

    run_full_pipeline(
        query=query,
        country=country,
        limit=limit,
        skip_capture=skip_capture,
        skip_upload=skip_upload,
        skip_sheets=skip_sheets,
        skip_ocr=skip_ocr,
        skip_ideas=skip_ideas
    )


if __name__ == "__main__":
    main()

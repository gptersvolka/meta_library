"""
주간 파이프라인 실행 모듈
광고 수집-이미지 업로드 파이프라인을 orchestration (Playwright 스크래핑 방식)
"""

import asyncio
import importlib
import os
from datetime import datetime

import click
from loguru import logger

from src.config import (
    QUERY,
    COUNTRY,
    ensure_dirs,
    get_env
)


def run_full_pipeline(
    query: str,
    country: str,
    limit: int,
    headless: bool = True,
    image_only: bool = False,
    skip_upload: bool = False
):
    """
    파이프라인 실행 (Playwright 스크래핑 방식)

    Steps:
    1. Playwright로 Meta Ads Library에서 광고 수집
    2. 이미지를 imgbb에 업로드 (영구 보관)
    """
    logger.info("=" * 50)
    logger.info(f"파이프라인 시작: {datetime.now().isoformat()}")
    logger.info(f"검색 조건 - 키워드: {query}, 국가: {country}, 최대: {limit}개")
    logger.info("=" * 50)

    ensure_dirs()

    # Step 1: Playwright로 광고 수집
    logger.info("\n[Step 1/2] 광고 수집 시작 (Playwright 스크래핑)")
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
    logger.info(f"[Step 1/2] 완료 - {len(ads)}개 광고 수집, 저장: {raw_file}")

    # Step 2: imgbb에 이미지 업로드
    if not skip_upload:
        imgbb_api_key = os.getenv("IMGBB_API_KEY")

        if imgbb_api_key:
            logger.info("\n[Step 2/2] imgbb 이미지 업로드 시작")
            upload_module = importlib.import_module("src.03_upload_images")
            process_raw_file = upload_module.process_raw_file_with_imgbb

            result = process_raw_file(raw_file)
            logger.info(f"[Step 2/2] 완료 - {result['uploaded']}개 업로드, {result['skipped']}개 건너뜀")
        else:
            logger.warning("\n[Step 2/2] IMGBB_API_KEY 미설정 - 이미지 업로드 건너뜀")
            logger.warning("imgbb를 사용하려면 .env에 IMGBB_API_KEY를 설정하세요.")
    else:
        logger.info("\n[Step 2/2] 이미지 업로드 건너뜀")

    logger.info("\n" + "=" * 50)
    logger.info(f"파이프라인 완료: {datetime.now().isoformat()}")
    logger.info("=" * 50)

    return raw_file


@click.command()
@click.option("--query", "-q", default=QUERY, help="검색 키워드")
@click.option("--country", "-c", default=COUNTRY, help="국가 코드")
@click.option("--limit", "-l", default=50, help="최대 수집 개수")
@click.option("--headless/--no-headless", default=True, help="헤드리스 모드 (기본: True)")
@click.option("--image-only", "-i", is_flag=True, help="이미지 광고만 수집 (비디오 제외)")
@click.option("--skip-upload", is_flag=True, help="이미지 업로드 건너뛰기")
def main(
    query: str,
    country: str,
    limit: int,
    headless: bool,
    image_only: bool,
    skip_upload: bool
):
    """광고 수집 파이프라인을 실행합니다 (Playwright 스크래핑 방식)."""
    if not query:
        logger.error("검색 키워드가 필요합니다. --query 옵션을 사용하세요.")
        return

    run_full_pipeline(
        query=query,
        country=country,
        limit=limit,
        headless=headless,
        image_only=image_only,
        skip_upload=skip_upload
    )


if __name__ == "__main__":
    main()

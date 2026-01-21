"""
주간 파이프라인 실행 모듈
광고 수집-이미지 업로드 파이프라인을 orchestration (Playwright 스크래핑 방식)
"""

import asyncio
import importlib
import json
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

# Supabase 클라이언트 초기화
def get_supabase_client():
    """Supabase 클라이언트 반환 (환경변수 필요)"""
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.warning("Supabase 환경변수 미설정 - DB 저장 건너뜀")
        return None

    try:
        from supabase import create_client
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Supabase 클라이언트 생성 실패: {e}")
        return None


def save_ads_to_supabase(ads: list, query: str, raw_file: str):
    """수집된 광고를 Supabase에 저장"""
    client = get_supabase_client()
    if not client:
        return {"saved": 0, "skipped": 0, "error": "Supabase 미연결"}

    saved = 0
    skipped = 0

    # raw 파일에서 permanent_image_url 정보 읽기
    try:
        with open(raw_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            ads_with_urls = {
                ad.get("image_urls", [""])[0]: ad.get("permanent_image_url")
                for ad in raw_data.get("ads", [])
            }
    except Exception as e:
        logger.warning(f"raw 파일 읽기 실패: {e}")
        ads_with_urls = {}

    for ad in ads:
        try:
            image_url = ad.get("image_urls", [""])[0] if ad.get("image_urls") else None
            if not image_url:
                skipped += 1
                continue

            # permanent_image_url 가져오기
            permanent_url = ads_with_urls.get(image_url) or ad.get("permanent_image_url")

            # ad_text가 문자열인 경우 배열로 변환 (PostgreSQL array 타입 호환)
            ad_text = ad.get("ad_text", [])
            if isinstance(ad_text, str):
                ad_text = [ad_text] if ad_text else []

            ad_data = {
                "keyword": query,
                "page_name": ad.get("page_name", "Unknown"),
                "ad_text": ad_text,
                "image_url": image_url,
                "permanent_image_url": permanent_url,
                "landing_url": ad.get("landing_url"),
                "collected_at": ad.get("collected_at", datetime.now().isoformat()),
            }

            # upsert로 중복 처리 (keyword + image_url 기준)
            result = client.table("ads").upsert(
                ad_data,
                on_conflict="keyword,image_url"
            ).execute()

            saved += 1

        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                logger.warning(f"광고 저장 실패: {e}")
                skipped += 1

    logger.info(f"Supabase 저장 완료: {saved}개 저장, {skipped}개 건너뜀")
    return {"saved": saved, "skipped": skipped}


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
            logger.info("\n[Step 2/3] imgbb 이미지 업로드 시작")
            upload_module = importlib.import_module("src.03_upload_images")
            process_raw_file = upload_module.process_raw_file_with_imgbb

            result = process_raw_file(raw_file)
            logger.info(f"[Step 2/3] 완료 - {result['uploaded']}개 업로드, {result['skipped']}개 건너뜀")
        else:
            logger.warning("\n[Step 2/3] IMGBB_API_KEY 미설정 - 이미지 업로드 건너뜀")
            logger.warning("imgbb를 사용하려면 .env에 IMGBB_API_KEY를 설정하세요.")
    else:
        logger.info("\n[Step 2/3] 이미지 업로드 건너뜀")

    # Step 3: Supabase에 광고 데이터 저장
    logger.info("\n[Step 3/3] Supabase DB 저장 시작")
    db_result = save_ads_to_supabase(ads, query, raw_file)
    if db_result.get("error"):
        logger.warning(f"[Step 3/3] {db_result['error']}")
    else:
        logger.info(f"[Step 3/3] 완료 - {db_result['saved']}개 저장, {db_result['skipped']}개 건너뜀")

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

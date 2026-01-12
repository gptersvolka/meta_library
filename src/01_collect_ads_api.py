"""
Meta Ads Library API를 통한 광고 수집 모듈
광고 메타데이터와 스냅샷 URL을 수집하여 JSON으로 저장
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import requests
from loguru import logger

from src.config import (
    get_meta_access_token,
    COUNTRY,
    QUERY,
    RAW_DIR,
    ensure_dirs
)

# Meta Ads Library API 엔드포인트
ADS_LIBRARY_API_URL = "https://graph.facebook.com/v18.0/ads_archive"


def collect_ads(
    query: str,
    country: str = "KR",
    limit: int = 50,
    ad_type: str = "ALL",
    ad_reached_countries: Optional[list] = None,
    search_page_ids: Optional[list] = None,
) -> list[dict]:
    """
    Meta Ads Library API에서 광고를 검색하여 수집

    Args:
        query: 검색 키워드
        country: 국가 코드 (ISO 3166-1 alpha-2)
        limit: 최대 수집 개수
        ad_type: 광고 유형 (ALL, POLITICAL_AND_ISSUE_ADS 등)
        ad_reached_countries: 광고가 도달한 국가 리스트
        search_page_ids: 특정 페이지 ID로 검색

    Returns:
        수집된 광고 리스트
    """
    logger.info(f"광고 수집 시작 - 키워드: {query}, 국가: {country}, 최대: {limit}개")

    params = {
        "access_token": get_meta_access_token(),
        "search_terms": query,
        "ad_type": ad_type,
        "ad_reached_countries": ad_reached_countries or [country],
        "fields": ",".join([
            "id",
            "ad_creation_time",
            "ad_creative_bodies",
            "ad_creative_link_captions",
            "ad_creative_link_descriptions",
            "ad_creative_link_titles",
            "ad_delivery_start_time",
            "ad_delivery_stop_time",
            "ad_snapshot_url",
            "bylines",
            "currency",
            "languages",
            "page_id",
            "page_name",
            "publisher_platforms",
            "estimated_audience_size",
        ]),
        "limit": min(limit, 100),  # API 최대 100개
    }

    if search_page_ids:
        params["search_page_ids"] = ",".join(search_page_ids)

    all_ads = []
    next_url = ADS_LIBRARY_API_URL

    while len(all_ads) < limit:
        try:
            if next_url == ADS_LIBRARY_API_URL:
                response = requests.get(next_url, params=params, timeout=30)
            else:
                response = requests.get(next_url, timeout=30)

            response.raise_for_status()
            data = response.json()

            ads = data.get("data", [])
            if not ads:
                logger.info("더 이상 수집할 광고가 없습니다.")
                break

            all_ads.extend(ads)
            logger.info(f"수집 진행: {len(all_ads)}개")

            # 페이지네이션
            paging = data.get("paging", {})
            next_url = paging.get("next")
            if not next_url:
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"API 호출 실패: {e}")
            break

    logger.info(f"총 {len(all_ads)}개 광고 수집 완료")
    return all_ads[:limit]


def save_raw_data(ads: list[dict], query: str) -> Path:
    """수집된 광고 데이터를 JSON 파일로 저장"""
    ensure_dirs()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c if c.isalnum() else "_" for c in query)[:30]
    filename = f"{timestamp}_{safe_query}.json"
    filepath = RAW_DIR / filename

    output_data = {
        "collected_at": datetime.now().isoformat(),
        "query": query,
        "count": len(ads),
        "ads": ads
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"원본 데이터 저장: {filepath}")
    return filepath


@click.command()
@click.option("--query", "-q", default=QUERY, help="검색 키워드")
@click.option("--country", "-c", default=COUNTRY, help="국가 코드")
@click.option("--limit", "-l", default=50, help="최대 수집 개수")
@click.option("--page-ids", "-p", default=None, help="페이지 ID (쉼표 구분)")
def main(query: str, country: str, limit: int, page_ids: Optional[str]):
    """Meta Ads Library에서 광고를 수집합니다."""
    if not query:
        logger.error("검색 키워드가 필요합니다. --query 옵션을 사용하세요.")
        return

    page_id_list = page_ids.split(",") if page_ids else None

    ads = collect_ads(
        query=query,
        country=country,
        limit=limit,
        search_page_ids=page_id_list
    )

    if ads:
        save_raw_data(ads, query)
    else:
        logger.warning("수집된 광고가 없습니다.")


if __name__ == "__main__":
    main()

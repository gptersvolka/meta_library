"""
Meta Ads Library 웹 스크래핑 모듈
Playwright를 사용하여 일반 상업 광고를 수집
"""

import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import click
from loguru import logger
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

from src.config import (
    COUNTRY,
    QUERY,
    RAW_DIR,
    ensure_dirs
)

# Meta 광고 라이브러리 기본 URL
ADS_LIBRARY_BASE_URL = "https://www.facebook.com/ads/library/"


def build_search_url(
    query: str,
    country: str = "KR",
    ad_type: str = "all",
    active_status: str = "active",
    media_type: str = "all"
) -> str:
    """검색 URL 생성"""
    params = {
        "active_status": active_status,
        "ad_type": ad_type,
        "country": country,
        "q": query,
        "search_type": "keyword_unordered",
        "media_type": media_type,
    }
    return f"{ADS_LIBRARY_BASE_URL}?{urlencode(params)}"


async def wait_for_ads_load(page: Page, timeout: int = 15000):
    """광고 카드가 로드될 때까지 대기"""
    try:
        # 여러 가능한 선택자 시도
        selectors = [
            'div[class*="_7jvw"]',  # 광고 카드 컨테이너
            'div[class*="x1dr59a3"]',
            'div[class*="xrvj5dj"]',
            '[data-visualcompletion="ignore-dynamic"]',
        ]

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout // len(selectors))
                logger.info(f"광고 컨테이너 발견: {selector}")
                break
            except PlaywrightTimeout:
                continue

        # 추가 로딩 대기
        await page.wait_for_timeout(3000)
    except PlaywrightTimeout:
        logger.warning("광고 로드 타임아웃 - 페이지에 광고가 없을 수 있습니다")


async def scroll_and_load_ads(page: Page, target_count: int, max_scrolls: int = 50):
    """스크롤하여 더 많은 광고 로드"""
    previous_count = 0
    scroll_count = 0
    no_change_count = 0

    while scroll_count < max_scrolls:
        # 현재 광고 개수 확인 - data-testid 선택자 사용
        ad_cards = await page.query_selector_all('[data-testid="ad-library-dynamic-content-container"]')
        if not ad_cards:
            ad_cards = await page.query_selector_all('[data-testid="ad-content-body-video-container"]')
        if not ad_cards:
            ad_cards = await page.query_selector_all('div[role="article"]')

        current_count = len(ad_cards)
        logger.info(f"현재 로드된 광고: {current_count}개")

        if current_count >= target_count:
            logger.info(f"목표 개수 {target_count}개 도달")
            break

        if current_count == previous_count:
            no_change_count += 1
            if no_change_count >= 3:
                logger.info("더 이상 로드할 광고가 없습니다")
                break
        else:
            no_change_count = 0

        previous_count = current_count

        # 스크롤 다운 - 안전하게
        try:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        except:
            pass
        await page.wait_for_timeout(2000)
        scroll_count += 1

    return current_count


async def extract_ad_data(page: Page, limit: int) -> list[dict]:
    """페이지에서 광고 데이터 추출"""
    ads = []

    # data-testid를 사용하여 광고 컨테이너 찾기
    ad_containers = await page.query_selector_all('[data-testid="ad-library-dynamic-content-container"]')

    if not ad_containers:
        # 대체 선택자: 비디오 컨테이너
        ad_containers = await page.query_selector_all('[data-testid="ad-content-body-video-container"]')

    if not ad_containers:
        # 대체 선택자: role=article
        ad_containers = await page.query_selector_all('div[role="article"]')

    logger.info(f"발견된 광고 컨테이너: {len(ad_containers)}개")

    for i, container in enumerate(ad_containers[:limit]):
        try:
            ad_data = await parse_ad_container(container, i)
            if ad_data:
                ads.append(ad_data)
                logger.debug(f"광고 {i+1} 파싱 완료: {ad_data.get('page_name', 'Unknown')}")
        except Exception as e:
            logger.warning(f"광고 {i+1} 파싱 실패: {e}")
            continue

    return ads


async def parse_ad_container(container, index: int) -> Optional[dict]:
    """개별 광고 컨테이너에서 데이터 추출"""
    ad_data = {
        "index": index,
        "collected_at": datetime.now().isoformat(),
    }

    try:
        # 부모 요소로 올라가서 전체 광고 카드 찾기
        # container의 부모들 중에서 광고 정보가 있는 곳 탐색
        parent = container

        # 텍스트 추출 시도 - 모든 span 요소에서 텍스트 수집
        all_text = await container.inner_text()
        if all_text:
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            # 첫 번째 줄이 보통 광고주 이름
            if lines:
                ad_data["page_name"] = lines[0] if len(lines[0]) < 100 else lines[0][:100]
            # 긴 텍스트가 광고 본문일 가능성
            ad_texts = [line for line in lines if len(line) > 20]
            if ad_texts:
                ad_data["ad_text"] = ad_texts[0] if len(ad_texts) == 1 else ad_texts[:3]

        # 이미지 URL 추출 - 모든 이미지 소스
        images = await container.query_selector_all('img')
        image_urls = []
        for img in images:
            src = await img.get_attribute("src")
            if src and ("scontent" in src or "fbcdn" in src):
                image_urls.append(src)

        if image_urls:
            ad_data["image_urls"] = list(set(image_urls))  # 중복 제거

        # 비디오 URL 추출
        videos = await container.query_selector_all('video')
        video_urls = []
        for video in videos:
            src = await video.get_attribute("src")
            if src:
                video_urls.append(src)
            # source 태그도 확인
            sources = await video.query_selector_all('source')
            for source in sources:
                src = await source.get_attribute("src")
                if src:
                    video_urls.append(src)

        if video_urls:
            ad_data["video_urls"] = list(set(video_urls))

        # 링크 추출
        links = await container.query_selector_all('a')
        for link in links:
            href = await link.get_attribute("href")
            if href:
                # 광고 ID가 포함된 링크
                if "id=" in href:
                    ad_data["ad_snapshot_url"] = f"https://www.facebook.com{href}" if href.startswith("/") else href
                    id_match = re.search(r'id=(\d+)', href)
                    if id_match:
                        ad_data["ad_id"] = id_match.group(1)
                    break

        # 데이터가 있으면 반환
        if any(key in ad_data for key in ["page_name", "ad_text", "image_urls", "video_urls"]):
            return ad_data

    except Exception as e:
        logger.debug(f"파싱 중 오류: {e}")

    return None


async def collect_ads_playwright(
    query: str,
    country: str = "KR",
    limit: int = 50,
    headless: bool = True,
    active_only: bool = True
) -> list[dict]:
    """
    Playwright로 Meta 광고 라이브러리에서 광고 수집

    Args:
        query: 검색 키워드
        country: 국가 코드
        limit: 최대 수집 개수
        headless: 헤드리스 모드 여부
        active_only: 활성 광고만 수집

    Returns:
        수집된 광고 리스트
    """
    logger.info(f"광고 수집 시작 - 키워드: {query}, 국가: {country}, 최대: {limit}개")

    active_status = "active" if active_only else "all"
    url = build_search_url(query, country, active_status=active_status)
    logger.info(f"검색 URL: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 페이지 로드
            await page.goto(url, wait_until="networkidle", timeout=60000)
            logger.info("페이지 로드 완료")

            # 쿠키 동의 팝업 처리
            try:
                cookie_btn = await page.query_selector('button[data-cookiebanner="accept_button"]')
                if cookie_btn:
                    await cookie_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass

            # 광고 로드 대기
            await wait_for_ads_load(page)

            # 스크롤하여 광고 로드
            loaded_count = await scroll_and_load_ads(page, limit)
            logger.info(f"총 {loaded_count}개 광고 로드됨")

            # 광고 데이터 추출
            ads = await extract_ad_data(page, limit)
            logger.info(f"총 {len(ads)}개 광고 데이터 추출 완료")

        except Exception as e:
            logger.error(f"수집 중 오류 발생: {e}")
            ads = []

        finally:
            await browser.close()

    return ads


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
        "source": "playwright_scraping",
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
@click.option("--headless/--no-headless", default=True, help="헤드리스 모드")
@click.option("--active-only/--all", default=True, help="활성 광고만 수집")
def main(query: str, country: str, limit: int, headless: bool, active_only: bool):
    """Meta Ads Library에서 광고를 수집합니다 (Playwright 스크래핑)."""
    if not query:
        logger.error("검색 키워드가 필요합니다. --query 옵션을 사용하세요.")
        return

    ads = asyncio.run(collect_ads_playwright(
        query=query,
        country=country,
        limit=limit,
        headless=headless,
        active_only=active_only
    ))

    if ads:
        save_raw_data(ads, query)
    else:
        logger.warning("수집된 광고가 없습니다.")


if __name__ == "__main__":
    main()

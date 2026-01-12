"""
광고 크리에이티브(이미지) 수집 모듈
API 응답에서 이미지 URL을 추출하거나, Playwright로 스냅샷 페이지를 캡처
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click
import requests
from loguru import logger
from PIL import Image
from io import BytesIO

from src.config import RAW_DIR, IMAGES_DIR, ensure_dirs

# Playwright는 필요할 때만 import (설치 안 된 경우 대비)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright가 설치되지 않았습니다. 캡처 기능이 제한됩니다.")


def download_image(url: str, save_path: Path) -> bool:
    """URL에서 이미지를 다운로드하여 저장"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # 이미지 유효성 검사
        img = Image.open(BytesIO(response.content))
        img.save(save_path)

        logger.debug(f"이미지 다운로드 완료: {save_path}")
        return True
    except Exception as e:
        logger.error(f"이미지 다운로드 실패 ({url}): {e}")
        return False


def capture_snapshot_page(snapshot_url: str, save_path: Path) -> bool:
    """Playwright로 광고 스냅샷 페이지를 캡처"""
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright가 필요합니다. 'pip install playwright && playwright install' 실행")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1024})

            page.goto(snapshot_url, wait_until="networkidle", timeout=60000)

            # 광고 카드 영역을 찾아서 캡처 (선택자는 Meta 페이지 구조에 따라 조정 필요)
            # 전체 페이지 캡처를 기본으로 함
            page.screenshot(path=str(save_path), full_page=False)

            browser.close()
            logger.debug(f"스냅샷 캡처 완료: {save_path}")
            return True
    except Exception as e:
        logger.error(f"스냅샷 캡처 실패 ({snapshot_url}): {e}")
        return False


def extract_image_urls_from_ad(ad: dict) -> list[str]:
    """광고 데이터에서 이미지 URL 추출 (가능한 경우)"""
    # Meta API 응답에서 이미지 URL이 포함된 필드들
    # 참고: 실제 이미지 URL은 ad_snapshot_url을 통해 접근해야 할 수 있음
    image_urls = []

    # ad_creative_link_captions, ad_creative_link_titles 등에서 이미지 추출 시도
    # 실제 API 응답 구조에 따라 조정 필요

    return image_urls


def fetch_creatives_from_raw(raw_file: Path) -> list[dict]:
    """
    원본 JSON 파일에서 광고 크리에이티브를 수집

    Returns:
        수집 결과 리스트 [{ad_id, image_path, status, ...}, ...]
    """
    ensure_dirs()

    with open(raw_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    ads = data.get("ads", [])
    results = []

    for i, ad in enumerate(ads):
        ad_id = ad.get("id", f"unknown_{i}")
        page_name = ad.get("page_name", "unknown")
        snapshot_url = ad.get("ad_snapshot_url")

        # 파일명 생성 (안전한 문자만 사용)
        safe_page_name = "".join(c if c.isalnum() else "_" for c in page_name)[:20]
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{timestamp}_{safe_page_name}_{ad_id}.png"
        save_path = IMAGES_DIR / filename

        result = {
            "ad_id": ad_id,
            "page_name": page_name,
            "snapshot_url": snapshot_url,
            "image_path": str(save_path),
            "status": "pending"
        }

        # 1차: 직접 이미지 URL이 있으면 다운로드
        image_urls = extract_image_urls_from_ad(ad)
        if image_urls:
            if download_image(image_urls[0], save_path):
                result["status"] = "success"
                result["method"] = "direct_download"
                results.append(result)
                continue

        # 2차: 스냅샷 URL로 페이지 캡처
        if snapshot_url:
            if capture_snapshot_page(snapshot_url, save_path):
                result["status"] = "success"
                result["method"] = "snapshot_capture"
            else:
                result["status"] = "failed"
                result["error"] = "캡처 실패"
        else:
            result["status"] = "skipped"
            result["error"] = "스냅샷 URL 없음"

        results.append(result)
        logger.info(f"[{i+1}/{len(ads)}] {ad_id}: {result['status']}")

    return results


@click.command()
@click.option("--raw-file", "-f", type=click.Path(exists=True), help="원본 JSON 파일 경로")
@click.option("--latest", "-l", is_flag=True, help="가장 최근 원본 파일 사용")
def main(raw_file: Optional[str], latest: bool):
    """광고 크리에이티브(이미지)를 수집합니다."""
    ensure_dirs()

    if latest:
        # 가장 최근 파일 찾기
        raw_files = sorted(RAW_DIR.glob("*.json"), reverse=True)
        if not raw_files:
            logger.error("원본 데이터 파일이 없습니다. 먼저 01_collect_ads_api.py를 실행하세요.")
            return
        raw_file = raw_files[0]
        logger.info(f"최근 파일 사용: {raw_file}")
    elif not raw_file:
        logger.error("--raw-file 또는 --latest 옵션을 지정하세요.")
        return
    else:
        raw_file = Path(raw_file)

    results = fetch_creatives_from_raw(raw_file)

    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(f"크리에이티브 수집 완료: {success_count}/{len(results)}개 성공")


if __name__ == "__main__":
    main()

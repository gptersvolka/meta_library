"""
광고 크리에이티브(이미지) 다운로드 모듈
Playwright 스크래핑으로 수집된 이미지 URL에서 이미지를 다운로드
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from io import BytesIO

import click
import requests
from loguru import logger
from PIL import Image

from src.config import RAW_DIR, IMAGES_DIR, ensure_dirs


def download_image(url: str, save_path: Path, timeout: int = 30) -> bool:
    """URL에서 이미지를 다운로드하여 저장"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        # 이미지 유효성 검사 및 저장
        img = Image.open(BytesIO(response.content))
        img.save(save_path)

        logger.debug(f"이미지 다운로드 완료: {save_path}")
        return True
    except Exception as e:
        logger.error(f"이미지 다운로드 실패 ({url[:50]}...): {e}")
        return False


def download_image_bytes(url: str, timeout: int = 30) -> Optional[bytes]:
    """URL에서 이미지 바이트 다운로드 (해시 계산용)"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.debug(f"이미지 바이트 다운로드 실패: {e}")
        return None


def calculate_image_hash(image_bytes: bytes) -> str:
    """이미지 바이트에서 MD5 해시 계산"""
    return hashlib.md5(image_bytes).hexdigest()


def fetch_creatives_from_raw(raw_file: Path, skip_duplicates: bool = True) -> list[dict]:
    """
    Playwright 스크래핑 JSON에서 이미지를 다운로드

    Args:
        raw_file: 원본 JSON 파일 경로
        skip_duplicates: 이미지 해시 기준 중복 제거 (기본값: True)

    Returns:
        다운로드 결과 리스트 [{ad_index, page_name, image_url, local_path, image_hash, status}, ...]
    """
    ensure_dirs()

    with open(raw_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    query = data.get("query", "unknown")
    ads = data.get("ads", [])
    results = []
    seen_hashes = set()
    skipped = 0

    logger.info(f"총 {len(ads)}개 광고에서 이미지 다운로드 시작")

    for i, ad in enumerate(ads):
        page_name = ad.get("page_name", "unknown")
        image_urls = ad.get("image_urls", [])

        if not image_urls:
            continue

        # 첫 번째 이미지 URL 사용
        image_url = image_urls[0]

        # 이미지 바이트 다운로드 (해시 계산 + 저장용)
        image_bytes = download_image_bytes(image_url)
        if not image_bytes:
            results.append({
                "ad_index": i,
                "page_name": page_name,
                "image_url": image_url,
                "status": "failed",
                "error": "다운로드 실패"
            })
            continue

        # 해시 계산
        image_hash = calculate_image_hash(image_bytes)

        # 중복 체크
        if skip_duplicates and image_hash in seen_hashes:
            skipped += 1
            continue
        seen_hashes.add(image_hash)

        # 파일명 생성 (안전한 문자만 사용)
        safe_page_name = "".join(c if c.isalnum() else "_" for c in page_name)[:20]
        timestamp = datetime.now().strftime("%Y%m%d")
        # 해시 앞 8자리로 고유성 보장
        filename = f"{timestamp}_{safe_page_name}_{image_hash[:8]}.png"
        save_path = IMAGES_DIR / filename

        # 이미 존재하면 건너뛰기
        if save_path.exists():
            results.append({
                "ad_index": i,
                "page_name": page_name,
                "image_url": image_url,
                "local_path": str(save_path),
                "filename": filename,
                "image_hash": image_hash,
                "status": "exists"
            })
            continue

        # 이미지 저장
        try:
            img = Image.open(BytesIO(image_bytes))
            img.save(save_path)

            results.append({
                "ad_index": i,
                "page_name": page_name,
                "image_url": image_url,
                "local_path": str(save_path),
                "filename": filename,
                "image_hash": image_hash,
                "status": "success"
            })
            logger.debug(f"[{i+1}] {page_name}: 저장 완료")
        except Exception as e:
            results.append({
                "ad_index": i,
                "page_name": page_name,
                "image_url": image_url,
                "image_hash": image_hash,
                "status": "failed",
                "error": str(e)
            })

    if skipped > 0:
        logger.info(f"중복 이미지 {skipped}개 건너뜀")

    success_count = sum(1 for r in results if r["status"] in ["success", "exists"])
    logger.info(f"이미지 다운로드 완료: {success_count}/{len(results)}개 성공")

    return results


@click.command()
@click.option("--raw-file", "-f", type=click.Path(exists=True), help="원본 JSON 파일 경로")
@click.option("--latest", "-l", is_flag=True, help="가장 최근 원본 파일 사용")
@click.option("--no-dedup", is_flag=True, help="중복 제거 비활성화")
def main(raw_file: Optional[str], latest: bool, no_dedup: bool):
    """Playwright 스크래핑 결과에서 이미지를 다운로드합니다."""
    ensure_dirs()

    if latest:
        raw_files = sorted(RAW_DIR.glob("*.json"), reverse=True)
        if not raw_files:
            logger.error("원본 데이터 파일이 없습니다. 먼저 01_collect_ads.py를 실행하세요.")
            return
        raw_file = raw_files[0]
        logger.info(f"최근 파일 사용: {raw_file}")
    elif not raw_file:
        logger.error("--raw-file 또는 --latest 옵션을 지정하세요.")
        return
    else:
        raw_file = Path(raw_file)

    results = fetch_creatives_from_raw(raw_file, skip_duplicates=not no_dedup)

    success_count = sum(1 for r in results if r["status"] in ["success", "exists"])
    logger.info(f"크리에이티브 다운로드 완료: {success_count}/{len(results)}개")


if __name__ == "__main__":
    main()

"""
Cloudflare R2 이미지 업로드 모듈
수집된 광고 이미지를 R2에 업로드하고 공개 URL 반환
"""

import hashlib
import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import boto3
import click
import requests
from botocore.config import Config
from loguru import logger
from PIL import Image

from src.config import RAW_DIR, PROJECT_ROOT, ensure_dirs, get_env


def get_r2_client():
    """Cloudflare R2 클라이언트 생성"""
    account_id = get_env("R2_ACCOUNT_ID", required=True)
    access_key_id = get_env("R2_ACCESS_KEY_ID", required=True)
    secret_access_key = get_env("R2_SECRET_ACCESS_KEY", required=True)

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )


def get_r2_public_url() -> str:
    """R2 공개 URL 반환"""
    return get_env("R2_PUBLIC_URL", required=True).rstrip("/")


def get_r2_bucket_name() -> str:
    """R2 버킷 이름 반환"""
    return get_env("R2_BUCKET_NAME", default="meta-ad-images")


def download_image_bytes(url: str, timeout: int = 30) -> Optional[bytes]:
    """URL에서 이미지 바이트 다운로드"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.debug(f"이미지 다운로드 실패: {e}")
        return None


def calculate_image_hash(image_bytes: bytes) -> str:
    """이미지 바이트에서 MD5 해시 계산"""
    return hashlib.md5(image_bytes).hexdigest()


def upload_to_r2(
    image_bytes: bytes,
    filename: str,
    content_type: str = "image/png"
) -> Optional[str]:
    """
    이미지를 R2에 업로드하고 공개 URL 반환

    Args:
        image_bytes: 이미지 바이트 데이터
        filename: 저장할 파일명
        content_type: MIME 타입

    Returns:
        공개 URL 또는 None (실패 시)
    """
    try:
        client = get_r2_client()
        bucket_name = get_r2_bucket_name()
        public_url = get_r2_public_url()

        # 이미지를 PNG로 변환 (일관성 위해)
        img = Image.open(BytesIO(image_bytes))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # R2에 업로드
        client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=buffer.getvalue(),
            ContentType=content_type
        )

        r2_url = f"{public_url}/{filename}"
        logger.debug(f"R2 업로드 완료: {filename}")
        return r2_url

    except Exception as e:
        logger.error(f"R2 업로드 실패 ({filename}): {e}")
        return None


def check_r2_exists(filename: str) -> bool:
    """R2에 파일이 이미 존재하는지 확인"""
    try:
        client = get_r2_client()
        bucket_name = get_r2_bucket_name()

        client.head_object(Bucket=bucket_name, Key=filename)
        return True
    except:
        return False


def process_raw_file_to_r2(raw_file: Path, skip_duplicates: bool = True) -> dict:
    """
    수집된 JSON 파일의 이미지들을 R2에 업로드하고 URL 추가

    Args:
        raw_file: 원본 JSON 파일 경로
        skip_duplicates: 중복 이미지 건너뛰기

    Returns:
        처리 결과 (업데이트된 JSON 데이터)
    """
    ensure_dirs()

    with open(raw_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    query = data.get("query", "unknown")
    ads = data.get("ads", [])
    public_url = get_r2_public_url()

    # 해시 로그 파일 (중복 방지)
    hash_log_file = PROJECT_ROOT / "data" / "r2_image_hashes.json"
    seen_hashes = set()
    if skip_duplicates and hash_log_file.exists():
        try:
            with open(hash_log_file, "r", encoding="utf-8") as f:
                seen_hashes = set(json.load(f).get("hashes", []))
        except:
            pass

    uploaded = 0
    skipped = 0
    failed = 0

    logger.info(f"총 {len(ads)}개 광고 이미지 R2 업로드 시작")

    for i, ad in enumerate(ads):
        image_urls = ad.get("image_urls", [])
        if not image_urls:
            continue

        image_url = image_urls[0]

        # 이미 R2 URL이 있으면 건너뛰기
        if ad.get("r2_image_url"):
            skipped += 1
            continue

        # 이미지 다운로드
        image_bytes = download_image_bytes(image_url)
        if not image_bytes:
            failed += 1
            continue

        # 해시 계산
        image_hash = calculate_image_hash(image_bytes)

        # 중복 체크
        if skip_duplicates and image_hash in seen_hashes:
            # 중복이지만 R2 URL 설정 (기존 파일 참조)
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{timestamp}_{image_hash[:8]}.png"
            ad["r2_image_url"] = f"{public_url}/{filename}"
            skipped += 1
            continue

        seen_hashes.add(image_hash)

        # 파일명 생성
        page_name = ad.get("page_name", "unknown")
        safe_name = "".join(c if c.isalnum() else "_" for c in page_name)[:20]
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{timestamp}_{safe_name}_{image_hash[:8]}.png"

        # R2에 이미 존재하는지 확인
        if check_r2_exists(filename):
            ad["r2_image_url"] = f"{public_url}/{filename}"
            skipped += 1
            continue

        # R2에 업로드
        r2_url = upload_to_r2(image_bytes, filename)
        if r2_url:
            ad["r2_image_url"] = r2_url
            uploaded += 1
            logger.debug(f"[{i+1}] {page_name}: 업로드 완료")
        else:
            failed += 1

    # 해시 로그 저장
    if skip_duplicates and seen_hashes:
        with open(hash_log_file, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.now().isoformat(),
                "count": len(seen_hashes),
                "hashes": list(seen_hashes)
            }, f, ensure_ascii=False, indent=2)

    # 업데이트된 JSON 저장
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"R2 업로드 완료: {uploaded}개 성공, {skipped}개 건너뜀, {failed}개 실패")

    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
        "total": len(ads)
    }


@click.command()
@click.option("--raw-file", "-f", type=click.Path(exists=True), help="원본 JSON 파일 경로")
@click.option("--latest", "-l", is_flag=True, help="가장 최근 원본 파일 사용")
@click.option("--all", "-a", "process_all", is_flag=True, help="모든 원본 파일 처리")
@click.option("--no-dedup", is_flag=True, help="중복 제거 비활성화")
def main(raw_file: Optional[str], latest: bool, process_all: bool, no_dedup: bool):
    """수집된 광고 이미지를 Cloudflare R2에 업로드합니다."""
    ensure_dirs()

    if process_all:
        raw_files = sorted(RAW_DIR.glob("*.json"))
        if not raw_files:
            logger.error("원본 데이터 파일이 없습니다.")
            return
        logger.info(f"총 {len(raw_files)}개 파일 처리")
        for rf in raw_files:
            logger.info(f"\n처리 중: {rf.name}")
            process_raw_file_to_r2(rf, skip_duplicates=not no_dedup)
    elif latest:
        raw_files = sorted(RAW_DIR.glob("*.json"), reverse=True)
        if not raw_files:
            logger.error("원본 데이터 파일이 없습니다.")
            return
        raw_file = raw_files[0]
        logger.info(f"최근 파일 사용: {raw_file}")
        process_raw_file_to_r2(raw_file, skip_duplicates=not no_dedup)
    elif raw_file:
        process_raw_file_to_r2(Path(raw_file), skip_duplicates=not no_dedup)
    else:
        logger.error("--raw-file, --latest, 또는 --all 옵션을 지정하세요.")


if __name__ == "__main__":
    main()

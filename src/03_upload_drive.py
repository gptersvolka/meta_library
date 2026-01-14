"""
Google Drive 업로드 모듈
수집된 이미지를 Drive에 업로드하고 공유 링크 생성
폴더 구조: 루트폴더 > 키워드 > 날짜(YYMMDD) > 이미지
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.config import (
    get_google_credentials_path,
    get_drive_folder_id,
    IMAGES_DIR,
    ensure_dirs
)

# Google Drive API 스코프
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service():
    """Google Drive API 서비스 객체 생성"""
    credentials = service_account.Credentials.from_service_account_file(
        get_google_credentials_path(), scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def get_or_create_folder(service, folder_name: str, parent_id: str, use_shared_drive: bool = True) -> str:
    """
    폴더가 있으면 ID 반환, 없으면 생성 후 ID 반환

    Args:
        service: Drive API 서비스 객체
        folder_name: 폴더 이름
        parent_id: 부모 폴더 ID
        use_shared_drive: 공유 드라이브 사용 여부

    Returns:
        폴더 ID
    """
    # 기존 폴더 검색
    query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=use_shared_drive,
        includeItemsFromAllDrives=use_shared_drive
    ).execute()
    files = results.get("files", [])

    if files:
        logger.debug(f"기존 폴더 사용: {folder_name}")
        return files[0]["id"]

    # 폴더 생성
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = service.files().create(
        body=folder_metadata,
        fields="id",
        supportsAllDrives=use_shared_drive
    ).execute()
    logger.info(f"새 폴더 생성: {folder_name}")
    return folder["id"]


def upload_file(service, file_path: Path, folder_id: str, use_shared_drive: bool = True) -> Optional[dict]:
    """
    파일을 Google Drive에 업로드 (공유 드라이브 지원)

    Returns:
        업로드된 파일 정보 {id, name, webViewLink, webContentLink}
    """
    try:
        file_metadata = {
            "name": file_path.name,
            "parents": [folder_id]
        }

        # MIME 타입 결정
        suffix = file_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        mime_type = mime_types.get(suffix, "application/octet-stream")

        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, webContentLink",
            supportsAllDrives=use_shared_drive
        ).execute()

        # 파일을 링크가 있는 모든 사용자가 볼 수 있도록 권한 설정
        try:
            service.permissions().create(
                fileId=file["id"],
                body={"type": "anyone", "role": "reader"},
                supportsAllDrives=use_shared_drive
            ).execute()
        except Exception as e:
            logger.warning(f"권한 설정 실패 (업로드는 성공): {e}")

        logger.debug(f"업로드 완료: {file_path.name} -> {file.get('webViewLink')}")
        return file

    except Exception as e:
        logger.error(f"업로드 실패 ({file_path}): {e}")
        return None


def upload_all_images(
    folder_id: Optional[str] = None,
    fetch_results: list[dict] = None,
    query: str = None,
    date_str: str = None
) -> list[dict]:
    """
    IMAGES_DIR의 모든 이미지를 Drive에 업로드

    Args:
        folder_id: Drive 루트 폴더 ID
        fetch_results: fetch_creatives 결과 (image_hash 매핑용)
        query: 검색 키워드 (폴더 구조용)
        date_str: 날짜 문자열 YYMMDD (폴더 구조용)

    Returns:
        업로드 결과 리스트 [{local_path, drive_id, drive_url, image_hash, status}, ...]

    폴더 구조:
        루트폴더 > 키워드 > 날짜(YYMMDD) > 이미지
    """
    ensure_dirs()
    root_folder_id = folder_id or get_drive_folder_id()

    service = get_drive_service()
    results = []

    image_files = list(IMAGES_DIR.glob("*"))
    image_files = [f for f in image_files if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp"]]

    if not image_files:
        logger.warning("업로드할 이미지가 없습니다.")
        return results

    # 폴더 구조 생성: 루트 > 키워드 > 날짜
    target_folder_id = root_folder_id

    if query:
        # 키워드 폴더 생성/조회
        keyword_folder_id = get_or_create_folder(service, query, root_folder_id)
        target_folder_id = keyword_folder_id

        if date_str:
            # 날짜 폴더 생성/조회 (YYMMDD 형식)
            date_folder_id = get_or_create_folder(service, date_str, keyword_folder_id)
            target_folder_id = date_folder_id

    logger.info(f"업로드 폴더: {'루트' if not query else query}{' > ' + date_str if date_str else ''}")

    # fetch_results를 filename으로 매핑 (image_hash 조회용)
    hash_map = {}
    if fetch_results:
        for fr in fetch_results:
            if fr.get("filename") and fr.get("image_hash"):
                hash_map[fr["filename"]] = fr["image_hash"]

    logger.info(f"{len(image_files)}개 이미지 업로드 시작")

    for i, file_path in enumerate(image_files):
        result = {
            "local_path": str(file_path),
            "filename": file_path.name,
            "status": "pending"
        }

        # image_hash 추가 (fetch_results에서 매핑)
        if file_path.name in hash_map:
            result["image_hash"] = hash_map[file_path.name]

        file_info = upload_file(service, file_path, target_folder_id)

        if file_info:
            result["drive_id"] = file_info["id"]
            result["drive_url"] = file_info.get("webViewLink", "")
            result["drive_content_url"] = file_info.get("webContentLink", "")
            # IMAGE 수식용 직접 링크 생성
            result["image_formula_url"] = f"https://drive.google.com/uc?id={file_info['id']}"
            result["status"] = "success"
        else:
            result["status"] = "failed"

        results.append(result)
        logger.info(f"[{i+1}/{len(image_files)}] {file_path.name}: {result['status']}")

    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(f"업로드 완료: {success_count}/{len(results)}개 성공")

    return results


@click.command()
@click.option("--folder-id", "-f", default=None, help="Drive 폴더 ID (기본값: .env의 DRIVE_FOLDER_ID)")
@click.option("--file", "-i", type=click.Path(exists=True), help="특정 파일만 업로드")
def main(folder_id: Optional[str], file: Optional[str]):
    """이미지를 Google Drive에 업로드합니다."""
    if file:
        service = get_drive_service()
        result = upload_file(service, Path(file), folder_id or get_drive_folder_id())
        if result:
            logger.info(f"업로드 성공: {result.get('webViewLink')}")
        else:
            logger.error("업로드 실패")
    else:
        upload_all_images(folder_id)


if __name__ == "__main__":
    main()

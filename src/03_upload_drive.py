"""
Google Drive 업로드 모듈
수집된 이미지를 Drive에 업로드하고 공유 링크 생성
"""

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


def upload_file(service, file_path: Path, folder_id: str) -> Optional[dict]:
    """
    파일을 Google Drive에 업로드

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
            fields="id, name, webViewLink, webContentLink"
        ).execute()

        # 파일을 링크가 있는 모든 사용자가 볼 수 있도록 권한 설정
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"}
        ).execute()

        logger.debug(f"업로드 완료: {file_path.name} -> {file.get('webViewLink')}")
        return file

    except Exception as e:
        logger.error(f"업로드 실패 ({file_path}): {e}")
        return None


def upload_all_images(folder_id: Optional[str] = None) -> list[dict]:
    """
    IMAGES_DIR의 모든 이미지를 Drive에 업로드

    Returns:
        업로드 결과 리스트 [{local_path, drive_id, drive_url, status}, ...]
    """
    ensure_dirs()
    folder_id = folder_id or get_drive_folder_id()

    service = get_drive_service()
    results = []

    image_files = list(IMAGES_DIR.glob("*"))
    image_files = [f for f in image_files if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp"]]

    if not image_files:
        logger.warning("업로드할 이미지가 없습니다.")
        return results

    logger.info(f"{len(image_files)}개 이미지 업로드 시작")

    for i, file_path in enumerate(image_files):
        result = {
            "local_path": str(file_path),
            "filename": file_path.name,
            "status": "pending"
        }

        file_info = upload_file(service, file_path, folder_id)

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

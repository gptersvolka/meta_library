"""
Google Sheets 기록 모듈
수집된 광고 데이터와 OCR 결과를 스프레드시트에 기록
"""

import hashlib
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import click
import gspread
import requests
from google.oauth2 import service_account
from loguru import logger
from PIL import Image

# pytesseract는 선택적 import (설치 안 된 경우 대비)
try:
    import pytesseract
    # Windows Tesseract 경로 설정
    import platform
    if platform.system() == "Windows":
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if Path(tesseract_path).exists():
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract가 설치되지 않았습니다. OCR 기능이 비활성화됩니다.")

from src.config import (
    get_google_credentials_path,
    get_sheet_id,
    RAW_DIR,
    ensure_dirs
)

# Google Sheets API 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]


def get_sheets_client() -> gspread.Client:
    """Google Sheets API 클라이언트 생성"""
    credentials = service_account.Credentials.from_service_account_file(
        get_google_credentials_path(), scopes=SCOPES
    )
    return gspread.authorize(credentials)


def ensure_worksheet(spreadsheet: gspread.Spreadsheet, title: str, headers: list[str]) -> gspread.Worksheet:
    """워크시트가 없으면 생성하고, 헤더가 없거나 다르면 업데이트"""
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        logger.info(f"워크시트 생성: {title}")

    # 헤더 확인 및 추가/업데이트
    existing_headers = worksheet.row_values(1) if worksheet.row_count > 0 else []
    if not existing_headers:
        worksheet.append_row(headers)
        logger.debug(f"헤더 추가: {headers}")
    elif existing_headers != headers:
        # 헤더가 다르면 업데이트
        worksheet.update([headers], 'A1')
        logger.debug(f"헤더 업데이트: {headers}")

    return worksheet


def write_ads_raw(spreadsheet: gspread.Spreadsheet, raw_file: Path, upload_results: list[dict] = None):
    """
    ads_raw 탭에 광고 데이터 기록

    Args:
        spreadsheet: 스프레드시트 객체
        raw_file: 원본 JSON 파일 경로
        upload_results: Drive 업로드 결과 (image_formula_url 포함)
    """
    headers = [
        "collected_at",
        "query",
        "ad_id",
        "page_name",
        "ad_snapshot_url",
        "image_file_path",
        "image_drive_url",
        "platforms",
        "start_date",
        "end_date",
        "status"
    ]

    worksheet = ensure_worksheet(spreadsheet, "ads_raw", headers)

    with open(raw_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    collected_at = data.get("collected_at", datetime.now().isoformat())
    query = data.get("query", "")
    ads = data.get("ads", [])

    # 업로드 결과를 ad_id로 매핑
    upload_map = {}
    if upload_results:
        for result in upload_results:
            # 파일명에서 ad_id 추출 (형식: YYYYMMDD_pagename_adid.png)
            filename = result.get("filename", "")
            parts = filename.rsplit("_", 1)
            if len(parts) > 1:
                ad_id = parts[-1].replace(".png", "").replace(".jpg", "")
                upload_map[ad_id] = result

    rows = []
    for ad in ads:
        ad_id = ad.get("id", "")
        upload_info = upload_map.get(ad_id, {})

        # IMAGE 수식으로 이미지 표시
        image_url = upload_info.get("image_formula_url", "")
        image_cell = f'=IMAGE("{image_url}")' if image_url else ""

        row = [
            collected_at,
            query,
            ad_id,
            ad.get("page_name", ""),
            ad.get("ad_snapshot_url", ""),
            upload_info.get("local_path", ""),
            image_cell,
            ", ".join(ad.get("publisher_platforms", [])),
            ad.get("ad_delivery_start_time", ""),
            ad.get("ad_delivery_stop_time", ""),
            "success"
        ]
        rows.append(row)

    if rows:
        worksheet.append_rows(rows)
        logger.info(f"ads_raw에 {len(rows)}개 행 추가")


def download_image(image_url: str, timeout: int = 15) -> Optional[bytes]:
    """이미지 URL에서 바이트 다운로드"""
    if not image_url:
        return None
    try:
        response = requests.get(image_url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.debug(f"이미지 다운로드 실패: {e}")
        return None


def calculate_image_hash(image_bytes: bytes) -> Optional[str]:
    """이미지 바이트에서 MD5 해시 계산"""
    if not image_bytes:
        return None
    return hashlib.md5(image_bytes).hexdigest()


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    이미지에서 텍스트 추출 (OCR)

    Args:
        image_bytes: 이미지 바이트 데이터

    Returns:
        추출된 텍스트 (줄바꿈 → 공백으로 변환)
    """
    if not TESSERACT_AVAILABLE or not image_bytes:
        return ""

    try:
        img = Image.open(BytesIO(image_bytes))
        # 한글 + 영어 인식
        text = pytesseract.image_to_string(img, lang='kor+eng')
        # 줄바꿈을 공백으로, 여러 공백을 하나로
        text = ' '.join(text.split())
        return text.strip()
    except Exception as e:
        logger.debug(f"OCR 실패: {e}")
        return ""


def get_existing_image_hashes(worksheet: gspread.Worksheet, hash_col_index: int = 7) -> set:
    """
    기존 시트에서 이미지 해시를 가져와 중복 체크용 set 생성

    Args:
        worksheet: 워크시트 객체
        hash_col_index: 이미지해시 컬럼 인덱스 (0-based, 기본값 6 = G열)

    Returns:
        set: 이미지 해시 문자열의 set
    """
    existing = set()
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) > 1:  # 헤더 제외
            for row in all_values[1:]:
                if len(row) > hash_col_index and row[hash_col_index]:
                    image_hash = row[hash_col_index].strip()
                    if image_hash:
                        existing.add(image_hash)
    except Exception as e:
        logger.warning(f"기존 이미지 해시 로드 실패: {e}")
    return existing


def write_ads_by_keyword(
    spreadsheet: gspread.Spreadsheet,
    raw_file: Path,
    upload_results: list[dict] = None,
    skip_duplicates: bool = True
):
    """
    키워드별 탭에 광고 데이터 기록 (Playwright 스크래핑 데이터용)

    Args:
        spreadsheet: 스프레드시트 객체
        raw_file: 원본 JSON 파일 경로
        upload_results: Drive 업로드 결과 (있으면 Drive URL 사용, 없으면 원본 URL)
        skip_duplicates: True면 중복 광고 제외 - 이미지 MD5 해시 기준 (기본값: True)
    """
    headers = [
        "수집일시",
        "광고주",
        "광고문구",
        "이미지",
        "이미지텍스트",  # OCR 추출 텍스트
        "비디오URL",
        "광고링크",
        "이미지해시"  # 중복 체크용 (숨겨도 됨)
    ]

    with open(raw_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    query = data.get("query", "unknown")
    collected_at = data.get("collected_at", datetime.now().isoformat())[:10]  # 날짜만
    ads = data.get("ads", [])

    # 키워드명으로 탭 생성
    worksheet = ensure_worksheet(spreadsheet, query, headers)

    # 중복 체크용 기존 이미지 해시 로드 (H열 = 인덱스 7)
    existing_hashes = set()
    if skip_duplicates:
        existing_hashes = get_existing_image_hashes(worksheet, hash_col_index=7)
        if existing_hashes:
            logger.info(f"기존 이미지 해시 {len(existing_hashes)}개 로드 (중복 체크용)")

    # upload_results를 image_hash로 매핑 (Drive URL 사용 시)
    drive_url_map = {}
    if upload_results:
        for result in upload_results:
            if result.get("status") == "success" and result.get("image_hash"):
                drive_url_map[result["image_hash"]] = result.get("image_formula_url", "")
        logger.info(f"Drive URL {len(drive_url_map)}개 매핑됨")

    rows = []
    skipped = 0
    no_image = 0

    logger.info(f"총 {len(ads)}개 광고 처리 시작 (이미지 해시 + OCR 처리 중...)")

    for i, ad in enumerate(ads):
        # 광고 문구 처리 (리스트면 합치기)
        ad_text = ad.get("ad_text", "")
        if isinstance(ad_text, list):
            ad_text = "\n".join(ad_text)

        # 광고주명
        page_name = ad.get("page_name", "")

        # URL 리스트 처리
        image_urls = ad.get("image_urls", [])
        image_url = image_urls[0] if image_urls else ""

        # 이미지가 없으면 건너뛰기 (이미지 VIEW 레퍼런스 목적)
        if not image_url:
            no_image += 1
            continue

        # 이미지 다운로드 (한 번만 다운로드하여 해시 + OCR 둘 다 처리)
        image_bytes = download_image(image_url)

        # 이미지 해시 계산
        if image_bytes:
            image_hash = calculate_image_hash(image_bytes)
            # OCR로 이미지 텍스트 추출
            image_text = extract_text_from_image(image_bytes)
        else:
            # 다운로드 실패 시 URL 기반 해시로 대체
            image_hash = hashlib.md5(image_url.encode()).hexdigest()
            image_text = ""
            logger.debug(f"[{i+1}] 이미지 다운로드 실패, URL 해시 사용: {page_name}")

        # 중복 체크: 이미지 해시 기준
        if skip_duplicates and image_hash in existing_hashes:
            skipped += 1
            continue

        # 중복 방지를 위해 현재 배치에도 추가
        existing_hashes.add(image_hash)

        # IMAGE 수식 - Drive URL 우선, 없으면 원본 URL
        if image_hash in drive_url_map and drive_url_map[image_hash]:
            image_cell = f'=IMAGE("{drive_url_map[image_hash]}")'
        else:
            image_cell = f'=IMAGE("{image_url}")'

        video_urls = ad.get("video_urls", [])
        video_url = video_urls[0] if video_urls else ""

        row = [
            collected_at,
            page_name,
            ad_text,
            image_cell,  # =IMAGE() 수식
            image_text,  # OCR 추출 텍스트
            video_url,
            ad.get("ad_snapshot_url", ""),
            image_hash  # 중복 체크용 해시
        ]
        rows.append(row)

    if skipped > 0 or no_image > 0:
        logger.info(f"건너뜀: 중복 이미지 {skipped}개, 이미지 없음 {no_image}개")

    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")  # 수식 실행되도록
        logger.info(f"'{query}' 탭에 {len(rows)}개 행 추가 (신규)")

        # 이미지 셀 크기 조정 (250x250)
        try:
            sheet_id = worksheet.id

            spreadsheet.batch_update({
                "requests": [
                    # C열(광고문구, 인덱스 2) 너비 550
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 2,
                                "endIndex": 3
                            },
                            "properties": {"pixelSize": 550},
                            "fields": "pixelSize"
                        }
                    },
                    # D열(이미지, 인덱스 3) 너비 250
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 3,
                                "endIndex": 4
                            },
                            "properties": {"pixelSize": 250},
                            "fields": "pixelSize"
                        }
                    },
                    # E열(이미지텍스트, 인덱스 4) 너비 550
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 4,
                                "endIndex": 5
                            },
                            "properties": {"pixelSize": 550},
                            "fields": "pixelSize"
                        }
                    },
                    # 데이터 행 높이 250 (헤더 제외)
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "ROWS",
                                "startIndex": 1,  # 2행부터
                                "endIndex": worksheet.row_count
                            },
                            "properties": {"pixelSize": 250},
                            "fields": "pixelSize"
                        }
                    },
                    # F~H열 숨김 (비디오URL, 광고링크, 이미지해시 - 인덱스 5, 6, 7)
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": 5,
                                "endIndex": 8
                            },
                            "properties": {"hiddenByUser": True},
                            "fields": "hiddenByUser"
                        }
                    }
                ]
            })
            logger.info("이미지 셀 크기 조정 완료 (250x250), F~H열 숨김")
        except Exception as e:
            logger.warning(f"셀 크기 조정 실패: {e}")
    else:
        logger.info(f"'{query}' 탭: 추가할 신규 광고 없음")


def write_ocr_text(spreadsheet: gspread.Spreadsheet, ocr_results: list[dict]):
    """
    ocr_text 탭에 OCR 결과 기록

    Args:
        ocr_results: OCR 결과 리스트 [{ad_id, ocr_text, key_claims, offer, cta}, ...]
    """
    headers = [
        "ad_id",
        "image_drive_url",
        "ocr_text",
        "key_claims",
        "offer",
        "cta",
        "notes"
    ]

    worksheet = ensure_worksheet(spreadsheet, "ocr_text", headers)

    rows = []
    for result in ocr_results:
        row = [
            result.get("ad_id", ""),
            result.get("image_url", ""),
            result.get("ocr_text", ""),
            result.get("key_claims", ""),
            result.get("offer", ""),
            result.get("cta", ""),
            result.get("notes", "")
        ]
        rows.append(row)

    if rows:
        worksheet.append_rows(rows)
        logger.info(f"ocr_text에 {len(rows)}개 행 추가")


def write_ideas(spreadsheet: gspread.Spreadsheet, ideas: list[dict]):
    """
    ideas 탭에 아이디어 기록

    Args:
        ideas: 아이디어 리스트
    """
    headers = [
        "week",
        "source_ads",
        "insights",
        "idea_1_title",
        "idea_1_copy",
        "idea_1_visual",
        "idea_2_title",
        "idea_2_copy",
        "idea_2_visual",
        "idea_3_title",
        "idea_3_copy",
        "idea_3_visual"
    ]

    worksheet = ensure_worksheet(spreadsheet, "ideas", headers)

    rows = []
    for idea in ideas:
        row = [
            idea.get("week", ""),
            idea.get("source_ads", ""),
            idea.get("insights", ""),
            idea.get("idea_1_title", ""),
            idea.get("idea_1_copy", ""),
            idea.get("idea_1_visual", ""),
            idea.get("idea_2_title", ""),
            idea.get("idea_2_copy", ""),
            idea.get("idea_2_visual", ""),
            idea.get("idea_3_title", ""),
            idea.get("idea_3_copy", ""),
            idea.get("idea_3_visual", "")
        ]
        rows.append(row)

    if rows:
        worksheet.append_rows(rows)
        logger.info(f"ideas에 {len(rows)}개 행 추가")


def clear_worksheet(spreadsheet: gspread.Spreadsheet, title: str):
    """워크시트 내용 삭제 (헤더 유지)"""
    try:
        worksheet = spreadsheet.worksheet(title)
        # 2행부터 모든 데이터 삭제
        if worksheet.row_count > 1:
            worksheet.delete_rows(2, worksheet.row_count)
            logger.info(f"'{title}' 탭 기존 데이터 삭제 완료")
    except gspread.WorksheetNotFound:
        logger.debug(f"'{title}' 탭이 없습니다. 새로 생성됩니다.")


@click.command()
@click.option("--raw-file", "-f", type=click.Path(exists=True), help="원본 JSON 파일 경로")
@click.option("--latest", "-l", is_flag=True, help="가장 최근 원본 파일 사용")
@click.option("--by-keyword", "-k", is_flag=True, help="키워드별 탭에 기록 (Playwright 스크래핑용)")
@click.option("--clear", "-c", is_flag=True, help="기존 탭 데이터 삭제 후 새로 기록")
def main(raw_file: Optional[str], latest: bool, by_keyword: bool, clear: bool):
    """광고 데이터를 Google Sheets에 기록합니다."""
    ensure_dirs()

    if latest:
        raw_files = sorted(RAW_DIR.glob("*.json"), reverse=True)
        if not raw_files:
            logger.error("원본 데이터 파일이 없습니다.")
            return
        raw_file = raw_files[0]
        logger.info(f"최근 파일 사용: {raw_file}")
    elif not raw_file:
        logger.error("--raw-file 또는 --latest 옵션을 지정하세요.")
        return
    else:
        raw_file = Path(raw_file)

    client = get_sheets_client()
    spreadsheet = client.open_by_key(get_sheet_id())

    # --clear 옵션 시 기존 데이터 삭제
    if clear and by_keyword:
        with open(raw_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        query = data.get("query", "unknown")
        clear_worksheet(spreadsheet, query)

    if by_keyword:
        write_ads_by_keyword(spreadsheet, raw_file)
    else:
        write_ads_raw(spreadsheet, raw_file)
    logger.info("Sheets 기록 완료")


if __name__ == "__main__":
    main()

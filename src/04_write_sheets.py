"""
Google Sheets 기록 모듈
수집된 광고 데이터와 OCR 결과를 스프레드시트에 기록
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import gspread
from google.oauth2 import service_account
from loguru import logger

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
    """워크시트가 없으면 생성하고, 헤더가 없으면 추가"""
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        logger.info(f"워크시트 생성: {title}")

    # 헤더 확인 및 추가
    existing_headers = worksheet.row_values(1) if worksheet.row_count > 0 else []
    if not existing_headers:
        worksheet.append_row(headers)
        logger.debug(f"헤더 추가: {headers}")

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


@click.command()
@click.option("--raw-file", "-f", type=click.Path(exists=True), help="원본 JSON 파일 경로")
@click.option("--latest", "-l", is_flag=True, help="가장 최근 원본 파일 사용")
def main(raw_file: Optional[str], latest: bool):
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

    write_ads_raw(spreadsheet, raw_file)
    logger.info("Sheets 기록 완료")


if __name__ == "__main__":
    main()

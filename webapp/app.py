"""
광고 소재 레퍼런스 갤러리 - Streamlit 웹 앱
Meta 광고 라이브러리에서 수집한 광고 이미지를 타일형 갤러리로 제공
"""

import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def is_cloud_environment():
    """Streamlit Cloud 환경인지 확인"""
    return "gcp_service_account" in st.secrets


def get_credentials():
    """환경에 따라 Google 인증 정보 반환"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    if is_cloud_environment():
        # Streamlit Cloud: secrets에서 인증 정보 로드
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
    else:
        # 로컬: 파일에서 인증 정보 로드
        from src.config import get_google_credentials_path
        credentials = service_account.Credentials.from_service_account_file(
            get_google_credentials_path(),
            scopes=scopes
        )
    return credentials


def get_sheet_id_config():
    """환경에 따라 Sheet ID 반환"""
    if is_cloud_environment():
        return st.secrets["SHEET_ID"]
    else:
        from src.config import get_sheet_id
        return get_sheet_id()

# 페이지 설정
st.set_page_config(
    page_title="광고 소재 레퍼런스",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    /* 메인 컨테이너 */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    /* 사이드바 스타일 */
    .css-1d391kg {
        padding-top: 1rem;
    }

    /* 이미지 카드 스타일 */
    .image-card {
        background: #1e1e1e;
        border-radius: 12px;
        padding: 8px;
        margin-bottom: 16px;
        transition: transform 0.2s;
    }
    .image-card:hover {
        transform: scale(1.02);
    }
    .image-card img {
        border-radius: 8px;
        width: 100%;
    }
    .card-title {
        color: #ffffff;
        font-size: 14px;
        font-weight: 600;
        margin-top: 8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .card-date {
        color: #888888;
        font-size: 12px;
    }

    /* 헤더 스타일 */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    /* 갤러리 그리드 */
    .gallery-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 16px;
    }

    /* 키워드 버튼 */
    .keyword-btn {
        width: 100%;
        text-align: left;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        background: transparent;
        border: none;
        color: #ffffff;
        cursor: pointer;
    }
    .keyword-btn.active {
        background: #4a4a4a;
    }
    .keyword-btn:hover {
        background: #3a3a3a;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_sheets_client():
    """Google Sheets 클라이언트 생성 (캐시됨)"""
    credentials = get_credentials()
    return gspread.authorize(credentials)


@st.cache_data(ttl=300)  # 5분 캐시
def load_keywords():
    """시트의 모든 키워드(탭) 목록 로드"""
    client = get_sheets_client()
    spreadsheet = client.open_by_key(get_sheet_id_config())

    # 시스템 시트 제외하고 키워드 탭만 반환
    system_sheets = ["raw_data", "ocr_results", "ideas", "설정"]
    keywords = [ws.title for ws in spreadsheet.worksheets()
                if ws.title not in system_sheets]
    return keywords


@st.cache_data(ttl=300)  # 5분 캐시
def load_ads_data(keyword: str):
    """특정 키워드의 광고 데이터 로드"""
    client = get_sheets_client()
    spreadsheet = client.open_by_key(get_sheet_id_config())

    try:
        worksheet = spreadsheet.worksheet(keyword)
        records = worksheet.get_all_records()
        return records
    except gspread.exceptions.WorksheetNotFound:
        return []


def parse_date(date_str: str):
    """날짜 문자열 파싱"""
    if not date_str:
        return None
    try:
        # 여러 형식 시도
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"]:
            try:
                return datetime.strptime(date_str.split(".")[0], fmt)
            except ValueError:
                continue
        return None
    except:
        return None


def extract_image_url(image_formula: str) -> str:
    """=IMAGE("url") 수식에서 URL 추출"""
    if not image_formula:
        return ""
    if image_formula.startswith('=IMAGE("') and image_formula.endswith('")'):
        return image_formula[8:-2]
    return image_formula


def render_gallery(ads: list, columns: int = 4):
    """타일형 갤러리 렌더링"""
    if not ads:
        st.info("해당 조건에 맞는 광고가 없습니다.")
        return

    # 컬럼 생성
    cols = st.columns(columns)

    for idx, ad in enumerate(ads):
        col = cols[idx % columns]

        with col:
            # 이미지 URL 추출
            image_url = extract_image_url(ad.get("이미지", ""))
            page_name = ad.get("광고주", "Unknown")
            ad_text = ad.get("광고 문구", "")[:100]
            collected_at = ad.get("수집일", "")

            if image_url:
                # 카드 컨테이너
                with st.container():
                    # 이미지
                    st.image(image_url, use_container_width=True)

                    # 광고주명
                    st.markdown(f"**{page_name}**")

                    # 수집일
                    if collected_at:
                        st.caption(f"📅 {collected_at[:10]}")

                    # 광고 문구 (확장 가능)
                    if ad_text:
                        with st.expander("광고 문구"):
                            st.write(ad_text)

                    st.divider()


def main():
    # ========== 사이드바 ==========
    with st.sidebar:
        st.title("🎨 광고 레퍼런스")
        st.caption("Meta 광고 라이브러리 수집")

        st.divider()

        # 키워드 목록 로드
        keywords = load_keywords()

        if not keywords:
            st.warning("등록된 키워드가 없습니다.")
            st.stop()

        # 키워드 선택
        st.subheader("📁 키워드")
        selected_keyword = st.radio(
            "트래킹 키워드 선택",
            keywords,
            label_visibility="collapsed"
        )

        st.divider()

        # 키워드 추가 (향후 기능)
        with st.expander("➕ 새 키워드 추가"):
            new_keyword = st.text_input("키워드 입력")
            if st.button("추가", use_container_width=True):
                st.info("키워드 추가 기능은 준비 중입니다.")

        st.divider()

        # 정보
        st.caption("© 2026 광고 소재 레퍼런스")

    # ========== 메인 영역 ==========

    # 상단 헤더
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.header(f"📌 {selected_keyword}")

    with col2:
        # 날짜 범위 필터
        date_range = st.date_input(
            "날짜 범위",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            format="YYYY-MM-DD"
        )

    with col3:
        # 컬럼 수 조절
        columns = st.selectbox("컬럼", [3, 4, 5, 6], index=1)

    st.divider()

    # 데이터 로드
    with st.spinner("광고 데이터 로딩 중..."):
        ads_data = load_ads_data(selected_keyword)

    # 날짜 필터 적용
    if ads_data and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_ads = []

        for ad in ads_data:
            ad_date = parse_date(ad.get("수집일", ""))
            if ad_date:
                ad_date_only = ad_date.date()
                if start_date <= ad_date_only <= end_date:
                    filtered_ads.append(ad)
            else:
                # 날짜 파싱 실패 시 포함
                filtered_ads.append(ad)

        ads_data = filtered_ads

    # 통계 표시
    st.caption(f"총 {len(ads_data)}개 광고")

    # 갤러리 렌더링
    render_gallery(ads_data, columns=columns)


if __name__ == "__main__":
    main()

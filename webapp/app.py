"""
광고 소재 레퍼런스 갤러리 - Streamlit 웹 앱
Meta 광고 라이브러리에서 수집한 광고 이미지를 타일형 갤러리로 제공
데이터 소스: data/raw/*.json (직접 로드)
"""

import streamlit as st
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"

# 페이지 설정
st.set_page_config(
    page_title="광고 소재 레퍼런스",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 - 흑백 모노톤 + 글래스모피즘 + 직각 디자인 + 얇은 폰트
st.markdown("""
<style>
    /* ===== Google Fonts - 얇은 폰트 ===== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* ===== 전체 배경 - 화이트 ===== */
    .stApp {
        background: #fafafa;
    }

    /* ===== 메인 컨테이너 ===== */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
        background: #ffffff;
    }

    /* ===== 메인 영역 텍스트 색상 (흰 배경용) ===== */
    .main .stMarkdown,
    .main .stMarkdown p,
    .main .stMarkdown span,
    .main label,
    .main .stTextInput label,
    .main .stSelectbox label,
    .main .stDateInput label,
    .main .stRadio label,
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
        color: #1a1a1a !important;
        font-weight: 300 !important;
    }

    /* ===== 사이드바 - 글래스모피즘 (흑백) ===== */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(0, 0, 0, 0.1) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
    }

    /* ===== 사이드바 텍스트 - 블랙 ===== */
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #1a1a1a !important;
        font-weight: 300 !important;
    }

    [data-testid="stSidebar"] .stCaption {
        color: rgba(0, 0, 0, 0.5) !important;
        font-weight: 200 !important;
    }

    /* ===== 사이드바 라디오 버튼 ===== */
    [data-testid="stSidebar"] .stRadio > div {
        background: rgba(0, 0, 0, 0.03);
        border-radius: 0;
        padding: 10px;
        border: 1px solid rgba(0, 0, 0, 0.08);
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(0, 0, 0, 0.1) !important;
    }

    /* ===== 이미지 카드 - 심플 스타일 ===== */
    .ad-card {
        background: #ffffff;
        border-radius: 8px;
        padding: 12px;
        padding-bottom: 0;
        margin-bottom: 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(0, 0, 0, 0.06);
        border-bottom: none;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }

    .ad-card img {
        border-radius: 4px;
        width: 100%;
        aspect-ratio: 1;
        object-fit: cover;
        display: block;
    }

    /* 카드 정보 영역 */
    .card-info {
        padding: 12px 2px 10px 2px;
    }

    .card-info .card-title {
        color: #1a1a1a;
        font-size: 13px;
        font-weight: 500;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .card-info .card-date {
        color: #999;
        font-size: 12px;
        font-weight: 400;
        margin-top: 2px;
        margin-bottom: 0;
    }

    /* 카드 구분선 */
    .card-divider {
        height: 1px;
        background: #e5e5e5;
        margin: 0 -12px;
    }

    /* ===== Date Input 스타일 (직각 + 글래스) ===== */
    .stDateInput {
        position: relative;
    }

    .stDateInput label {
        color: #1a1a1a !important;
        font-weight: 300 !important;
        font-size: 13px !important;
        margin-bottom: 8px !important;
        letter-spacing: 0.02em !important;
    }

    .stDateInput > div > div {
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 0 !important;
        padding: 4px 12px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    }

    .stDateInput > div > div:hover {
        border-color: rgba(0, 0, 0, 0.3) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }

    .stDateInput > div > div:focus-within {
        border-color: #1a1a1a !important;
        box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1) !important;
    }

    .stDateInput input {
        color: #1a1a1a !important;
        font-size: 13px !important;
        font-weight: 300 !important;
        letter-spacing: 0.02em !important;
    }

    .stDateInput svg {
        color: #1a1a1a !important;
    }

    /* ===== SelectBox 스타일 (직각 + 글래스) ===== */
    .stSelectbox label {
        color: #1a1a1a !important;
        font-weight: 300 !important;
        font-size: 13px !important;
        margin-bottom: 8px !important;
        letter-spacing: 0.02em !important;
    }

    .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 0 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    }

    .stSelectbox > div > div:hover {
        border-color: rgba(0, 0, 0, 0.3) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }

    .stSelectbox > div > div > div {
        color: #1a1a1a !important;
        font-weight: 300 !important;
    }

    .stSelectbox svg {
        color: #1a1a1a !important;
    }

    /* ===== SelectBox 드롭다운 메뉴 (흰색 + 직각) ===== */
    [data-baseweb="popover"] {
        background: rgba(255, 255, 255, 0.98) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 0 !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.12) !important;
    }

    [data-baseweb="popover"] li {
        color: #1a1a1a !important;
        font-weight: 300 !important;
    }

    [data-baseweb="popover"] li:hover {
        background: rgba(0, 0, 0, 0.05) !important;
    }

    /* ===== 헤더 (흑백 + 직각 + 글래스) ===== */
    .header-section {
        background: rgba(26, 26, 26, 0.95);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 0;
        padding: 28px 36px;
        margin-bottom: 28px;
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .header-section h1 {
        color: white !important;
        margin: 0;
        font-size: 24px;
        font-weight: 300 !important;
        letter-spacing: 0.05em;
    }

    .header-section p {
        color: rgba(255, 255, 255, 0.6);
        margin: 8px 0 0 0;
        font-weight: 200;
        letter-spacing: 0.03em;
    }

    /* ===== 통계 카드 (글래스 + 직각) ===== */
    .stat-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 0;
        padding: 20px 24px;
        text-align: center;
        border: 1px solid rgba(0, 0, 0, 0.08);
    }

    .stat-number {
        font-size: 32px;
        font-weight: 300;
        color: #1a1a1a;
        letter-spacing: 0.02em;
    }

    .stat-label {
        font-size: 12px;
        font-weight: 300;
        color: #888;
        margin-top: 4px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* ===== 모달/다이얼로그 스타일 (흰색 + 직각) ===== */
    [data-testid="stModal"] {
        background: rgba(255, 255, 255, 0.6) !important;
        backdrop-filter: blur(8px) !important;
    }

    [data-testid="stModal"] > div {
        background: #ffffff !important;
        border-radius: 0 !important;
        padding: 0 !important;
        max-width: 800px !important;
        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.12) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
    }

    [data-testid="stModal"] > div > div {
        background: #ffffff !important;
    }

    [data-testid="stModal"] h1,
    [data-testid="stModal"] h2,
    [data-testid="stModal"] h3,
    [data-testid="stModal"] p,
    [data-testid="stModal"] span,
    [data-testid="stModal"] label {
        color: #1a1a1a !important;
        font-weight: 300 !important;
    }

    /* ===== 모달 내부 닫기 버튼 (흰색 + 직각) ===== */
    [data-testid="stModal"] button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.9) !important;
        color: #1a1a1a !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 0 !important;
        font-weight: 300 !important;
    }

    /* ===== 모달 헤더 (흰색 + 직각) ===== */
    .modal-header {
        background: #ffffff;
        padding: 24px 28px;
        border-radius: 0;
        margin-bottom: 24px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    }

    .modal-header h3 {
        color: #1a1a1a !important;
        margin: 0;
        font-size: 15px;
        font-weight: 400 !important;
        letter-spacing: 0.03em;
    }

    .modal-header p {
        color: #666 !important;
        margin: 4px 0 0 0;
        font-size: 11px;
        font-weight: 300 !important;
    }

    /* ===== 모달 섹션 (흰색 + 직각) ===== */
    .modal-section {
        background: #ffffff;
        border-radius: 0;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(0, 0, 0, 0.08);
    }

    .modal-section-title {
        font-size: 10px;
        font-weight: 400;
        color: #1a1a1a;
        margin-bottom: 8px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .modal-section-content {
        color: #1a1a1a;
        font-size: 11px;
        font-weight: 300;
        line-height: 1.7;
    }

    /* ===== 갤러리 카드 버튼 (테스트용 빨간색) ===== */
    /* 테스트: CSS 적용 여부 확인 */
    [data-testid="column"] button,
    [data-testid="column"] [data-testid="baseButton-secondary"],
    .stMainBlockContainer button {
        background: #ff0000 !important;
        background-color: #ff0000 !important;
        color: #ffffff !important;
        border: 3px solid #ff0000 !important;
    }

    [data-testid="column"] button p,
    .stMainBlockContainer button p {
        color: #ffffff !important;
    }

    /* ===== 사이드바 Refresh 버튼 (별도 스타일) ===== */
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        background-color: transparent !important;
        color: #888 !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-weight: 300 !important;
        font-size: 12px !important;
        letter-spacing: 0.03em !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        width: 100% !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(0, 0, 0, 0.03) !important;
        color: #555 !important;
        border-color: rgba(0, 0, 0, 0.2) !important;
    }

    [data-testid="stSidebar"] .stButton > button::before,
    [data-testid="stSidebar"] .stButton > button::after {
        display: none !important;
    }

    /* ===== 캡션 텍스트 색상 ===== */
    .main .stCaption,
    .main [data-testid="stCaptionContainer"] {
        color: #888 !important;
        font-weight: 300 !important;
    }

    /* ===== Info/Success/Warning 박스 텍스트 ===== */
    .stAlert {
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 0 !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
    }

    .stAlert p {
        color: #1a1a1a !important;
        font-weight: 300 !important;
    }

    /* ===== divider 스타일 ===== */
    .main hr {
        border-color: rgba(0, 0, 0, 0.08) !important;
    }

    /* ===== 달력 팝업 스타일 (직각 + 흰색) ===== */
    [data-baseweb="calendar"] {
        background: rgba(255, 255, 255, 0.98) !important;
        border-radius: 0 !important;
    }

    [data-baseweb="calendar"] button {
        border-radius: 0 !important;
    }

    /* ===== 스크롤바 스타일 ===== */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: transparent;
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 0;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 0, 0, 0.3);
    }

    /* ===== 멀티셀렉트 태그 스타일 ===== */
    .stMultiSelect {
        margin-top: 8px;
    }

    .stMultiSelect label {
        color: #1a1a1a !important;
        font-weight: 300 !important;
        font-size: 13px !important;
        letter-spacing: 0.02em !important;
    }

    .stMultiSelect > div > div {
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 0 !important;
        min-height: 42px !important;
        padding: 4px 8px !important;
    }

    .stMultiSelect > div > div:hover {
        border-color: rgba(0, 0, 0, 0.3) !important;
    }

    .stMultiSelect > div > div:focus-within {
        border-color: #1a1a1a !important;
        box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1) !important;
    }

    /* 선택된 태그 스타일 (흰색 배경 + 검은 글씨) */
    .stMultiSelect [data-baseweb="tag"] {
        background: #ffffff !important;
        border-radius: 0 !important;
        border: 1px solid rgba(0, 0, 0, 0.15) !important;
        padding: 4px 10px !important;
        margin: 2px !important;
        font-weight: 300 !important;
        font-size: 11px !important;
        letter-spacing: 0.03em !important;
    }

    .stMultiSelect [data-baseweb="tag"] span {
        color: #1a1a1a !important;
    }

    .stMultiSelect [data-baseweb="tag"] svg {
        color: rgba(0, 0, 0, 0.4) !important;
    }

    .stMultiSelect [data-baseweb="tag"]:hover svg {
        color: #1a1a1a !important;
    }

    /* 드롭다운 메뉴 (흰색 배경) */
    .stMultiSelect [data-baseweb="popover"],
    .stMultiSelect [data-baseweb="menu"] {
        background: #ffffff !important;
        border-radius: 0 !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
    }

    .stMultiSelect [data-baseweb="popover"] li,
    .stMultiSelect [data-baseweb="menu"] li {
        color: #1a1a1a !important;
        font-weight: 300 !important;
        font-size: 11px !important;
        background: #ffffff !important;
    }

    .stMultiSelect [data-baseweb="popover"] li:hover,
    .stMultiSelect [data-baseweb="menu"] li:hover {
        background: rgba(0, 0, 0, 0.03) !important;
    }

    /* placeholder 텍스트 */
    .stMultiSelect input::placeholder {
        color: #888 !important;
        font-weight: 300 !important;
        font-size: 11px !important;
    }

    .stMultiSelect input {
        font-size: 11px !important;
        color: #1a1a1a !important;
    }

    /* ===== 필터 라벨 통일 (날짜, 광고주 동일 크기) ===== */
    .filter-label {
        font-size: 11px;
        font-weight: 400;
        color: #1a1a1a;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_all_json_data():
    """모든 JSON 파일에서 광고 데이터 로드"""
    all_ads = {}  # keyword -> list of ads

    if not DATA_RAW_DIR.exists():
        return all_ads

    for json_file in DATA_RAW_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            query = data.get("query", "unknown")
            collected_at = data.get("collected_at", "")
            ads = data.get("ads", [])

            if query not in all_ads:
                all_ads[query] = []

            for ad in ads:
                ad["_collected_at"] = collected_at
                ad["_source_file"] = json_file.name
                all_ads[query].append(ad)

        except Exception as e:
            st.warning(f"파일 로드 실패: {json_file.name} - {e}")

    # 각 키워드별로 중복 제거 (image_urls 기준)
    for keyword in all_ads:
        seen_urls = set()
        unique_ads = []
        for ad in all_ads[keyword]:
            image_urls = ad.get("image_urls", [])
            if image_urls:
                url = image_urls[0]
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_ads.append(ad)
        all_ads[keyword] = unique_ads

    return all_ads


def get_keywords():
    """키워드 목록 반환"""
    data = load_all_json_data()
    return list(data.keys())


def get_ads_by_keyword(keyword: str):
    """특정 키워드의 광고 목록 반환"""
    data = load_all_json_data()
    return data.get(keyword, [])


def parse_date(date_str: str):
    """날짜 문자열 파싱"""
    if not date_str:
        return None
    try:
        # ISO 형식
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except:
            return None


def is_valid_ad_image(image_url: str, min_size: int = 200) -> bool:
    """
    광고 소재 이미지인지 판단 (프로필 이미지 제외)
    Meta CDN URL에서 크기 정보 추출하여 필터링
    """
    if not image_url:
        return False

    # URL에서 크기 정보 추출 (예: s600x600, p200x200 등)
    size_patterns = [
        r'_s(\d+)x(\d+)',  # _s600x600
        r's(\d+)x(\d+)',   # s600x600
        r'p(\d+)x(\d+)',   # p200x200
        r'(\d+)x(\d+)',    # 일반 크기
    ]

    for pattern in size_patterns:
        match = re.search(pattern, image_url)
        if match:
            width = int(match.group(1))
            height = int(match.group(2)) if match.lastindex >= 2 else width
            # 작은 이미지는 프로필/썸네일로 판단
            if width < min_size or height < min_size:
                return False
            return True

    # 크기 정보가 없으면 일단 포함 (보수적 접근)
    return True


@st.dialog("Ad Detail", width="large")
def show_ad_detail(ad: dict):
    """광고 상세 모달 (팝업) 렌더링"""
    image_urls = ad.get("image_urls", [])
    image_url = image_urls[0] if image_urls else ""
    page_name = ad.get("page_name", "Unknown")
    ad_text = ad.get("ad_text", [])
    if isinstance(ad_text, list):
        ad_text = "\n".join(ad_text)

    # OCR 텍스트 (시트에서 가져온 경우)
    ocr_text = ad.get("ocr_text", ad.get("이미지텍스트", ""))

    # 모달 헤더
    st.markdown(f"""
    <div class="modal-header">
        <h3>{page_name}</h3>
        <p>{ad.get('_collected_at', '')[:10]}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        if image_url:
            st.image(image_url, width="stretch")

    with col2:
        # 광고 문구
        st.markdown("""
        <div class="modal-section">
            <div class="modal-section-title">Ad Copy</div>
        </div>
        """, unsafe_allow_html=True)
        if ad_text:
            st.markdown(f"""
            <div class="modal-section-content" style="background: #ffffff; padding: 12px; border-radius: 0; margin-top: -12px; border: 1px solid rgba(0,0,0,0.08);">
                {ad_text}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("No ad copy")

        st.markdown("<br>", unsafe_allow_html=True)

        # OCR 텍스트
        st.markdown("""
        <div class="modal-section">
            <div class="modal-section-title">Image Text (OCR)</div>
        </div>
        """, unsafe_allow_html=True)
        if ocr_text:
            st.markdown(f"""
            <div class="modal-section-content" style="background: #ffffff; padding: 12px; border-radius: 0; margin-top: -12px; border: 1px solid rgba(0,0,0,0.08);">
                {ocr_text}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("No OCR text")


def render_gallery(ads: list, columns: int = 6):
    """타일형 갤러리 렌더링"""
    if not ads:
        st.info("No ads matching the criteria.")
        return

    # 유효한 광고 이미지만 필터링 (프로필 이미지 제외)
    valid_ads = []
    for ad in ads:
        image_urls = ad.get("image_urls", [])
        if image_urls:
            # 유효한 크기의 이미지 URL 찾기
            valid_url = None
            for url in image_urls:
                if is_valid_ad_image(url, min_size=200):
                    valid_url = url
                    break
            if valid_url:
                ad["_valid_image_url"] = valid_url
                valid_ads.append(ad)

    if not valid_ads:
        st.info("No ads matching the criteria.")
        return

    cols = st.columns(columns)

    for idx, ad in enumerate(valid_ads):
        col = cols[idx % columns]

        with col:
            image_url = ad.get("_valid_image_url", "")
            page_name = ad.get("page_name", "Unknown")
            collected_at = ad.get("_collected_at", "")[:10]

            if image_url:
                # 카드 렌더링 (이미지 + 정보 + 구분선)
                st.markdown(f"""
                <div class="ad-card">
                    <img src="{image_url}" alt="{page_name}" loading="lazy"
                         onerror="this.src='https://via.placeholder.com/300?text=No+Image'">
                    <div class="card-info">
                        <div class="card-title">{page_name}</div>
                        <div class="card-date">{collected_at}</div>
                    </div>
                    <div class="card-divider"></div>
                </div>
                """, unsafe_allow_html=True)

                # 하단 전체 너비 버튼
                if st.button("description", key=f"detail_{idx}"):
                    show_ad_detail(ad)


def main():
    # ========== 사이드바 ==========
    with st.sidebar:
        st.markdown("# Ad Reference")
        st.caption("Meta Ad Library Collection")

        st.divider()

        keywords = get_keywords()

        if not keywords:
            st.warning("No data collected.")
            st.info("Run the pipeline first:\n`python -m src.07_run_weekly --query 'keyword'`")
            st.stop()

        st.markdown("### Keywords")
        selected_keyword = st.radio(
            "Select keyword",
            keywords,
            label_visibility="collapsed"
        )

        st.divider()

        # 새로고침 버튼 (아이콘 포함)
        if st.button("↻  Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.caption("© 2026 Ad Reference Gallery")

    # ========== 메인 영역 ==========

    # 헤더
    st.markdown(f"""
    <div class="header-section">
        <h1>{selected_keyword}</h1>
        <p>Ad creatives from Meta Ad Library</p>
    </div>
    """, unsafe_allow_html=True)

    # 데이터 로드 (필터 전)
    ads_data = get_ads_by_keyword(selected_keyword)

    # 날짜 필터 라벨
    st.markdown('<div class="filter-label">Date Range</div>', unsafe_allow_html=True)
    date_range = st.date_input(
        "Date Range",
        value=(datetime.now() - timedelta(days=30), datetime.now()),
        format="YYYY-MM-DD",
        label_visibility="collapsed"
    )

    # 날짜 필터 먼저 적용하여 해당 기간의 광고만 추출
    date_filtered_ads = ads_data
    if ads_data and len(date_range) == 2:
        start_date, end_date = date_range
        date_filtered_ads = []

        for ad in ads_data:
            ad_date = parse_date(ad.get("_collected_at", ""))
            if ad_date:
                ad_date_only = ad_date.date()
                if start_date <= ad_date_only <= end_date:
                    date_filtered_ads.append(ad)
            else:
                date_filtered_ads.append(ad)

    # 날짜 필터링된 데이터에서 광고주 목록 추출 (ㄱㄴㄷ 순 정렬)
    available_advertisers = sorted(set(ad.get("page_name", "") for ad in date_filtered_ads if ad.get("page_name")))

    # 광고주 라벨
    st.markdown('<div class="filter-label">Advertiser</div>', unsafe_allow_html=True)

    # 멀티셀렉트로 여러 광고주 선택 가능
    selected_advertisers = st.multiselect(
        "Select advertisers",
        options=available_advertisers,
        default=[],
        placeholder="Click to select (all if none)",
        label_visibility="collapsed"
    )

    # 고정 컬럼 수
    columns = 6

    # 최종 필터링된 데이터
    ads_data = date_filtered_ads

    # 광고주 필터 적용 (선택된 광고주가 있을 때만)
    if selected_advertisers:
        ads_data = [ad for ad in ads_data if ad.get("page_name") in selected_advertisers]

    # 최신 순 정렬
    ads_data = sorted(ads_data, key=lambda x: parse_date(x.get("_collected_at", "")) or datetime.min, reverse=True)

    # 통계
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(ads_data)}</div>
            <div class="stat-label">Total Ads</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        unique_advertisers = len(set(ad.get("page_name", "") for ad in ads_data))
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{unique_advertisers}</div>
            <div class="stat-label">Advertisers</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # 갤러리 렌더링
    render_gallery(ads_data, columns=columns)


if __name__ == "__main__":
    main()

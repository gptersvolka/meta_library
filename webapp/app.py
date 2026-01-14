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
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"

# 페이지 설정
st.set_page_config(
    page_title="광고 소재 레퍼런스",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 - 사이드바 컬러, 메인 화이트
st.markdown("""
<style>
    /* 전체 배경 - 화이트 */
    .stApp {
        background: #f8f9fa;
    }

    /* 메인 컨테이너 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
        background: #ffffff;
    }

    /* 사이드바 - 그라데이션 컬러 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
    }

    /* 사이드바 텍스트 - 화이트 */
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: white !important;
    }

    [data-testid="stSidebar"] .stCaption {
        color: rgba(255,255,255,0.7) !important;
    }

    /* 사이드바 라디오 버튼 */
    [data-testid="stSidebar"] .stRadio > div {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 10px;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2) !important;
    }

    /* 이미지 카드 - 화이트 톤 */
    .ad-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 16px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        border: 1px solid #eee;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        cursor: pointer;
    }

    .ad-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
    }

    .ad-card img {
        border-radius: 12px;
        width: 100%;
        aspect-ratio: 1;
        object-fit: cover;
    }

    .card-title {
        color: #1a1a2e;
        font-size: 14px;
        font-weight: 600;
        margin-top: 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .card-date {
        color: #888;
        font-size: 12px;
        margin-top: 4px;
    }

    /* 헤더 */
    .header-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        color: white;
    }

    .header-section h1 {
        color: white !important;
        margin: 0;
        font-size: 28px;
    }

    .header-section p {
        color: rgba(255,255,255,0.8);
        margin: 8px 0 0 0;
    }

    /* 통계 카드 */
    .stat-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }

    .stat-number {
        font-size: 28px;
        font-weight: 700;
        color: #667eea;
    }

    .stat-label {
        font-size: 13px;
        color: #666;
        margin-top: 4px;
    }

    /* 모달/다이얼로그 스타일 */
    .modal-content {
        background: white;
        border-radius: 16px;
        padding: 24px;
        max-height: 80vh;
        overflow-y: auto;
    }

    .modal-image {
        width: 100%;
        border-radius: 12px;
        margin-bottom: 16px;
    }

    .modal-title {
        font-size: 20px;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 16px;
    }

    .modal-section {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .modal-section-title {
        font-size: 14px;
        font-weight: 600;
        color: #667eea;
        margin-bottom: 8px;
    }

    /* Streamlit 기본 요소 */
    .stSelectbox > div > div,
    .stDateInput > div > div {
        background: white !important;
        border: 1px solid #ddd !important;
        border-radius: 10px !important;
    }

    /* 버튼 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 8px 20px !important;
    }

    .stButton > button:hover {
        opacity: 0.9 !important;
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


def render_ad_modal(ad: dict):
    """광고 상세 모달 렌더링"""
    image_urls = ad.get("image_urls", [])
    image_url = image_urls[0] if image_urls else ""
    page_name = ad.get("page_name", "Unknown")
    ad_text = ad.get("ad_text", [])
    if isinstance(ad_text, list):
        ad_text = "\n".join(ad_text)

    # OCR 텍스트 (시트에서 가져온 경우)
    ocr_text = ad.get("ocr_text", ad.get("이미지텍스트", ""))

    col1, col2 = st.columns([1, 1])

    with col1:
        if image_url:
            st.image(image_url, use_container_width=True)

    with col2:
        st.markdown(f"### {page_name}")
        st.caption(f"📅 {ad.get('_collected_at', '')[:10]}")

        st.markdown("---")

        # 광고 문구
        st.markdown("**📝 광고 문구**")
        if ad_text:
            st.info(ad_text)
        else:
            st.caption("광고 문구 없음")

        # OCR 텍스트
        st.markdown("**🔍 이미지 텍스트 (OCR)**")
        if ocr_text:
            st.success(ocr_text)
        else:
            st.caption("OCR 텍스트 없음")


def render_gallery(ads: list, columns: int = 6):
    """타일형 갤러리 렌더링"""
    if not ads:
        st.info("📭 해당 조건에 맞는 광고가 없습니다.")
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
        st.info("📭 해당 조건에 맞는 광고가 없습니다.")
        return

    cols = st.columns(columns)

    for idx, ad in enumerate(valid_ads):
        col = cols[idx % columns]

        with col:
            image_url = ad.get("_valid_image_url", "")
            page_name = ad.get("page_name", "Unknown")
            collected_at = ad.get("_collected_at", "")[:10]

            if image_url:
                # 카드 렌더링
                st.markdown(f"""
                <div class="ad-card">
                    <img src="{image_url}" alt="{page_name}" loading="lazy"
                         onerror="this.src='https://via.placeholder.com/300?text=No+Image'">
                    <div class="card-title">{page_name}</div>
                    <div class="card-date">광고 집행 일 {collected_at}</div>
                </div>
                """, unsafe_allow_html=True)

                # 상세 보기 버튼
                if st.button("상세 보기", key=f"detail_{idx}", use_container_width=True):
                    st.session_state.selected_ad = ad
                    st.session_state.show_modal = True


def main():
    # 세션 상태 초기화
    if "show_modal" not in st.session_state:
        st.session_state.show_modal = False
    if "selected_ad" not in st.session_state:
        st.session_state.selected_ad = None

    # ========== 사이드바 ==========
    with st.sidebar:
        st.markdown("# 🎨 광고 레퍼런스")
        st.caption("Meta 광고 라이브러리 수집")

        st.divider()

        keywords = get_keywords()

        if not keywords:
            st.warning("수집된 데이터가 없습니다.")
            st.info("먼저 파이프라인을 실행하세요:\n`python -m src.07_run_weekly --query '키워드'`")
            st.stop()

        st.markdown("### 📁 키워드")
        selected_keyword = st.radio(
            "트래킹 키워드 선택",
            keywords,
            label_visibility="collapsed"
        )

        st.divider()

        # 새로고침 버튼
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption("© 2026 Ad Reference Gallery")

    # ========== 모달 (상세 보기) ==========
    if st.session_state.show_modal and st.session_state.selected_ad:
        with st.container():
            col1, col2, col3 = st.columns([1, 6, 1])
            with col2:
                st.markdown("---")
                st.markdown("### 📋 광고 상세 정보")

                render_ad_modal(st.session_state.selected_ad)

                if st.button("✕ 닫기", use_container_width=True):
                    st.session_state.show_modal = False
                    st.session_state.selected_ad = None
                    st.rerun()

                st.markdown("---")

    # ========== 메인 영역 ==========

    # 헤더
    st.markdown(f"""
    <div class="header-section">
        <h1>📌 {selected_keyword}</h1>
        <p>Meta 광고 라이브러리에서 수집한 광고 소재</p>
    </div>
    """, unsafe_allow_html=True)

    # 필터 영역
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

    with col1:
        date_range = st.date_input(
            "📅 날짜 범위",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            format="YYYY-MM-DD"
        )

    with col3:
        columns = st.selectbox("컬럼 수", [4, 5, 6, 7, 8], index=2)

    # 데이터 로드
    ads_data = get_ads_by_keyword(selected_keyword)

    # 날짜 필터 적용
    if ads_data and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_ads = []

        for ad in ads_data:
            ad_date = parse_date(ad.get("_collected_at", ""))
            if ad_date:
                ad_date_only = ad_date.date()
                if start_date <= ad_date_only <= end_date:
                    filtered_ads.append(ad)
            else:
                filtered_ads.append(ad)

        ads_data = filtered_ads

    # 통계
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(ads_data)}</div>
            <div class="stat-label">총 광고 수</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        unique_advertisers = len(set(ad.get("page_name", "") for ad in ads_data))
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{unique_advertisers}</div>
            <div class="stat-label">광고주 수</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # 갤러리 렌더링
    render_gallery(ads_data, columns=columns)


if __name__ == "__main__":
    main()

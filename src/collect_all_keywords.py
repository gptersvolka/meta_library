"""
Supabase에서 키워드를 읽어 모든 키워드에 대해 수집 실행
(GitHub Actions용 - 공백이 포함된 키워드 지원)
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def get_keywords_from_supabase():
    """Supabase에서 활성화된 키워드 목록 가져오기"""
    try:
        import requests

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase 환경변수 미설정")
            return []

        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }

        response = requests.get(
            f"{url}/rest/v1/keywords?enabled=eq.true&select=query",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            keywords = [item["query"] for item in data]
            logger.info(f"Supabase에서 {len(keywords)}개 키워드 로드: {keywords}")
            return keywords
        else:
            logger.error(f"Supabase API 오류: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"키워드 로드 실패: {e}")
        return []


def main():
    """모든 키워드에 대해 수집 실행"""
    import importlib
    weekly_module = importlib.import_module("src.07_run_weekly")
    run_full_pipeline = weekly_module.run_full_pipeline

    # 수동 입력 키워드 확인
    manual_query = os.getenv("MANUAL_QUERY", "").strip()

    if manual_query:
        keywords = [manual_query]
        logger.info(f"수동 입력 키워드: {manual_query}")
    else:
        keywords = get_keywords_from_supabase()

    if not keywords:
        logger.warning("수집할 키워드가 없습니다.")
        return

    logger.info("=" * 60)
    logger.info(f"전체 수집 시작: {datetime.now().isoformat()}")
    logger.info(f"대상 키워드 {len(keywords)}개: {keywords}")
    logger.info("=" * 60)

    results = []

    for i, keyword in enumerate(keywords, 1):
        logger.info(f"\n[{i}/{len(keywords)}] '{keyword}' 수집 시작...")

        try:
            result = run_full_pipeline(
                query=keyword,
                country="KR",
                limit=50,
                headless=True,
                image_only=True,
                skip_upload=False
            )
            results.append({"keyword": keyword, "success": bool(result)})
            logger.info(f"[{i}/{len(keywords)}] '{keyword}' 완료")
        except Exception as e:
            logger.error(f"[{i}/{len(keywords)}] '{keyword}' 실패: {e}")
            results.append({"keyword": keyword, "success": False, "error": str(e)})

    # 결과 요약
    success_count = sum(1 for r in results if r.get("success"))
    fail_count = len(results) - success_count

    logger.info("\n" + "=" * 60)
    logger.info(f"전체 수집 완료: {datetime.now().isoformat()}")
    logger.info(f"성공: {success_count}개, 실패: {fail_count}개")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

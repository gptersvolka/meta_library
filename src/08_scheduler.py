"""
자동 수집 스케줄러
등록된 키워드들을 매일 지정 시간에 자동 수집
"""

import json
import importlib
import schedule
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.config import PROJECT_ROOT, setup_logging

# 숫자로 시작하는 모듈명은 importlib으로 로드
_weekly_module = importlib.import_module("src.07_run_weekly")
run_full_pipeline = _weekly_module.run_full_pipeline


KEYWORDS_FILE = PROJECT_ROOT / "data" / "keywords.json"


def load_keywords():
    """키워드 설정 파일 로드"""
    if not KEYWORDS_FILE.exists():
        logger.warning(f"키워드 파일이 없습니다: {KEYWORDS_FILE}")
        return {"keywords": [], "schedule": {"time": "09:00"}}

    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_keywords(data):
    """키워드 설정 파일 저장"""
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_keyword(query: str, country: str = "KR", limit: int = 50):
    """새 키워드 추가"""
    data = load_keywords()

    # 중복 체크
    for kw in data["keywords"]:
        if kw["query"] == query:
            logger.info(f"이미 등록된 키워드: {query}")
            return False

    data["keywords"].append({
        "query": query,
        "country": country,
        "limit": limit,
        "enabled": True
    })
    save_keywords(data)
    logger.info(f"키워드 추가됨: {query}")
    return True


def remove_keyword(query: str):
    """키워드 제거"""
    data = load_keywords()
    data["keywords"] = [kw for kw in data["keywords"] if kw["query"] != query]
    save_keywords(data)
    logger.info(f"키워드 제거됨: {query}")


def list_keywords():
    """등록된 키워드 목록 반환"""
    data = load_keywords()
    return data.get("keywords", [])


def count_today_images() -> int:
    """오늘 수집된 이미지 개수 카운트"""
    from src.config import IMAGES_DIR
    today_str = datetime.now().strftime("%Y%m%d")
    count = 0
    for img_file in IMAGES_DIR.glob(f"{today_str}_*.png"):
        count += 1
    return count


def run_scheduled_collection():
    """스케줄된 수집 실행 - 등록된 모든 키워드 수집 (일일 제한 적용)"""
    logger.info("=" * 60)
    logger.info(f"스케줄 수집 시작: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    data = load_keywords()
    keywords = data.get("keywords", [])
    daily_limit = data.get("daily_limit", 20)  # 일일 최대 수집량

    if not keywords:
        logger.warning("등록된 키워드가 없습니다.")
        return

    enabled_keywords = [kw for kw in keywords if kw.get("enabled", True)]
    logger.info(f"수집 대상 키워드: {len(enabled_keywords)}개")
    logger.info(f"일일 최대 수집량: {daily_limit}개")

    # 오늘 이미 수집된 이미지 확인
    already_collected = count_today_images()
    logger.info(f"오늘 이미 수집된 이미지: {already_collected}개")

    if already_collected >= daily_limit:
        logger.info(f"일일 제한({daily_limit}개)에 도달. 수집 건너뜀.")
        return

    total_collected = already_collected

    for idx, kw in enumerate(enabled_keywords, 1):
        # 일일 제한 체크
        if total_collected >= daily_limit:
            logger.info(f"일일 제한({daily_limit}개) 도달. 나머지 키워드 건너뜀.")
            break

        query = kw["query"]
        country = kw.get("country", "KR")
        # 남은 수집 가능 개수만큼만 요청
        remaining = daily_limit - total_collected
        limit = min(kw.get("limit", 20), remaining)

        logger.info(f"\n[{idx}/{len(enabled_keywords)}] 키워드 수집: {query} (최대 {limit}개)")

        try:
            run_full_pipeline(
                query=query,
                country=country,
                limit=limit,
                headless=True,
                image_only=True,  # 동영상 제외, 이미지/캐러셀 첫장만 수집
                skip_download=False,
                skip_upload=False,
                skip_sheets=False
            )
            # 수집 후 카운트 갱신
            total_collected = count_today_images()
            logger.info(f"현재까지 오늘 총 {total_collected}개 이미지 수집")
        except Exception as e:
            logger.error(f"키워드 '{query}' 수집 실패: {e}")
            continue

    logger.info("\n" + "=" * 60)
    logger.info(f"스케줄 수집 완료: {datetime.now().isoformat()}")
    logger.info(f"오늘 총 수집: {total_collected}개 이미지")
    logger.info("=" * 60)


def start_scheduler():
    """스케줄러 시작 (백그라운드 실행)"""
    setup_logging()

    data = load_keywords()
    schedule_time = data.get("schedule", {}).get("time", "09:00")

    logger.info(f"스케줄러 시작 - 매일 {schedule_time}에 수집 실행")
    logger.info(f"등록된 키워드: {[kw['query'] for kw in data.get('keywords', [])]}")

    # 매일 지정 시간에 실행
    schedule.every().day.at(schedule_time).do(run_scheduled_collection)

    logger.info("스케줄러가 실행 중입니다. Ctrl+C로 종료하세요.")

    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크


if __name__ == "__main__":
    import click

    @click.group()
    def cli():
        """광고 수집 스케줄러"""
        pass

    @cli.command()
    def start():
        """스케줄러 시작 (매일 지정 시간에 자동 수집)"""
        start_scheduler()

    @cli.command()
    def run_now():
        """지금 즉시 모든 키워드 수집 실행"""
        setup_logging()
        run_scheduled_collection()

    @cli.command()
    @click.argument("query")
    @click.option("--country", "-c", default="KR", help="국가 코드")
    @click.option("--limit", "-l", default=50, help="최대 수집 개수")
    def add(query: str, country: str, limit: int):
        """새 키워드 추가"""
        setup_logging()
        add_keyword(query, country, limit)

    @cli.command()
    @click.argument("query")
    def remove(query: str):
        """키워드 제거"""
        setup_logging()
        remove_keyword(query)

    @cli.command()
    def list():
        """등록된 키워드 목록 출력"""
        keywords = list_keywords()
        if not keywords:
            print("등록된 키워드가 없습니다.")
            return

        print("\n등록된 키워드:")
        print("-" * 50)
        for kw in keywords:
            status = "활성" if kw.get("enabled", True) else "비활성"
            print(f"  - {kw['query']} ({kw.get('country', 'KR')}, {kw.get('limit', 50)}개, {status})")
        print()

    @cli.command()
    @click.argument("time")
    def set_time(time: str):
        """수집 시간 변경 (예: 09:00)"""
        data = load_keywords()
        data["schedule"]["time"] = time
        save_keywords(data)
        print(f"수집 시간이 {time}으로 변경되었습니다.")

    cli()

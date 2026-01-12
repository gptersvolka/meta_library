"""
광고 수집 모듈 (alias)
실제 구현: 01_collect_ads.py (Playwright 웹 스크래핑)
"""
import asyncio
import importlib

# 숫자가 붙은 모듈에서 import
_module = importlib.import_module("src.01_collect_ads")

# Playwright 스크래핑 함수 (async)
collect_ads_playwright = _module.collect_ads_playwright
save_raw_data = _module.save_raw_data
ADS_LIBRARY_BASE_URL = _module.ADS_LIBRARY_BASE_URL


def collect_ads(
    query: str,
    country: str = "KR",
    limit: int = 50,
    **kwargs
) -> list[dict]:
    """
    동기 래퍼 - 파이프라인에서 호출용
    내부적으로 async Playwright 함수를 실행
    """
    return asyncio.run(collect_ads_playwright(
        query=query,
        country=country,
        limit=limit,
        headless=kwargs.get("headless", True),
        active_only=kwargs.get("active_only", True)
    ))


__all__ = ["collect_ads", "collect_ads_playwright", "save_raw_data", "ADS_LIBRARY_BASE_URL"]

"""
광고 수집 모듈 (alias)
실제 구현: 01_collect_ads_api.py
"""
import importlib

# 숫자가 붙은 모듈에서 import
_module = importlib.import_module("src.01_collect_ads_api")

collect_ads = _module.collect_ads
save_raw_data = _module.save_raw_data
ADS_LIBRARY_API_URL = _module.ADS_LIBRARY_API_URL

__all__ = ["collect_ads", "save_raw_data", "ADS_LIBRARY_API_URL"]

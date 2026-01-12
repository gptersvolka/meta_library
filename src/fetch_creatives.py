"""
크리에이티브 수집 모듈 (alias)
실제 구현: 02_fetch_creatives.py
"""
import importlib

_module = importlib.import_module("src.02_fetch_creatives")

download_image = _module.download_image
capture_snapshot_page = _module.capture_snapshot_page
fetch_creatives_from_raw = _module.fetch_creatives_from_raw

__all__ = ["download_image", "capture_snapshot_page", "fetch_creatives_from_raw"]

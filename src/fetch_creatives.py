"""
크리에이티브 수집 모듈 (alias)
실제 구현: 02_fetch_creatives.py
"""
import importlib

_module = importlib.import_module("src.02_fetch_creatives")

download_image = _module.download_image
download_image_bytes = _module.download_image_bytes
calculate_image_hash = _module.calculate_image_hash
fetch_creatives_from_raw = _module.fetch_creatives_from_raw

__all__ = ["download_image", "download_image_bytes", "calculate_image_hash", "fetch_creatives_from_raw"]

"""
Sheets 기록 모듈 (alias)
실제 구현: 04_write_sheets.py
"""
import importlib

_module = importlib.import_module("src.04_write_sheets")

get_sheets_client = _module.get_sheets_client
ensure_worksheet = _module.ensure_worksheet
write_ads_raw = _module.write_ads_raw
write_ads_by_keyword = _module.write_ads_by_keyword
write_ocr_text = _module.write_ocr_text
write_ideas = _module.write_ideas

__all__ = ["get_sheets_client", "ensure_worksheet", "write_ads_raw", "write_ads_by_keyword", "write_ocr_text", "write_ideas"]

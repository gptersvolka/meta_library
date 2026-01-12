"""
OCR 모듈 (alias)
실제 구현: 05_ocr.py
"""
import importlib

_module = importlib.import_module("src.05_ocr")

preprocess_image = _module.preprocess_image
extract_text = _module.extract_text
parse_ad_elements = _module.parse_ad_elements
process_all_images = _module.process_all_images

__all__ = ["preprocess_image", "extract_text", "parse_ad_elements", "process_all_images"]

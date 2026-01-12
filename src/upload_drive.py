"""
Drive 업로드 모듈 (alias)
실제 구현: 03_upload_drive.py
"""
import importlib

_module = importlib.import_module("src.03_upload_drive")

get_drive_service = _module.get_drive_service
upload_file = _module.upload_file
upload_all_images = _module.upload_all_images

__all__ = ["get_drive_service", "upload_file", "upload_all_images"]

"""
환경 설정 로드 모듈
.env 파일에서 환경 변수를 읽어 전역 설정으로 제공
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
IMAGES_DIR = DATA_DIR / "images"
OCR_DIR = DATA_DIR / "ocr"
LOGS_DIR = PROJECT_ROOT / "logs"

# .env 파일 로드
load_dotenv(PROJECT_ROOT / ".env")


def get_env(key: str, default: str = None, required: bool = False) -> str:
    """환경 변수 값을 가져옴"""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"필수 환경 변수 '{key}'가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return value


# 검색 설정 (선택적 - import 시점에 로드)
COUNTRY = get_env("COUNTRY", default="KR")
QUERY = get_env("QUERY", default="")


# 필수 설정 (함수로 제공 - 실행 시점에 검증)
def get_meta_access_token() -> str:
    """Meta API 토큰 반환"""
    return get_env("META_ACCESS_TOKEN", required=True)


def get_google_credentials_path() -> str:
    """Google 서비스 계정 JSON 경로 반환"""
    return get_env("GOOGLE_APPLICATION_CREDENTIALS", required=True)


def get_sheet_id() -> str:
    """Google 스프레드시트 ID 반환"""
    return get_env("SHEET_ID", required=True)


def get_drive_folder_id() -> str:
    """Google Drive 폴더 ID 반환"""
    return get_env("DRIVE_FOLDER_ID", required=True)


# 하위 호환성을 위한 변수 (실행 시점에 lazy load)
class _LazyConfig:
    """필수 환경 변수를 실행 시점에 로드하는 래퍼"""

    @property
    def META_ACCESS_TOKEN(self):
        return get_meta_access_token()

    @property
    def GOOGLE_CREDENTIALS_PATH(self):
        return get_google_credentials_path()

    @property
    def SHEET_ID(self):
        return get_sheet_id()

    @property
    def DRIVE_FOLDER_ID(self):
        return get_drive_folder_id()


_lazy = _LazyConfig()

# 모듈 레벨에서 접근 가능하도록 (실행 시점에 로드됨)
META_ACCESS_TOKEN = property(lambda self: get_meta_access_token())
GOOGLE_CREDENTIALS_PATH = property(lambda self: get_google_credentials_path())
SHEET_ID = property(lambda self: get_sheet_id())
DRIVE_FOLDER_ID = property(lambda self: get_drive_folder_id())


def ensure_dirs():
    """필요한 디렉토리들이 존재하는지 확인하고 생성"""
    for dir_path in [RAW_DIR, IMAGES_DIR, OCR_DIR, LOGS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """로깅 설정 초기화"""
    from loguru import logger
    ensure_dirs()
    logger.add(
        LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        encoding="utf-8",
        level="INFO"
    )
    return logger


if __name__ == "__main__":
    # 설정 테스트
    ensure_dirs()
    print(f"프로젝트 루트: {PROJECT_ROOT}")
    print(f"국가: {COUNTRY}")
    print(f"검색 키워드: {QUERY}")

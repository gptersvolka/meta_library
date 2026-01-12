"""
OCR 처리 모듈
이미지에서 텍스트를 추출하고 주요 정보(혜택, 오퍼, CTA)를 파싱
"""

import json
import re
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

from src.config import IMAGES_DIR, OCR_DIR, ensure_dirs


def preprocess_image(image_path: Path) -> Image.Image:
    """OCR 정확도 향상을 위한 이미지 전처리"""
    img = Image.open(image_path)

    # 그레이스케일 변환
    img = img.convert("L")

    # 대비 향상
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # 선명도 향상
    img = img.filter(ImageFilter.SHARPEN)

    # 이미지 확대 (작은 텍스트 인식률 향상)
    width, height = img.size
    if width < 1000:
        scale = 1000 / width
        img = img.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

    return img


def extract_text(image_path: Path, lang: str = "kor+eng") -> str:
    """
    이미지에서 텍스트 추출

    Args:
        image_path: 이미지 파일 경로
        lang: OCR 언어 (기본값: 한국어+영어)

    Returns:
        추출된 텍스트
    """
    try:
        # 전처리
        img = preprocess_image(image_path)

        # OCR 실행
        text = pytesseract.image_to_string(img, lang=lang)

        # 불필요한 공백 정리
        text = re.sub(r'\s+', ' ', text).strip()

        return text
    except Exception as e:
        logger.error(f"OCR 실패 ({image_path}): {e}")
        return ""


def parse_ad_elements(text: str) -> dict:
    """
    OCR 텍스트에서 광고 요소 추출

    Returns:
        {key_claims, offer, cta}
    """
    result = {
        "key_claims": "",
        "offer": "",
        "cta": ""
    }

    if not text:
        return result

    # CTA 패턴 (버튼 텍스트)
    cta_patterns = [
        r'(지금\s*(신청|구매|확인|시작|가입))',
        r'(무료\s*(체험|시작|다운로드))',
        r'(자세히\s*보기)',
        r'(더\s*알아보기)',
        r'(바로\s*가기)',
        r'(구매하기|신청하기|가입하기|다운로드)',
        r'(Shop\s*Now|Learn\s*More|Sign\s*Up|Get\s*Started|Buy\s*Now)',
    ]

    ctas = []
    for pattern in cta_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        ctas.extend([m[0] if isinstance(m, tuple) else m for m in matches])
    result["cta"] = ", ".join(set(ctas))

    # 오퍼 패턴 (가격, 할인, 혜택)
    offer_patterns = [
        r'(\d+%\s*(할인|OFF|세일))',
        r'(₩[\d,]+원?)',
        r'(\d+원)',
        r'(무료\s*배송)',
        r'(첫\s*달?\s*무료)',
        r'(\d+\+\d+)',
        r'(사은품|증정|선물)',
    ]

    offers = []
    for pattern in offer_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        offers.extend([m[0] if isinstance(m, tuple) else m for m in matches])
    result["offer"] = ", ".join(set(offers))

    # 핵심 주장 (남은 텍스트에서 핵심 문장 추출)
    # CTA와 오퍼를 제외한 첫 몇 문장을 핵심 주장으로 간주
    sentences = re.split(r'[.!?]\s*', text)
    key_sentences = []
    for sent in sentences[:5]:
        sent = sent.strip()
        if len(sent) > 10 and not any(cta.lower() in sent.lower() for cta in ctas):
            key_sentences.append(sent)
    result["key_claims"] = ". ".join(key_sentences[:3])

    return result


def process_all_images(lang: str = "kor+eng") -> list[dict]:
    """
    IMAGES_DIR의 모든 이미지에 대해 OCR 수행

    Returns:
        OCR 결과 리스트
    """
    ensure_dirs()
    results = []

    image_files = list(IMAGES_DIR.glob("*"))
    image_files = [f for f in image_files if f.suffix.lower() in [".png", ".jpg", ".jpeg"]]

    if not image_files:
        logger.warning("처리할 이미지가 없습니다.")
        return results

    logger.info(f"{len(image_files)}개 이미지 OCR 시작")

    for i, image_path in enumerate(image_files):
        # 파일명에서 ad_id 추출
        filename = image_path.stem
        parts = filename.rsplit("_", 1)
        ad_id = parts[-1] if len(parts) > 1 else filename

        # OCR 수행
        text = extract_text(image_path, lang)
        elements = parse_ad_elements(text)

        result = {
            "ad_id": ad_id,
            "image_path": str(image_path),
            "ocr_text": text,
            **elements
        }
        results.append(result)

        # OCR 결과 개별 저장
        ocr_file = OCR_DIR / f"{filename}.json"
        with open(ocr_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"[{i+1}/{len(image_files)}] {filename}: {len(text)}자 추출")

    # 전체 결과 저장
    all_results_file = OCR_DIR / "all_ocr_results.json"
    with open(all_results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"OCR 완료: {len(results)}개 이미지 처리")
    return results


@click.command()
@click.option("--image", "-i", type=click.Path(exists=True), help="특정 이미지 파일만 처리")
@click.option("--lang", "-l", default="kor+eng", help="OCR 언어 (기본값: kor+eng)")
def main(image: Optional[str], lang: str):
    """이미지에서 텍스트를 추출합니다."""
    ensure_dirs()

    if image:
        image_path = Path(image)
        text = extract_text(image_path, lang)
        elements = parse_ad_elements(text)

        logger.info(f"추출된 텍스트:\n{text}")
        logger.info(f"파싱 결과: {elements}")
    else:
        process_all_images(lang)


if __name__ == "__main__":
    main()

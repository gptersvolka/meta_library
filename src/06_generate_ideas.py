"""
광고 소재 아이디어 생성 모듈
수집된 광고 데이터와 OCR 결과를 분석하여 새로운 아이디어 제안
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from src.config import OCR_DIR, RAW_DIR, ensure_dirs


def analyze_patterns(ocr_results: list[dict]) -> dict:
    """
    OCR 결과에서 패턴 분석

    Returns:
        패턴 분석 결과 {common_ctas, common_offers, hook_patterns, ...}
    """
    ctas = []
    offers = []
    claims = []

    for result in ocr_results:
        if result.get("cta"):
            ctas.extend([c.strip() for c in result["cta"].split(",")])
        if result.get("offer"):
            offers.extend([o.strip() for o in result["offer"].split(",")])
        if result.get("key_claims"):
            claims.append(result["key_claims"])

    # 빈도 계산
    from collections import Counter
    cta_freq = Counter(ctas)
    offer_freq = Counter(offers)

    return {
        "common_ctas": cta_freq.most_common(5),
        "common_offers": offer_freq.most_common(5),
        "claim_samples": claims[:10],
        "total_ads_analyzed": len(ocr_results)
    }


def generate_ideas_from_patterns(patterns: dict, source_ads: list[str]) -> dict:
    """
    패턴 분석 결과를 바탕으로 아이디어 생성

    Note: 실제 프로덕션에서는 LLM API를 사용하여 더 창의적인 아이디어 생성 가능
    현재는 템플릿 기반으로 구현
    """
    week = datetime.now().strftime("%Y-W%W")

    # 패턴 기반 인사이트 생성
    insights = []

    common_ctas = patterns.get("common_ctas", [])
    if common_ctas:
        top_cta = common_ctas[0][0] if common_ctas else "자세히 보기"
        insights.append(f"가장 많이 사용된 CTA: {top_cta}")

    common_offers = patterns.get("common_offers", [])
    if common_offers:
        top_offer = common_offers[0][0] if common_offers else "할인"
        insights.append(f"주요 오퍼 유형: {top_offer}")

    insights.append(f"분석된 광고 수: {patterns.get('total_ads_analyzed', 0)}개")

    # 아이디어 템플릿
    idea = {
        "week": week,
        "source_ads": ", ".join(source_ads[:5]),
        "insights": " | ".join(insights),

        # 아이디어 1: 직접적 혜택 강조
        "idea_1_title": "혜택 직접 소구",
        "idea_1_copy": f"지금 {common_offers[0][0] if common_offers else '특별 혜택'}! {common_ctas[0][0] if common_ctas else '지금 확인하세요'}",
        "idea_1_visual": "중앙에 큰 숫자(할인율/가격), 하단에 CTA 버튼",

        # 아이디어 2: 문제-해결 구조
        "idea_2_title": "문제 해결형",
        "idea_2_copy": "[고객 고민]으로 힘드셨죠? [제품/서비스]로 해결하세요",
        "idea_2_visual": "Before-After 분할 레이아웃, 감정적 이미지 사용",

        # 아이디어 3: 사회적 증거
        "idea_3_title": "사회적 증거형",
        "idea_3_copy": "이미 [숫자]명이 선택한 [제품/서비스]",
        "idea_3_visual": "리뷰/평점 스크린샷, 고객 후기 인용"
    }

    return idea


def generate_ideas_with_llm(ocr_results: list[dict], patterns: dict) -> list[dict]:
    """
    LLM을 사용한 아이디어 생성 (확장용)

    Note: 실제 구현 시 OpenAI, Claude 등의 API 연동 필요
    현재는 placeholder
    """
    # TODO: LLM API 연동
    # prompt = f'''
    # 다음 광고 데이터를 분석하여 새로운 광고 소재 아이디어 3개를 생성하세요.
    #
    # 분석된 패턴:
    # - 자주 사용된 CTA: {patterns.get('common_ctas')}
    # - 자주 사용된 오퍼: {patterns.get('common_offers')}
    # - 주요 주장 예시: {patterns.get('claim_samples')}
    #
    # 각 아이디어는 다음 형식으로 제공:
    # - title: 아이디어 제목
    # - copy: 광고 문구 (1-2문장)
    # - visual: 비주얼 가이드
    # '''

    logger.info("LLM 아이디어 생성은 아직 구현되지 않았습니다. 템플릿 기반 생성 사용")
    return []


def generate_all_ideas() -> list[dict]:
    """전체 아이디어 생성 파이프라인"""
    ensure_dirs()

    # OCR 결과 로드
    ocr_file = OCR_DIR / "all_ocr_results.json"
    if not ocr_file.exists():
        logger.error("OCR 결과 파일이 없습니다. 먼저 05_ocr.py를 실행하세요.")
        return []

    with open(ocr_file, "r", encoding="utf-8") as f:
        ocr_results = json.load(f)

    if not ocr_results:
        logger.warning("OCR 결과가 비어있습니다.")
        return []

    # 패턴 분석
    patterns = analyze_patterns(ocr_results)
    logger.info(f"패턴 분석 완료: {patterns}")

    # 소스 광고 ID 추출
    source_ads = [r.get("ad_id", "") for r in ocr_results if r.get("ad_id")]

    # 아이디어 생성
    ideas = [generate_ideas_from_patterns(patterns, source_ads)]

    # LLM 기반 추가 아이디어 (구현 시)
    # llm_ideas = generate_ideas_with_llm(ocr_results, patterns)
    # ideas.extend(llm_ideas)

    # 결과 저장
    ideas_file = OCR_DIR / "generated_ideas.json"
    with open(ideas_file, "w", encoding="utf-8") as f:
        json.dump(ideas, f, ensure_ascii=False, indent=2)

    logger.info(f"아이디어 생성 완료: {len(ideas)}개")
    return ideas


@click.command()
@click.option("--use-llm", is_flag=True, help="LLM 기반 아이디어 생성 사용 (미구현)")
def main(use_llm: bool):
    """광고 소재 아이디어를 생성합니다."""
    if use_llm:
        logger.warning("LLM 기반 생성은 아직 구현되지 않았습니다.")

    ideas = generate_all_ideas()

    if ideas:
        for i, idea in enumerate(ideas, 1):
            logger.info(f"\n=== 아이디어 {i} ===")
            logger.info(f"인사이트: {idea.get('insights')}")
            logger.info(f"아이디어 1: {idea.get('idea_1_title')} - {idea.get('idea_1_copy')}")
            logger.info(f"아이디어 2: {idea.get('idea_2_title')} - {idea.get('idea_2_copy')}")
            logger.info(f"아이디어 3: {idea.get('idea_3_title')} - {idea.get('idea_3_copy')}")


if __name__ == "__main__":
    main()

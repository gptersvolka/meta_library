"""
기존 data/raw/*.json 파일들을 Supabase ads 테이블로 마이그레이션
(C++ 빌드 도구 없이 requests 사용)
"""

import json
import os
import glob
import requests
from datetime import datetime

def get_supabase_config():
    """Supabase 설정 반환"""
    from dotenv import load_dotenv
    load_dotenv()

    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    return url, key


def supabase_upsert(table: str, data: dict, url: str, key: str):
    """Supabase REST API로 upsert"""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    response = requests.post(
        f"{url}/rest/v1/{table}",
        headers=headers,
        json=data
    )

    return response.status_code in [200, 201, 204, 409]


def migrate_ads_to_supabase():
    """기존 JSON 파일들의 광고 데이터를 Supabase로 마이그레이션"""

    url, key = get_supabase_config()

    if not url or not key:
        print("[ERROR] Supabase env not set")
        print("   Set SUPABASE_URL and SUPABASE_KEY in .env")
        return

    # data/raw/*.json 파일들 찾기
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    json_files = glob.glob(os.path.join(data_dir, "*.json"))

    print(f"[INFO] Found {len(json_files)} JSON files")

    total_saved = 0
    total_skipped = 0

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            query = data.get("query", "unknown")
            ads = data.get("ads", [])

            print(f"\n[PROCESSING] {os.path.basename(json_file)} ({query}, {len(ads)} ads)")

            for ad in ads:
                image_url = ad.get("image_urls", [""])[0] if ad.get("image_urls") else None
                if not image_url:
                    total_skipped += 1
                    continue

                permanent_url = ad.get("permanent_image_url")

                ad_data = {
                    "keyword": query,
                    "page_name": ad.get("page_name", "Unknown"),
                    "ad_text": ad.get("ad_text", []),
                    "image_url": image_url,
                    "permanent_image_url": permanent_url,
                    "landing_url": ad.get("landing_url"),
                    "collected_at": ad.get("collected_at", datetime.now().isoformat()),
                }

                if supabase_upsert("ads", ad_data, url, key):
                    total_saved += 1
                else:
                    total_skipped += 1

        except Exception as e:
            print(f"   [ERROR] File processing failed: {e}")

    print(f"\n[DONE] Migration complete!")
    print(f"   Saved: {total_saved}")
    print(f"   Skipped: {total_skipped}")


def migrate_keywords_to_supabase():
    """기존 keywords.json을 Supabase로 마이그레이션"""

    url, key = get_supabase_config()

    if not url or not key:
        print("[ERROR] Supabase env not set")
        return

    keywords_file = os.path.join(os.path.dirname(__file__), "..", "data", "keywords.json")

    if not os.path.exists(keywords_file):
        print("[ERROR] keywords.json not found")
        return

    with open(keywords_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    keywords = data.get("keywords", [])
    print(f"[INFO] Migrating {len(keywords)} keywords...")

    saved = 0
    for kw in keywords:
        kw_data = {
            "query": kw.get("query"),
            "country": kw.get("country", "KR"),
            "ad_limit": kw.get("limit", 50),
            "enabled": kw.get("enabled", True),
        }

        if supabase_upsert("keywords", kw_data, url, key):
            saved += 1
        else:
            print(f"   [WARN] {kw.get('query')} save failed")

    print(f"[DONE] {saved} keywords migrated!")


if __name__ == "__main__":
    print("=" * 50)
    print("Supabase Migration Script")
    print("=" * 50)

    print("\n[1/2] Keywords Migration")
    migrate_keywords_to_supabase()

    print("\n[2/2] Ads Data Migration")
    migrate_ads_to_supabase()

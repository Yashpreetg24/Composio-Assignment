import argparse
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

from googlesearch import search

from research import analyze_with_llm, fetch_page_text
from runner import (
    export_results_csv,
    load_existing_results,
    load_seed_data,
    save_results_json,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_domain(hint: str) -> str:
    # Basic cleanup
    hint = hint.split(" ")[
        0
    ].strip()  # e.g. "twenty.com (open-source CRM)" -> "twenty.com"
    if not hint.startswith("http"):
        hint = "https://" + hint
    parsed = urlparse(hint)
    return parsed.netloc


def advanced_research(app_data: dict) -> Any:
    """Perform a deep-dive research with multiple fallbacks."""
    app_name = app_data["app"]
    hint = app_data["hint"]
    domain = extract_domain(hint)

    urls_to_try = []

    # 1. Primary search
    primary_query = f"{app_name} API developer documentation {hint}"
    try:
        primary_results = list(search(primary_query, num_results=1))
        if primary_results:
            urls_to_try.append(primary_results[0])
    except Exception as e:
        logger.warning(f"Primary search failed: {e}")

    # 2. Direct guesses
    urls_to_try.extend(
        [
            f"https://{domain}/docs",
            f"https://{domain}/developers",
            f"https://{domain}/api",
            f"https://developers.{domain}",
        ]
    )

    # 3. Secondary search
    secondary_query = f'"{app_name} API documentation" OR "{app_name} MCP server"'
    try:
        sec_results = list(search(secondary_query, num_results=2))
        urls_to_try.extend(sec_results)
    except Exception as e:
        logger.warning(f"Secondary search failed: {e}")

    # Remove duplicates while preserving order
    seen = set()
    urls_to_try = [x for x in urls_to_try if not (x in seen or seen.add(x))]

    best_text = ""
    best_url = ""

    for url in urls_to_try:
        logger.info(f"Trying to fetch: {url}")
        text = fetch_page_text(url)
        # Simple heuristic: if it has enough text and mentions API
        if len(text) > 500 and (
            "API" in text or "developer" in text.lower() or "endpoints" in text.lower()
        ):
            best_text = text
            best_url = url
            break

    # LLM analysis
    logger.info(f"Running LLM analysis on best URL: {best_url}")
    result = analyze_with_llm(app_data, best_text, best_url)

    # Wait for rate limits
    time.sleep(2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", type=int, nargs="+", required=True)
    args = parser.parse_args()

    target_ids = set(args.ids)
    apps = load_seed_data()
    results = load_existing_results()

    apps_to_run = [a for a in apps if a["id"] in target_ids]

    recheck_log = []

    for app_data in apps_to_run:
        app_id = app_data["id"]
        old_result = results.get(app_id, {})
        old_verdict = old_result.get("buildability_verdict", "unknown")
        old_conf = old_result.get("confidence", "unknown")

        logger.info(f"--- Advanced recheck for [{app_id}] {app_data['app']} ---")
        try:
            new_result_obj = advanced_research(app_data)
            new_result = new_result_obj.model_dump()

            new_verdict = new_result.get("buildability_verdict")
            new_conf = new_result.get("confidence")

            log_entry = {
                "id": app_id,
                "app": app_data["app"],
                "verdict_changed": old_verdict != new_verdict,
                "confidence_changed": old_conf != new_conf,
                "old_verdict": old_verdict,
                "new_verdict": new_verdict,
                "old_confidence": old_conf,
                "new_confidence": new_conf,
                "new_evidence_url": new_result.get("evidence_url"),
            }
            recheck_log.append(log_entry)

            logger.info(
                f"Verdict: {old_verdict} -> {new_verdict} | Confidence: {old_conf} -> {new_conf}"
            )

            # Save new result
            results[app_id] = new_result
            save_results_json(results)

        except Exception as e:
            logger.error(f"Failed advanced recheck for {app_data['app']}: {e}")

    export_results_csv(results)

    # Save recheck log
    with open("recheck_log.json", "w", encoding="utf-8") as f:
        json.dump(recheck_log, f, indent=2)

    logger.info("Advanced recheck complete. Check recheck_log.json for comparisons.")


if __name__ == "__main__":
    main()

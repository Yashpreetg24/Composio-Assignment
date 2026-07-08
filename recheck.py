import argparse
import logging

from research import research_app
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


def main():
    parser = argparse.ArgumentParser(description="Re-run research for specific app IDs")
    parser.add_argument(
        "--ids", type=int, nargs="+", required=True, help="List of app IDs to re-run"
    )
    args = parser.parse_args()

    target_ids = set(args.ids)

    apps = load_seed_data()
    if not apps:
        return

    results = load_existing_results()

    apps_to_run = [app for app in apps if app["id"] in target_ids]

    if not apps_to_run:
        logger.warning(f"No apps found matching IDs: {target_ids}")
        return

    logger.info(
        f"Re-running research for {len(apps_to_run)} apps: {[a['id'] for a in apps_to_run]}"
    )

    for app_data in apps_to_run:
        app_id = app_data["id"]
        try:
            result = research_app(app_data)
            results[app_id] = result.model_dump()

            # Save immediately
            save_results_json(results)
            logger.info(f"Successfully updated [{app_id}] {app_data['app']}")
        except Exception as e:
            logger.error(f"Failed to re-run {app_data['app']}: {e}")

    # Final export
    export_results_csv(results)
    logger.info("Re-check complete. Results saved to results.json and results.csv")


if __name__ == "__main__":
    main()

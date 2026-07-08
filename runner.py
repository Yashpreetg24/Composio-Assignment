import json
import csv
import os
import logging
from typing import List, Dict, Any
from research import research_app

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SEED_FILE = "apps_seed.json"
RESULTS_JSON_FILE = "results.json"
RESULTS_CSV_FILE = "results.csv"

def load_seed_data() -> List[Dict[str, Any]]:
    if not os.path.exists(SEED_FILE):
        logger.error(f"Seed file {SEED_FILE} not found.")
        return []
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_existing_results() -> Dict[int, Dict[str, Any]]:
    if not os.path.exists(RESULTS_JSON_FILE):
        return {}
    try:
        with open(RESULTS_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Support both list and dict formats for backwards compatibility
            if isinstance(data, list):
                return {item['id']: item for item in data}
            return data
    except Exception as e:
        logger.warning(f"Could not load existing results. Starting fresh. Error: {e}")
        return {}

def save_results_json(results: Dict[int, Dict[str, Any]]):
    with open(RESULTS_JSON_FILE, 'w', encoding='utf-8') as f:
        # Save as a list of objects
        json.dump(list(results.values()), f, indent=2, ensure_ascii=False)

def export_results_csv(results: Dict[int, Dict[str, Any]]):
    if not results:
        return
        
    # Get all possible fields from the first result (or our schema)
    fields = [
        "id", "category", "app", "description", "auth_methods", 
        "self_serve", "api_surface", "buildability_verdict", 
        "verdict_reason", "evidence_url", "confidence", "needs_human_review"
    ]
    
    with open(RESULTS_CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        
        for res in results.values():
            row = dict(res)
            # Convert list to string for CSV
            if isinstance(row.get('auth_methods'), list):
                row['auth_methods'] = ", ".join(row['auth_methods'])
            writer.writerow(row)

def main():
    apps = load_seed_data()
    if not apps:
        return
        
    results = load_existing_results()
    
    logger.info(f"Loaded {len(apps)} apps to research. Found {len(results)} existing results.")
    
    human_review_needed = []
    
    # Process each app sequentially
    for app_data in apps:
        app_id = app_data['id']
        
        # Skip if we already successfully processed it and it doesn't need human review
        if app_id in results and not results[app_id].get('needs_human_review', False):
            logger.info(f"Skipping [{app_id}] {app_data['app']} (already processed)")
            continue
            
        try:
            result = research_app(app_data)
            # Convert Pydantic model to dict
            result_dict = result.model_dump()
            
            # Store in our results map
            results[app_id] = result_dict
            
            if result_dict.get('needs_human_review'):
                human_review_needed.append(result_dict)
                
            # Save incrementally
            save_results_json(results)
            
        except Exception as e:
            logger.error(f"Failed to process app {app_data['app']}: {e}")
            # Ensure it's marked for human review
            fallback = {
                "id": app_id,
                "category": app_data['category'],
                "app": app_data['app'],
                "needs_human_review": True,
                "verdict_reason": f"Runner script error: {str(e)}"
            }
            results[app_id] = fallback
            human_review_needed.append(fallback)
            save_results_json(results)

    # Final export
    export_results_csv(results)
    
    # Print summary
    print("\n" + "="*50)
    print("RESEARCH RUN COMPLETE")
    print("="*50)
    print(f"Total apps processed: {len(results)} / {len(apps)}")
    print(f"Apps needing human review: {len(human_review_needed)}")
    
    if human_review_needed:
        print("\n--- APPS NEEDING HUMAN REVIEW ---")
        for app in human_review_needed:
            print(f"- [{app['id']}] {app['app']}: {app.get('verdict_reason', 'Unknown reason')}")

if __name__ == "__main__":
    main()

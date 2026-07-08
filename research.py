import json
import logging
import time
from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from openai import OpenAI
import os
from dotenv import load_dotenv

from schema import AppResearchResult
from pydantic import ValidationError

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize clients
openai_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def search_for_docs_url(app_name: str, hint: str) -> Optional[str]:
    """Search for the API documentation URL using DuckDuckGo."""
    query = f"{app_name} API developer documentation {hint}"
    try:
        results = list(search(query, num_results=3))
        if results:
            return results[0]
    except Exception as e:
        logger.warning(f"Search failed for {app_name}: {e}")
    return None

def fetch_page_text(url: str) -> str:
    """Fetch the webpage and extract its text."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        # Limit text length to avoid token limits (Claude 3.5 Sonnet has 200k context, but we keep it reasonable)
        return text[:20000]
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""

def analyze_with_llm(app_data: dict, docs_text: str, evidence_url: str) -> AppResearchResult:
    """Use Anthropic to analyze the docs text and extract structured information."""
    prompt = f"""
    You are an expert API researcher. Your task is to analyze the provided documentation text for an app and extract specific structured information.
    
    App Name: {app_data['app']}
    Category: {app_data['category']}
    Hint: {app_data['hint']}
    Evidence URL: {evidence_url}
    
    Documentation Text (first 20000 chars):
    {docs_text}
    
    Based on the information above, extract the required fields and return a raw JSON object matching this schema. DO NOT wrap it in markdown code blocks. DO NOT add any other text.
    {{
        "id": {app_data['id']},
        "category": "{app_data['category']}",
        "app": "{app_data['app']}",
        "description": "One-line description of what the app does",
        "auth_methods": ["OAuth2", "API key"], // array of strings
        "self_serve": "self-serve", // one of "self-serve", "gated-paid", "gated-approval", "gated-partnership"
        "api_surface": "Short text describing whether there's a documented public REST/GraphQL API...",
        "buildability_verdict": "buildable-now", // one of "buildable-now", "buildable-with-friction", "not-buildable"
        "verdict_reason": "One-line reason/blocker for the buildability verdict",
        "evidence_url": "{evidence_url}",
        "confidence": "high", // one of "high", "medium", "low"
        "needs_human_review": false // boolean, true if you couldn't find clear info
    }}
    """
    
    if not docs_text:
        # If we couldn't fetch text, still let LLM try based on just the name/hint or return needs_human_review
        prompt = f"""
        We could not fetch the documentation for {app_data['app']}.
        Please return a JSON object with needs_human_review = true, and fill in what you can based on your general knowledge.
        Evidence URL: {evidence_url if evidence_url else 'None found'}
        """ + prompt

    def _call_llm(current_prompt):
        resp = openai_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "user", "content": current_prompt}
            ],
            temperature=0,
            max_tokens=1024,
        )
        return json.loads(resp.choices[0].message.content.strip())

    try:
        data = _call_llm(prompt)
        try:
            return AppResearchResult(**data)
        except ValidationError as ve:
            logger.warning(f"Validation failed for {app_data['app']}, retrying... Error: {ve}")
            retry_prompt = prompt + "\n\nWARNING: Your previous response failed validation. Make sure self_serve is STRICTLY ONE OF: 'self-serve', 'gated-paid', 'gated-approval', 'gated-partnership' and buildability_verdict is STRICTLY ONE OF: 'buildable-now', 'buildable-with-friction', 'not-buildable'."
            data2 = _call_llm(retry_prompt)
            try:
                return AppResearchResult(**data2)
            except ValidationError as ve2:
                logger.error(f"Validation failed again for {app_data['app']}, falling back.")
                # Fallback on the returned data but fix the strict fields
                data2['self_serve'] = 'gated-approval'
                data2['buildability_verdict'] = 'buildable-with-friction'
                data2['confidence'] = 'low'
                data2['needs_human_review'] = True
                data2['verdict_reason'] = f"Validation fallback: {ve2}"
                return AppResearchResult(**data2)
        
    except Exception as e:
        logger.error(f"LLM extraction failed for {app_data['app']}: {e}")
        # Return a fallback result
        return AppResearchResult(
            id=app_data['id'],
            category=app_data['category'],
            app=app_data['app'],
            description="Failed to extract",
            auth_methods=[],
            self_serve="gated-partnership", # Safe fallback
            api_surface="Unknown due to extraction error",
            buildability_verdict="not-buildable",
            verdict_reason=f"Error during analysis: {str(e)}",
            evidence_url=evidence_url if evidence_url else "",
            confidence="low",
            needs_human_review=True
        )

def research_app(app_data: dict) -> AppResearchResult:
    """End-to-end research for a single app."""
    logger.info(f"Researching [{app_data['id']}] {app_data['app']}...")
    
    evidence_url = search_for_docs_url(app_data['app'], app_data['hint'])
    
    docs_text = ""
    if evidence_url:
        docs_text = fetch_page_text(evidence_url)
    
    result = analyze_with_llm(app_data, docs_text, evidence_url or "")
    
    # Simple rate limiting for DuckDuckGo and Anthropic
    time.sleep(2)
    
    return result

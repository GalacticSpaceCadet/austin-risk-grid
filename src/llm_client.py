"""
LLM Client: Ollama API Integration
Simple client for communicating with locally-running Qwen3 8B via Ollama.
"""

import json
import requests
from typing import Dict, List, Optional


# Import config
try:
    from .config import (
        OLLAMA_API_URL, OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_MAX_TOKENS,
        MAX_PREDICTED_INCIDENTS
    )
    DEFAULT_API_URL = OLLAMA_API_URL
    DEFAULT_MODEL = OLLAMA_MODEL
    DEFAULT_TEMPERATURE = OLLAMA_TEMPERATURE
    DEFAULT_MAX_TOKENS = OLLAMA_MAX_TOKENS
    DEFAULT_MAX_PREDICTED = MAX_PREDICTED_INCIDENTS
except ImportError:
    # Fallback defaults
    DEFAULT_API_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "qwen3:8b"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 8000
    DEFAULT_MAX_PREDICTED = 20


def build_prompt(formatted_data: Dict, max_incidents: int = None) -> str:
    """
    Build prompt for LLM to predict spatial distribution.

    Args:
        formatted_data: Formatted data from format_for_llm()
        max_incidents: Maximum number of incidents to request (uses config default if None)

    Returns:
        Prompt string for LLM
    """
    max_incidents = max_incidents or DEFAULT_MAX_PREDICTED
    
    current = formatted_data["current_3hour_slice"]
    year_prior = formatted_data["year_prior_same_day"]
    week_prior_current = formatted_data.get("week_prior_current_slice", {})
    week_prior_future = formatted_data.get("week_prior_future_slice", {})

    prompt = f"""Predict traffic incidents 3 hours after {current['end_time']} in Austin, Texas.

Current 3-hour slice ({current['start_time']} to {current['end_time']}): {current['incident_count']} incidents
Locations: {json.dumps(current['locations'][:200], indent=2)}

Year prior 8-hour window ({year_prior.get('start_time', 'N/A')} to {year_prior.get('end_time', 'N/A')}): {year_prior['incident_count']} incidents  
Locations: {json.dumps(year_prior['locations'][:200], indent=2)}

Week prior current slice ({week_prior_current.get('start_time', 'N/A')} to {week_prior_current.get('end_time', 'N/A')}): {week_prior_current.get('incident_count', 0)} incidents
Locations: {json.dumps(week_prior_current.get('locations', [])[:200], indent=2)}

Week prior future slice ({week_prior_future.get('start_time', 'N/A')} to {week_prior_future.get('end_time', 'N/A')}) - THIS IS WHAT WE'RE PREDICTING: {week_prior_future.get('incident_count', 0)} incidents
Locations: {json.dumps(week_prior_future.get('locations', [])[:200], indent=2)}

Return ONLY a JSON array with up to {max_incidents} predicted locations. Each object: {{"lat": float, "lon": float, "weight": float}}.
Lat range: 30.17-30.50, Lon range: -97.90 to -97.60, Weight: 0.0-1.0.

JSON only, no explanation:"""

    return prompt


def generate_prediction(
    formatted_data: Dict,
    api_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    Call Ollama API to generate prediction.

    Args:
        formatted_data: Formatted data from format_for_llm()
        api_url: Ollama API endpoint URL (uses config default if None)
        model: Model name (uses config default if None)
        temperature: Sampling temperature (uses config default if None)
        max_tokens: Maximum tokens to generate (uses config default if None)

    Returns:
        Raw response text from LLM
    """
    # Use config defaults if not provided
    api_url = api_url or DEFAULT_API_URL
    model = model or DEFAULT_MODEL
    temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
    max_tokens = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
    
    prompt = build_prompt(formatted_data, max_incidents=None)

    # Ollama API format
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }

    try:
        response = requests.post(api_url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        # Extract text from Ollama response
        if "response" in result:
            response_text = result["response"]
            if not response_text or response_text.strip() == "":
                raise ValueError(f"Empty response from Ollama. Full result: {result}")
            return response_text
        else:
            raise ValueError(f"Unexpected API response format. Full result: {result}")
            
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to connect to Ollama API at {api_url}: {e}")


def parse_llm_response(response_text: str, max_incidents: int = None) -> List[Dict]:
    """
    Extract and validate JSON from LLM response.

    Args:
        response_text: Raw text response from LLM
        max_incidents: Maximum number of incidents to return (uses config default if None)

    Returns:
        List of predicted incidents with lat, lon, weight (limited to max_incidents)
    """
    max_incidents = max_incidents or DEFAULT_MAX_PREDICTED
    
    # Try to extract JSON from response (may have extra text)
    response_text = response_text.strip()
    
    # Find JSON array in response
    start_idx = response_text.find('[')
    end_idx = response_text.rfind(']') + 1
    
    if start_idx == -1 or end_idx == 0:
        raise ValueError(f"Could not find JSON array in LLM response: {response_text[:200]}")
    
    json_str = response_text[start_idx:end_idx]
    
    try:
        predictions = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {e}\nResponse: {json_str[:500]}")
    
    # Validate structure
    if not isinstance(predictions, list):
        raise ValueError(f"Expected list, got {type(predictions)}")
    
    validated = []
    for i, pred in enumerate(predictions):
        if len(validated) >= max_incidents:
            break
            
        if not isinstance(pred, dict):
            continue
        if "lat" not in pred or "lon" not in pred or "weight" not in pred:
            continue
        
        # Validate ranges
        lat = float(pred["lat"])
        lon = float(pred["lon"])
        weight = float(pred["weight"])
        
        # Austin bounds check
        if 30.0 <= lat <= 31.0 and -98.0 <= lon <= -97.0:
            validated.append({
                "lat": lat,
                "lon": lon,
                "weight": max(0.0, min(1.0, weight))  # Clamp weight to [0, 1]
            })
    
    if not validated:
        raise ValueError("No valid predictions found in LLM response")
    
    return validated


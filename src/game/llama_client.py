"""
LLaMA Client for Pandemonium AI

Handles Ollama API calls with retry logic and fallback.
Ollama must be running locally: ollama serve
"""

import requests
import json
from typing import Dict, Tuple, Optional

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"
TIMEOUT_SECONDS = 90


def call_ollama(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.8,
    max_retries: int = 2
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Call local Ollama LLM with retry logic.

    Args:
        system_prompt: System instructions for the LLM
        user_prompt: User task description
        model: Ollama model name (default: llama3.2)
        temperature: Sampling temperature (0.0-1.0)
        max_retries: Number of retry attempts

    Returns:
        Tuple of (success: bool, parsed_json: Dict or None, error_message: str or None)

    Example:
        success, data, error = call_ollama(system_prompt, user_prompt)
        if success:
            print(data["scenario_name"])
        else:
            print(f"Error: {error}")
    """
    # Combine prompts
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    for attempt in range(max_retries):
        try:
            print(f"[LLM] Calling Ollama (attempt {attempt + 1}/{max_retries})...")

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "format": "json",  # Force JSON output
                    "options": {
                        "temperature": temperature,
                        "num_predict": 2500  # Max tokens (long scenarios need this)
                    }
                },
                timeout=TIMEOUT_SECONDS
            )

            if response.status_code != 200:
                error = f"Ollama API error: HTTP {response.status_code}"
                print(f"[ERROR] {error}")
                if attempt < max_retries - 1:
                    print("[RETRY] Retrying...")
                    continue
                return False, None, error

            # Parse Ollama response
            ollama_data = response.json()
            llm_output = ollama_data.get("response", "")

            if not llm_output:
                error = "Empty response from Ollama"
                print(f"[ERROR] {error}")
                if attempt < max_retries - 1:
                    continue
                return False, None, error

            # Try to parse JSON
            try:
                parsed = json.loads(llm_output)

                # Validate schema
                if validate_pandemonium_schema(parsed):
                    print("[OK] Valid Pandemonium scenario generated!")
                    return True, parsed, None
                else:
                    error = "Schema validation failed - missing required fields"
                    print(f"[ERROR] {error}")
                    if attempt < max_retries - 1:
                        print("[RETRY] Retrying with stricter prompt...")
                        # Add stricter instructions for retry
                        full_prompt += "\n\nIMPORTANT: You MUST include ALL required fields: mode, scenario_name, mission_briefing, time_compression_factor, global_modifiers, waves"
                        continue
                    return False, None, error

            except json.JSONDecodeError as e:
                error = f"JSON parse error: {str(e)}"
                print(f"[ERROR] {error}")
                print(f"Raw output: {llm_output[:200]}...")
                if attempt < max_retries - 1:
                    print("[RETRY] Retrying...")
                    continue
                return False, None, error

        except requests.exceptions.ConnectionError:
            error = "Cannot connect to Ollama server. Is it running? Start with: ollama serve"
            print(f"[ERROR] {error}")
            return False, None, error

        except requests.exceptions.Timeout:
            error = f"Request timeout after {TIMEOUT_SECONDS}s"
            print(f"[ERROR] {error}")
            if attempt < max_retries - 1:
                print("[RETRY] Retrying...")
                continue
            return False, None, error

        except Exception as e:
            error = f"Unexpected error: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error}")
            return False, None, error

    return False, None, "Max retries exceeded"


def validate_pandemonium_schema(data: Dict) -> bool:
    """
    Validate LLM output against required Pandemonium schema.

    Args:
        data: Parsed JSON from LLM

    Returns:
        True if valid, False otherwise

    Required schema:
        {
            "mode": "PANDEMONIUM",
            "scenario_name": str,
            "mission_briefing": str,
            "time_compression_factor": int,
            "global_modifiers": {
                "radio_congestion": float,
                "unit_fatigue_rate": float,
                "dispatch_delay_seconds": int,
                "ems_delayed": bool
            },
            "waves": [
                {
                    "t_plus_seconds": int,
                    "wave_name": str,
                    "clusters": [
                        {
                            "cell_id": str,
                            "incident_type": str,
                            "severity": int,
                            "count": int,
                            "spread_radius_cells": int,
                            "cascade": [...]  # optional
                        }
                    ]
                }
            ]
        }
    """
    # Check top-level fields
    required_fields = [
        "mode", "scenario_name", "mission_briefing",
        "time_compression_factor", "global_modifiers", "waves"
    ]

    for field in required_fields:
        if field not in data:
            print(f"[ERROR] Missing field: {field}")
            return False

    # Validate mode
    if data["mode"] != "PANDEMONIUM":
        print(f"[ERROR] Invalid mode: {data['mode']} (expected 'PANDEMONIUM')")
        return False

    # Validate global_modifiers structure
    modifiers = data.get("global_modifiers", {})
    required_modifiers = ["radio_congestion", "unit_fatigue_rate", "dispatch_delay_seconds"]
    for mod in required_modifiers:
        if mod not in modifiers:
            print(f"[ERROR] Missing modifier: {mod}")
            return False

    # Validate waves structure
    waves = data.get("waves", [])
    if not isinstance(waves, list) or len(waves) == 0:
        print("[ERROR] Waves must be a non-empty list")
        return False

    for i, wave in enumerate(waves):
        # Check wave fields
        if "t_plus_seconds" not in wave:
            print(f"[ERROR] Wave {i}: missing t_plus_seconds")
            return False
        if "clusters" not in wave:
            print(f"[ERROR] Wave {i}: missing clusters")
            return False

        # Check clusters
        clusters = wave.get("clusters", [])
        if not isinstance(clusters, list) or len(clusters) == 0:
            print(f"[ERROR] Wave {i}: clusters must be non-empty list")
            return False

        for j, cluster in enumerate(clusters):
            required_cluster_fields = ["cell_id", "incident_type", "severity", "count"]
            for field in required_cluster_fields:
                if field not in cluster:
                    print(f"[ERROR] Wave {i}, Cluster {j}: missing {field}")
                    return False

    return True


def test_ollama_connection() -> Tuple[bool, str]:
    """
    Test if Ollama is running and accessible.

    Returns:
        Tuple of (is_running: bool, message: str)
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "unknown") for m in models]
            return True, f"Ollama running. Available models: {', '.join(model_names)}"
        else:
            return False, f"Ollama responded with HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Ollama not running. Start with: ollama serve"
    except Exception as e:
        return False, f"Error checking Ollama: {str(e)}"

"""
Configuration for LLM prediction and ambulance optimization.
"""

# Ollama API Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_TEMPERATURE = 0.7
OLLAMA_MAX_TOKENS = 8000

# Ambulance Optimization Defaults
DEFAULT_NUM_AMBULANCES = 5
DEFAULT_COVERAGE_RADIUS_KM = 5.0
DEFAULT_DECAY_FUNCTION = "linear"  # "linear" or "exponential"

# Optimization Algorithm
OPTIMIZATION_METHOD = "greedy"  # "greedy" or "simulated_annealing"

# Prediction Limits
MAX_PREDICTED_INCIDENTS = 20  # Maximum number of predicted incidents to return


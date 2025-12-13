"""
Runner script for Phase 2: Spatial and Temporal Structuring
"""

from src.enrich_incidents import enrich


if __name__ == "__main__":
    print("Starting Phase 2: Spatial and Temporal Structuring")
    print("-" * 50)
    enrich()

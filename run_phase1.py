"""
Runner script for Phase 1: Data Ingestion
"""

from src.ingest_incidents import ingest


if __name__ == "__main__":
    print("Starting Phase 1: Data Ingestion")
    print("-" * 50)
    ingest()

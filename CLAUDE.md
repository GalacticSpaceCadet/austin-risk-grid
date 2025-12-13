# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Traffic Agent Project - A data processing pipeline for traffic data analysis using Python and pandas.

## Development Commands

**Data Processing:**
```bash
python build_training_table.py
```
This command formats and processes traffic data for training purposes.

## Architecture

This is an early-stage project focused on traffic data analysis:

1. **Data Pipeline**: CSV data ingestion → pandas processing → training table generation
2. **Core Script**: `build_training_table.py` handles data formatting and table construction

The project expects CSV format data files that will be processed through pandas for analysis and training.

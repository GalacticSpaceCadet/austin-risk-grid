@echo off
echo Starting Austin Risk Grid Dashboard...
call venv\Scripts\activate
streamlit run app/dashboard.py

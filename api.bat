CALL deactivate
CALL venv/Scripts/activate.bat
CALL uvicorn src.api.api:app --workers 1
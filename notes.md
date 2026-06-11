# Installing Dependencies
pip install -r requirements.txt

# Creating a virtual environment
python -m venv .venv

# Running FastAPI APP

fastapi dev

# Using uvcorn

uvicorn main:app --reload --port 8000
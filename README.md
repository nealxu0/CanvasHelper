# CanvasHelper

This project is a hackathon prototype that fetches assignments from OSU Canvas (Carmen), summarizes them with a local LLM (Ollama), and generates a schedule using a Random Forest model.

---

## Project Structure

- `frontend/` – React app (UI)
- `backend/` – Flask backend
  - `main.py` – Flask entry point
  - `requirements.txt` – backend dependencies
  - `.env` – API tokens and secrets (not committed)
  - `models/` – trained ML models (`.pkl`)
  - `train_model.py` – script to train sklearn model
  - `utils/`
    - `canvas_parser.py` – cleans and formats Canvas assignment data
- `README.md` – this file

---

## Setup Instructions

### Frontend Setup (React)

```bash
cd frontend
npm i
npm run dev
```

### will run on localhost:3000

---

### Backend Setup (Flask)

```bash
cd backend
python3 -m venv venv
python -m venv venv
source venv/bin/activate
venv\Scripts\activate
pip install -r requirements.txt
```

---

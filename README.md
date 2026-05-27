# Kidney Disease Risk Predictor API

An intelligent kidney disease risk predictor built from a clinical dataset and wrapped in a FastAPI service for deployment.

## Project Overview

This repository includes:

- `Intelligent_Self_Learning_Kidney_Disease_Risk_Predictor_json.ipynb` — notebook with preprocessing, model training, SHAP explainability, and an interactive self-learning demonstration.
- `kidney_predictor.py` — reusable model loader, predictor, feedback loop, and artifact persistence.
- `app.py` — FastAPI application exposing prediction and feedback endpoints.
- `requirements.txt` — Python dependencies.
- `Dockerfile` — container image definition for cloud deployment.
- `Procfile` — process startup command for platform services.
- `DEPLOYMENT.md` — deployment guidance for Render, Railway, Azure, and Docker.
- `kidney_disease.csv` — source dataset.

## Features

- Binary kidney disease risk classification (`ckd` vs `notckd`)
- Probabilistic risk scoring and risk tier assignment
- Clinical recommendation generation
- Self-learning feedback loop with optional retraining trigger
- FastAPI endpoints for easy integration
- Docker-ready for cloud deployment

## Requirements

- Python 3.14
- `pip`

## Setup

1. Create or activate your Python environment.

2. Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Ensure the dataset `kidney_disease.csv` is present in the repository root.

## Running Locally

### Start the API

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Test the service

```bash
curl http://127.0.0.1:8000/
```

### Example prediction request

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_data": {"age": 65.0, "bp": 140.0, "sg": 1.010, "al": 3.0, "su": 2.0, "rbc": "abnormal", "pc": "abnormal", "pcc": "present", "ba": "notpresent", "bgr": 180.0, "bu": 58.0, "sc": 3.5, "sod": 132.0, "pot": 5.2, "hemo": 8.5, "pcv": 26.0, "wc": 11000.0, "rc": 3.1, "htn": "yes", "dm": "yes", "cad": "yes", "appet": "poor", "pe": "yes", "ane": "yes"}}'
```

## API Endpoints

- `GET /` — service status and model metadata
- `GET /health` — health check
- `POST /predict` — return risk prediction for a patient record
- `POST /feedback` — submit clinician feedback and accumulate retraining data
- `GET /metadata` — retrieve model and feature metadata

## Docker Deployment

Build the Docker image:

```bash
docker build -t kidney-risk-api .
```

Run the container locally:

```bash
docker run -p 8000:8000 kidney-risk-api
```

## Cloud Deployment

See `DEPLOYMENT.md` for recommended deployment options including Render, Railway, Azure App Service, and generic Docker-based hosts.

## Notes

- The API will train a fallback model automatically when no prebuilt artifact is found.
- Feedback is stored in memory and triggers a retrain once the set threshold is reached.
- For production, use a persistent model registry, secure data transport, and audit logging.

## License

This project is released under the MIT License.

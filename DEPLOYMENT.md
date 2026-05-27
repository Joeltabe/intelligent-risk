# Deployment Guide

This project provides a FastAPI web service for the Kidney Disease Risk Predictor.

## Files created
- `app.py` - FastAPI application exposing `/predict`, `/feedback`, `/metadata`, and health endpoints.
- `kidney_predictor.py` - model loader, training fallback, prediction, and retraining logic.
- `requirements.txt` - Python dependencies for runtime.
- `Dockerfile` - container definition for cloud deployment.
- `Procfile` - process command for platforms that use Procfile detection.

## Local run
1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Start the API:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```
3. Test the root endpoint:
   ```bash
   curl http://127.0.0.1:8000/
   ```

## Cloud deployment options

### Option 1: Render (recommended)
1. Push the repo to GitHub.
2. Create a new Web Service in Render.
3. Select the GitHub repo and branch.
4. Choose Docker as the environment.
5. Set the port to `8000` if prompted.
6. Deploy.

### Option 2: Railway
1. Connect your GitHub repository to Railway.
2. Create a new service using the Docker deployment option.
3. Railway will build the container using `Dockerfile`.
4. Set the start command to:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port $PORT
   ```

### Option 3: Azure App Service (Container)
1. Build and push the Docker image to Azure Container Registry.
2. Create an Azure Web App for Containers and point it to the image.
3. Ensure the container port is configured to `8000`.

### Option 4: Any Docker-compatible cloud
Build locally:
```bash
docker build -t kidney-risk-api .
```
Run locally:
```bash
docker run -p 8000:8000 kidney-risk-api
```

## API endpoints
- `GET /` - service status
- `GET /health` - health check
- `POST /predict` - predict risk
- `POST /feedback` - submit clinician feedback
- `GET /metadata` - model metadata

## Example request
```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"patient_data": {"age": 65.0, "bp": 140.0, "sg": 1.010, "al": 3.0, "su": 2.0, "rbc": "abnormal", "pc": "abnormal", "pcc": "present", "ba": "notpresent", "bgr": 180.0, "bu": 58.0, "sc": 3.5, "sod": 132.0, "pot": 5.2, "hemo": 8.5, "pcv": 26.0, "wc": 11000.0, "rc": 3.1, "htn": "yes", "dm": "yes", "cad": "yes", "appet": "poor", "pe": "yes", "ane": "yes"}}'
```

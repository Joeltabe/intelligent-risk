from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from kidney_predictor import load_predictor, KidneyRiskPredictor

app = FastAPI(
    title='Kidney Disease Risk Predictor API',
    version='1.0.0',
    description='A FastAPI service for kidney disease risk scoring, recommendations, and feedback-driven retraining.'
)

predictor: KidneyRiskPredictor = load_predictor()


class PatientRequest(BaseModel):
    patient_data: Dict[str, Any]


class FeedbackRequest(BaseModel):
    patient_data: Dict[str, Any]
    actual_label: str


@app.get('/')
def read_root() -> Dict[str, Any]:
    return {
        'status': 'ok',
        'model_version': predictor.version,
        'training_timestamp': predictor.training_timestamp,
        'feature_count': len(predictor.feature_names)
    }


@app.get('/health')
def health_check() -> Dict[str, str]:
    return {'status': 'healthy'}


@app.post('/predict')
def predict_risk(request: PatientRequest) -> Dict[str, Any]:
    try:
        return predictor.predict(request.patient_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post('/feedback')
def ingest_feedback(request: FeedbackRequest) -> Dict[str, Any]:
    try:
        predictor.learn_from_feedback(request.patient_data, request.actual_label)
        return {
            'status': 'accepted',
            'feedback_records': len(predictor.feedback_buffer),
            'model_version': predictor.version
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get('/metadata')
def metadata() -> Dict[str, Any]:
    return {
        'model_version': predictor.version,
        'training_timestamp': predictor.training_timestamp,
        'feature_names': predictor.feature_names,
        'numeric_features': predictor.numeric_features,
        'categorical_features': predictor.categorical_features
    }

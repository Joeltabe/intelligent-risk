from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Dict

from kidney_predictor import load_predictor, KidneyRiskPredictor

app = FastAPI(
    title='Kidney Disease Risk Predictor API',
    version='1.0.0',
    description='A FastAPI service for kidney disease risk scoring, recommendations, and feedback-driven retraining.'
)

predictor: KidneyRiskPredictor = load_predictor()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class PatientRequest(BaseModel):
    patient_data: Dict[str, Any]


class FeedbackRequest(BaseModel):
    patient_data: Dict[str, Any]
    actual_label: str = Field(..., description="True outcome label: ckd|notckd")
    predicted_label: str | None = Field(default=None, description="Optional frontend predicted label")
    case_id: str | None = Field(default=None, description="Optional client case identifier")


@app.get('/')
def read_root() -> Dict[str, Any]:
    return {
        'status': 'ok',
        'model_version': predictor.version,
        'training_timestamp': predictor.training_timestamp,
        'feature_count': len(predictor.feature_names),
        'model_used': predictor.get_model_used()
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
        return predictor.learn_from_feedback(
            request.patient_data,
            request.actual_label,
            request.predicted_label,
            request.case_id
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get('/metadata')
def metadata() -> Dict[str, Any]:
    return {
        'model_version': predictor.version,
        'training_timestamp': predictor.training_timestamp,
        'feature_names': predictor.feature_names,
        'numeric_features': predictor.numeric_features,
        'categorical_features': predictor.categorical_features,
        'model_used': predictor.get_model_used(),
        'retrain_threshold': predictor.retrain_threshold
    }

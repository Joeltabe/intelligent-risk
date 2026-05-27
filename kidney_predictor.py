import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

try:
    import shap
except ImportError:
    shap = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

DEFAULT_MODEL_PATH = Path('model/kidney_risk_api.pkl')
DEFAULT_DATA_PATH = Path('kidney_disease.csv')


def load_kidney_data(filepath: str) -> pd.DataFrame:
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Kidney dataset not found at: {filepath}")

    if filepath.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(filepath)
    else:
        df = pd.read_csv(filepath, encoding='utf-8-sig', on_bad_lines='warn')

    if 'id' in df.columns:
        df = df.drop(columns=['id'])

    required = ['classification', 'age', 'bp']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    num_cols = ['sg', 'al', 'su', 'bgr', 'bu', 'sc', 'sod', 'pot', 'hemo', 'pcv', 'wc', 'rc']
    for col in num_cols:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = pd.to_numeric(df[col], errors='coerce')

    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.strip().str.lower().replace('nan', np.nan)

    return df


class KidneyRiskPredictor:
    RISK_TIERS = {
        'Low': (0.0, 0.25),
        'Moderate': (0.25, 0.50),
        'High': (0.50, 0.75),
        'Critical': (0.75, 1.0)
    }

    CLINICAL_RECOMMENDATIONS = {
        'age': 'Evaluate for age-related decline in kidney function. Consider annual eGFR screening for individuals over 60.',
        'bp': 'Intensified blood pressure monitoring. Lifestyle modifications (DASH diet, exercise). Review antihypertensive therapy.',
        'sg': 'Urine specific gravity test to assess concentrating ability. Advise on adequate hydration.',
        'al': 'Urine albumin-to-creatinine ratio (ACR) or 24-hour protein. Investigate proteinuria sources.',
        'su': 'Fasting glucose, HbA1c, or oral glucose tolerance test. Manage diabetes carefully.',
        'bgr': 'Blood glucose control and diabetes monitoring. Consider endocrinology referral.',
        'bu': 'Blood urea nitrogen to assess kidney function and hydration. Review protein intake.',
        'sc': 'Serum creatinine and eGFR calculation. Nephrology consult if eGFR < 60 mL/min/1.73m^2.',
        'sod': 'Serum sodium evaluation. Assess fluid balance and diuretic use for dysnatremia.',
        'pot': 'Serum potassium monitoring. Manage hyperkalemia/hypokalemia with medication review.',
        'hemo': 'Complete blood count for anemia. Evaluate iron studies and CKD-related anemia.',
        'pcv': 'Hematocrit assessment. Investigate anemia or polycythemia causes.',
        'wc': 'White blood cell count evaluation for infection or inflammation. Perform differential testing.',
        'rc': 'Red blood cell count assessment for anemia or erythrocytosis.',
        'htn': 'Aggressive blood pressure control and review antihypertensive regimen.',
        'dm': 'Tight glycemic control, HbA1c monitoring, and diabetic complication screening.',
        'cad': 'Cardiovascular risk reduction, stress testing, and cardiology referral as needed.',
        'appet': 'Nutritional evaluation and dietary counseling for poor appetite or uremia.',
        'pe': 'Assess fluid overload and edema. Consider diuretics and nephrology evaluation.',
        'ane': 'Anemia workup including iron studies, B12, folate, and possible ESA therapy.'
    }

    def __init__(self, model_type: str = 'random_forest', retrain_threshold: int = 20):
        self.model_type = model_type
        self.retrain_threshold = retrain_threshold
        self.pipeline: Optional[Pipeline] = None
        self.target_encoder = None
        self.feature_names: List[str] = []
        self.numeric_features: List[str] = []
        self.categorical_features: List[str] = []
        self.shap_explainer = None
        self.feedback_buffer = pd.DataFrame()
        self.version = '1.0.0'
        self.training_timestamp: Optional[str] = None

    def get_model_used(self) -> str:
        if self.pipeline is None:
            return self.model_type
        classifier = self.pipeline.named_steps.get('classifier')
        return classifier.__class__.__name__ if classifier is not None else self.model_type

    def build_pipeline(self, X: pd.DataFrame) -> None:
        self.numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
        self.feature_names = self.numeric_features + self.categorical_features

        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='mean'))
        ])
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('ordinal', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
        ])

        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features)
            ],
            remainder='drop',
            sparse_threshold=0
        )

        if self.model_type == 'logistic':
            estimator = LogisticRegression(random_state=42, max_iter=1000, n_jobs=-1)
        else:
            estimator = RandomForestClassifier(random_state=42, n_jobs=-1, n_estimators=150, max_depth=12)

        self.pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('scaler', StandardScaler()),
            ('classifier', estimator)
        ])

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        if self.pipeline is None:
            self.build_pipeline(X)

        y_clean = pd.Series(y).astype(str).str.strip().str.lower()
        self.target_encoder = LabelEncoder()
        y_enc = self.target_encoder.fit_transform(y_clean)

        self.pipeline.fit(X, y_enc)
        self.training_timestamp = pd.Timestamp.now().isoformat()
        logger.info('Model trained successfully.')

    def _get_risk_tier(self, prob: float) -> str:
        for tier, (low, high) in self.RISK_TIERS.items():
            if low <= prob < high:
                return tier
        return 'Critical'

    def _generate_recommendations(self, patient_df: pd.DataFrame, prob: float, top_risk_drivers: List[str]) -> List[str]:
        recs: List[str] = []
        if prob > 0.25:
            recs.append('Routine kidney function panel (eGFR, creatinine, BUN).')
        if prob > 0.50:
            recs.append('Nephrology specialist referral for further evaluation.')

        for driver in top_risk_drivers:
            if driver in self.CLINICAL_RECOMMENDATIONS:
                recs.append(f"Address {driver.upper()}: {self.CLINICAL_RECOMMENDATIONS[driver]}")

        for feat, val in patient_df.iloc[0].items():
            if feat in self.CLINICAL_RECOMMENDATIONS and feat not in top_risk_drivers:
                if pd.isna(val) or str(val).strip().lower() in {'', 'missing', 'nan'}:
                    recs.append(f"Consider {self.CLINICAL_RECOMMENDATIONS[feat]}")
                elif feat == 'bp' and pd.to_numeric(val, errors='coerce') > 140:
                    recs.append(f"Elevated BP detected ({val}). {self.CLINICAL_RECOMMENDATIONS[feat]}")
                elif feat == 'sc' and pd.to_numeric(val, errors='coerce') > 1.5:
                    recs.append(f"Elevated serum creatinine detected ({val}). {self.CLINICAL_RECOMMENDATIONS[feat]}")
                elif feat == 'al' and pd.to_numeric(val, errors='coerce') > 2:
                    recs.append(f"Elevated albuminuria detected ({val}). {self.CLINICAL_RECOMMENDATIONS[feat]}")

        return list(dict.fromkeys(recs))

    def predict(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.pipeline is None:
            raise RuntimeError('Model not trained.')

        df_in = pd.DataFrame([patient_data])
        df_in = df_in.reindex(columns=self.feature_names, fill_value=np.nan)

        proba = self.pipeline.predict_proba(df_in)[0]
        ckd_index = 1
        if self.target_encoder is not None and hasattr(self.target_encoder, 'classes_'):
            if 'ckd' in self.target_encoder.classes_:
                ckd_index = int(np.where(self.target_encoder.classes_ == 'ckd')[0][0])
            elif len(self.target_encoder.classes_) > 1:
                ckd_index = 1
            else:
                ckd_index = 0

        risk_probability = float(proba[ckd_index])
        tier = self._get_risk_tier(risk_probability)
        recommendations = self._generate_recommendations(df_in, risk_probability, [])

        return {
            'risk_probability': round(risk_probability, 4),
            'risk_tier': tier,
            'recommendations': recommendations,
            'top_risk_drivers': [],
            'model_version': self.version,
            'model_used': self.get_model_used(),
            'confidence': 'High' if risk_probability > 0.8 or risk_probability < 0.2 else 'Moderate',
            'raw_patient_data': patient_data
        }

    def learn_from_feedback(self, patient_data: Dict[str, Any], actual_label: str, predicted_label: Optional[str] = None, case_id: Optional[str] = None) -> Dict[str, Any]:
        normalized_outcome = str(actual_label).strip().lower()
        if normalized_outcome not in {'ckd', 'notckd'}:
            raise ValueError("actual_label must be either 'ckd' or 'notckd'")

        if predicted_label is None:
            inference = self.predict(patient_data)
            predicted_label = 'ckd' if float(inference['risk_probability']) >= 0.5 else 'notckd'

        record = {
            **patient_data,
            'actual_outcome': normalized_outcome,
            'predicted_label': str(predicted_label).strip().lower(),
            'case_id': case_id or ''
        }
        self.feedback_buffer = pd.concat([self.feedback_buffer, pd.DataFrame([record])], ignore_index=True)
        logger.info('Stored clinician feedback (%d records total).', len(self.feedback_buffer))

        model_retrained = False
        previous_version = self.version
        if len(self.feedback_buffer) >= self.retrain_threshold:
            self._self_retrain()
            model_retrained = self.version != previous_version

        outcome_match = record['predicted_label'] == normalized_outcome
        return {
            'status': 'accepted',
            'case_id': case_id,
            'actual_label': normalized_outcome,
            'predicted_label': record['predicted_label'],
            'prediction_match': outcome_match,
            'feedback_records': len(self.feedback_buffer),
            'model_retrained': model_retrained,
            'model_version': self.version,
            'model_used': self.get_model_used()
        }

    def _self_retrain(self) -> None:
        X_new = self.feedback_buffer.drop(columns=['actual_outcome', 'predicted_label', 'case_id'], errors='ignore')
        y_new = self.feedback_buffer['actual_outcome']
        self.version = f"{float(self.version) + 0.1:.1f}"
        self.build_pipeline(X_new)
        self.train(X_new, y_new)
        self.feedback_buffer = pd.DataFrame()
        logger.info('Model self-retrained to version %s.', self.version)

    def save_artifacts(self, path: str = str(DEFAULT_MODEL_PATH)) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            'model_type': self.model_type,
            'pipeline': self.pipeline,
            'target_encoder': self.target_encoder,
            'feature_names': self.feature_names,
            'numeric_features': self.numeric_features,
            'categorical_features': self.categorical_features,
            'version': self.version,
            'training_timestamp': self.training_timestamp
        }
        joblib.dump(artifact, str(p))
        logger.info('Saved model artifact to %s.', p)


def load_predictor(model_path: Path = DEFAULT_MODEL_PATH, data_path: Path = DEFAULT_DATA_PATH) -> KidneyRiskPredictor:
    predictor = None
    if model_path.exists():
        try:
            raw = joblib.load(str(model_path))
            if isinstance(raw, dict):
                predictor = KidneyRiskPredictor(model_type=raw.get('model_type', 'random_forest'))
                predictor.pipeline = raw['pipeline']
                predictor.target_encoder = raw['target_encoder']
                predictor.feature_names = raw['feature_names']
                predictor.numeric_features = raw['numeric_features']
                predictor.categorical_features = raw['categorical_features']
                predictor.version = raw.get('version', '1.0.0')
                predictor.training_timestamp = raw.get('training_timestamp')
            else:
                predictor = raw
        except Exception as exc:
            logger.warning('Could not load existing artifact: %s', exc)
            predictor = None

    if predictor is None:
        df = load_kidney_data(str(data_path))
        df = df[df['classification'].isin(['ckd', 'notckd'])].copy()
        X = df.drop(columns=['classification'])
        y = df['classification']
        predictor = KidneyRiskPredictor()
        predictor.build_pipeline(X)
        predictor.train(X, y)
        predictor.save_artifacts(str(model_path))

    return predictor

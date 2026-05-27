# Kidney Disease Risk Predictor API

An intelligent kidney disease risk predictor built from a clinical dataset and exposed through a FastAPI service.

This README is a practical integration guide for teams that have already deployed (for example, on Railway) and now need to connect web/mobile/backend apps to the API.

---

## 1) What you deployed on Railway

Your Railway service is a REST API with these endpoints:

- `GET /` → status and model metadata
- `GET /health` → liveness check
- `GET /metadata` → feature/schema metadata
- `POST /predict` → risk prediction for one patient payload
- `POST /feedback` → submit true clinical outcome + optional frontend prediction for quality feedback learning

These routes are defined in `app.py` and executed by FastAPI. The prediction logic and model artifacts are handled in `kidney_predictor.py`.

---

## 2) Get your Railway API base URL

After deployment, Railway gives you a public domain, such as:

- `https://web-production-a106d9.up.railway.app`

Use that as your `BASE_URL` in all requests below.

Example:

```bash
BASE_URL="https://web-production-a106d9.up.railway.app"
```

---

## 3) Verify your API is reachable

### Health check

```bash
curl "$BASE_URL/health"
```

Expected response:

```json
{"status":"healthy"}
```

### Root status

```bash
curl "$BASE_URL/"
```

Example response:

```json
{
  "status": "ok",
  "model_version": "1.0.0",
  "training_timestamp": "2026-05-27T12:34:56.000000",
  "feature_count": 24,
  "model_used": "RandomForestClassifier"
}
```

---

## 4) Required input fields for prediction

The API expects a JSON object with this shape:

```json
{
  "patient_data": {
    "age": 65.0,
    "bp": 140.0,
    "sg": 1.01,
    "al": 3.0,
    "su": 2.0,
    "rbc": "abnormal",
    "pc": "abnormal",
    "pcc": "present",
    "ba": "notpresent",
    "bgr": 180.0,
    "bu": 58.0,
    "sc": 3.5,
    "sod": 132.0,
    "pot": 5.2,
    "hemo": 8.5,
    "pcv": 26.0,
    "wc": 11000.0,
    "rc": 3.1,
    "htn": "yes",
    "dm": "yes",
    "cad": "yes",
    "appet": "poor",
    "pe": "yes",
    "ane": "yes"
  }
}
```

### Feature list (24 fields)

Numeric (send as numbers if possible):

- `age`, `bp`, `sg`, `al`, `su`, `bgr`, `bu`, `sc`, `sod`, `pot`, `hemo`, `pcv`, `wc`, `rc`

Categorical (send as strings):

- `rbc`, `pc`, `pcc`, `ba`, `htn`, `dm`, `cad`, `appet`, `pe`, `ane`

### Are all fields mandatory?

- Best practice: send all 24 fields for most accurate output.
- If a field is missing, the model pipeline imputes missing values internally.
- Unknown categorical values are safely encoded with fallback handling.

---


---

## 4.1) Full variable reference (meaning + how frontend should use each field)

This section is for frontend/backend integrators so you can map each variable to a form field, validation rule, and UX hint.

### A) Request body wrapper

- `patient_data` (object): Container for all clinical input variables used by the model.
  - Frontend use: Build a single object from your form and send as `{ "patient_data": {...} }`.

### B) Input variables used by the model (inside `patient_data`)

#### Demographics & vitals

- `age` (number): Patient age in years.
  - Typical use: Numeric input.
  - Why it matters: Kidney risk increases with age.

- `bp` (number): Blood pressure (typically systolic mmHg in this dataset).
  - Typical use: Numeric input.
  - Why it matters: Hypertension is strongly associated with kidney damage.

#### Urine/lab numeric markers

- `sg` (number): Urine specific gravity.
  - Use: Decimal numeric input (e.g., `1.010`).
  - Meaning: Kidney concentrating ability marker.

- `al` (number): Albumin in urine (proteinuria grade/level).
  - Use: Numeric input.
  - Meaning: Higher albumin generally indicates kidney injury.

- `su` (number): Sugar in urine.
  - Use: Numeric input.
  - Meaning: Can correlate with diabetes-related kidney risk.

- `bgr` (number): Blood glucose random.
  - Use: Numeric input.
  - Meaning: Hyperglycemia contributes to CKD risk.

- `bu` (number): Blood urea.
  - Use: Numeric input.
  - Meaning: Elevated values may indicate impaired kidney clearance.

- `sc` (number): Serum creatinine.
  - Use: Numeric input.
  - Meaning: Key renal function marker.

- `sod` (number): Serum sodium.
  - Use: Numeric input.
  - Meaning: Electrolyte balance marker.

- `pot` (number): Serum potassium.
  - Use: Numeric input.
  - Meaning: Kidney dysfunction can alter potassium levels.

- `hemo` (number): Hemoglobin.
  - Use: Numeric input.
  - Meaning: CKD can be associated with anemia.

- `pcv` (number): Packed cell volume / hematocrit.
  - Use: Numeric input.
  - Meaning: Helps evaluate anemia/hematologic status.

- `wc` (number): White blood cell count.
  - Use: Numeric input.
  - Meaning: Infection/inflammation context.

- `rc` (number): Red blood cell count.
  - Use: Numeric input.
  - Meaning: Low values can indicate anemia patterns seen in CKD.

#### Categorical clinical indicators

- `rbc` (string): Red blood cells in urine (`normal`/`abnormal`).
- `pc` (string): Pus cells (`normal`/`abnormal`).
- `pcc` (string): Pus cell clumps (`present`/`notpresent`).
- `ba` (string): Bacteria (`present`/`notpresent`).
- `htn` (string): Hypertension history (`yes`/`no`).
- `dm` (string): Diabetes mellitus (`yes`/`no`).
- `cad` (string): Coronary artery disease (`yes`/`no`).
- `appet` (string): Appetite (`good`/`poor`).
- `pe` (string): Pedal edema (`yes`/`no`).
- `ane` (string): Anemia (`yes`/`no`).

Frontend guidance for categorical variables:

- Prefer dropdown/radio controls to avoid spelling errors.
- Send lowercase canonical values (`yes`, `no`, `present`, `notpresent`, `normal`, `abnormal`, etc.).
- If unknown, you may omit the field; model preprocessing imputes missing values.

### C) Feedback endpoint additional variables

- `actual_label` (string, required): Ground-truth clinical outcome. Allowed: `ckd` or `notckd`.
  - Use: Submit once real diagnosis/outcome is known.

- `predicted_label` (string, optional): Label predicted by your app/model at decision time.
  - Use: Enables direct prediction-vs-outcome matching in API response.

- `case_id` (string, optional): Your frontend/backend case identifier (visit ID, encounter ID, etc.).
  - Use: Traceability for audit/history screens.

### D) Key response variables from `/predict`

- `risk_probability` (number): Probability of CKD class.
- `risk_tier` (string): Tier derived from probability (`Low`, `Moderate`, `High`, `Critical`).
- `recommendations` (array[string]): Clinical next-step guidance text.
- `model_version` (string): Version of currently loaded model.
- `model_used` (string): Classifier type currently serving requests (e.g., `RandomForestClassifier`).
- `confidence` (string): Heuristic confidence bucket from probability.
- `raw_patient_data` (object): Echo of submitted input.

Frontend UX suggestion:

- Show both `risk_probability` and `risk_tier` together.
- Render `recommendations` as bullet points.
- Display `model_version` + `model_used` in a “Model Info” section for transparency.

### E) Key response variables from `/feedback`

- `status`: Feedback acceptance status.
- `prediction_match` (boolean): Whether `predicted_label` matches `actual_label`.
- `feedback_records` (number): Current buffered feedback records count.
- `model_retrained` (boolean): True when retrain threshold is hit and model refreshed.
- `model_version` / `model_used`: Post-feedback serving model details.


## 5) Call the prediction endpoint

### Linux / macOS / Git Bash
```bash
curl -X POST "$BASE_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{
```

### Windows PowerShell
PowerShell's `curl` is an alias for `Invoke-WebRequest`. Use `curl.exe` for the real curl:

```powershell
curl.exe -X POST "$BASE_URL/predict" `
  -H "Content-Type: application/json" `
  -d '{\"patient_data\":{\"age\":65,\"bp\":140,\"sg\":1.01,\"al\":3,\"su\":2,\"bgr\":180,\"bu\":58,\"sc\":3.5,\"sod\":132,\"pot\":5.2,\"hemo\":8.5,\"pcv\":26,\"wc\":11000,\"rc\":3.1,\"rbc\":\"abnormal\",\"pc\":\"abnormal\",\"pcc\":\"present\",\"ba\":\"notpresent\",\"htn\":\"yes\",\"dm\":\"yes\",\"cad\":\"yes\",\"appet\":\"poor\",\"pe\":\"yes\",\"ane\":\"yes\"}}'
```



### Full JSON payload reference
```json
{
  "patient_data": {
    "age": 65.0,
    "bp": 140.0,
    "sg": 1.010,
    "al": 3.0,
    "su": 2.0,
    "rbc": "abnormal",
    "pc": "abnormal",
    "pcc": "present",
    "ba": "notpresent",
    "bgr": 180.0,
    "bu": 58.0,
    "sc": 3.5,
    "sod": 132.0,
    "pot": 5.2,
    "hemo": 8.5,
    "pcv": 26.0,
    "wc": 11000.0,
    "rc": 3.1,
    "htn": "yes",
    "dm": "yes",
    "cad": "yes",
    "appet": "poor",
    "pe": "yes",
    "ane": "yes"
  }
}
```

Example response:

```json
{
  "risk_probability": 0.9123,
  "risk_tier": "Critical",
  "recommendations": [
    "Routine kidney function panel (eGFR, creatinine, BUN).",
    "Nephrology specialist referral for further evaluation."
  ],
  "top_risk_drivers": [],
  "model_version": "1.0.0",
  "confidence": "High",
  "raw_patient_data": {
    "age": 65.0,
    "bp": 140.0
  }
}
```

---

## 6) Submit feedback (for self-learning)

Use `POST /feedback` after you later know the real outcome.

Payload format:

```json
{
  "patient_data": { "...same fields used for prediction...": "..." },
  "actual_label": "ckd",
  "predicted_label": "notckd",
  "case_id": "visit-2026-00014"
}
```

Valid labels should match training classes, typically:

- `ckd`
- `notckd`

Example:

```bash
curl -X POST "$BASE_URL/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_data": {
      "age": 52,
      "bp": 130,
      "sc": 1.8,
      "htn": "yes",
      "dm": "no"
    },
    "actual_label": "ckd"
  }'
```

Response example:

```json
{
  "status": "accepted",
  "case_id": "visit-2026-00014",
  "actual_label": "ckd",
  "predicted_label": "notckd",
  "prediction_match": false,
  "feedback_records": 4,
  "model_retrained": false,
  "model_version": "1.0.0",
  "model_used": "RandomForestClassifier"
}
```

Notes:

- Feedback is buffered in memory.
- Automatic retraining occurs when the buffer reaches the configured threshold (default: 20 records).
- In-memory feedback is not durable across container restarts unless you add persistence.

---

## 7) Connect from your app (frontend/backend/mobile)

## JavaScript / TypeScript (frontend or Node backend)

```ts
const BASE_URL = "https://web-production-a106d9.up.railway.app";

export async function predictKidneyRisk(patientData: Record<string, unknown>) {
  const res = await fetch(`${BASE_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_data: patientData }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }

  return res.json();
}
```

## Python client

```python
import requests

BASE_URL = "https://web-production-a106d9.up.railway.app"

def predict_kidney_risk(patient_data: dict) -> dict:
    response = requests.post(
        f"{BASE_URL}/predict",
        json={"patient_data": patient_data},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
```

## Mobile app (Flutter/React Native/Swift/Kotlin)

Use the same REST pattern:

- Method: `POST`
- URL: `${BASE_URL}/predict`
- Header: `Content-Type: application/json`
- Body: `{ "patient_data": { ... } }`

---

## 8) API documentation (interactive)

FastAPI auto-generates docs:

- Swagger UI: `https://web-production-a106d9.up.railway.app/docs`
- ReDoc: `https://web-production-a106d9.up.railway.app/redoc`
- OpenAPI JSON: `https://web-production-a106d9.up.railway.app/openapi.json`

If your app team needs exact request/response contracts, share the OpenAPI JSON.

---

## 9) Integration checklist

- Set a stable `BASE_URL` in your app config.
- Implement timeout + retry logic in your API client.
- Handle non-200 errors by reading `detail` from FastAPI responses.
- Validate/normalize categorical values (e.g., lowercase `yes/no`, `present/notpresent`).
- Send all 24 features where possible.
- Log request IDs and responses (excluding PHI where required).
- Gate this API behind auth in production (see security section).

---

## 10) Security and production hardening

Current code exposes open endpoints by default. Before production clinical usage, add:

- API authentication (API key, JWT, OAuth2, or mTLS)
- HTTPS-only access and secure secret storage
- CORS policy restricted to trusted origins
- Rate limiting and abuse controls
- Structured audit logging with PII/PHI controls
- Persistent storage for feedback and model versions
- Monitoring/alerting for uptime, latency, and model drift

---

## 11) Troubleshooting

### `400 Bad Request`

- Usually invalid payload shape or incompatible field values.
- Confirm body is wrapped as `{ "patient_data": {...} }`.

### `422 Unprocessable Entity`

- Pydantic validation failed.
- Check JSON format and top-level keys.

### `500 Internal Server Error`

- Check Railway logs for stack traces.
- Verify model artifact exists or dataset is available for fallback training.

### Model seems to ignore some fields

- Missing fields are imputed by the preprocessing pipeline.
- For best results, send complete and clean records.

---

## 12) Local development

Install and run:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Local URLs:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

---

## 13) Project structure

- `app.py` — FastAPI app + endpoint definitions
- `kidney_predictor.py` — model loading, inference, recommendations, feedback retraining
- `model/kidney_risk_api.pkl` — saved API model artifact
- `model/kidney_risk_predictor.pkl` — additional model artifact
- `DEPLOYMENT.md` — platform deployment steps (Render, Railway, Azure, Docker)
- `Dockerfile` / `Procfile` — runtime process config

---

## 14) License

This project is released under the MIT License.

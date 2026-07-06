from fastapi import FastAPI, Body
from pydantic import BaseModel
from datetime import datetime
import re

app = FastAPI(
    title="AI Services Layer - Claims Processing Engine",
    description="AI microservice evaluating healthcare claims for denial probability.",
    version="2.0.0"
)

class PredictionResponse(BaseModel):
    claimId: str
    denialScore: float
    status: str


def find_key(data, target_key, default_value=None):
    """
    Recursively search nested dict/list for a key, case-insensitive.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == target_key.lower():
                return v
            if isinstance(v, (dict, list)):
                result = find_key(v, target_key, None)
                if result is not None:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_key(item, target_key, None)
            if result is not None:
                return result
    return default_value


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def normalize_text(value):
    return str(value).strip().upper() if value is not None else ""


def calculate_age(dob_str: str):
    """
    Expects DOB in YYYY-MM-DD format.
    Returns None if parsing fails.
    """
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = datetime.today().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except Exception:
        return None


@app.post("/predict/denial-probability", response_model=PredictionResponse)
async def predict_denial(payload: dict = Body(...)):
    try:
        # -----------------------------
        # Extract claim fields from Boomi payload
        # -----------------------------
        claim_id = str(find_key(payload, "ClaimID", "CLM-DEMO-999"))

        billed_amount = safe_float(find_key(payload, "BilledAmount", 0.0))

        prior_auth = normalize_text(find_key(payload, "PriorAuth", ""))
        billing_npi = str(find_key(payload, "BillingNPI", "")).strip()
        rendering_npi = str(find_key(payload, "RenderingNPI", "")).strip()
        taxonomy = normalize_text(find_key(payload, "Taxonomy", ""))
        dob = str(find_key(payload, "DOB", "")).strip()
        gender = normalize_text(find_key(payload, "Gender", ""))

        # -----------------------------
        # Risk scoring logic
        # -----------------------------
        score = 0.12   # base denial risk

        # 1) Amount-based risk
        if billed_amount >= 15000:
            score += 0.42
        elif billed_amount >= 10000:
            score += 0.32
        elif billed_amount >= 6000:
            score += 0.22
        elif billed_amount >= 3000:
            score += 0.10

        # 2) Prior authorization quality
        # good prior auth lowers risk, weak/missing increases it
        # Examples of "good" values: PA-7788, AUTH-9901, VALID-PA-123
        if prior_auth == "" or prior_auth in {"NA", "NONE", "N/A"}:
            score += 0.22
        elif len(prior_auth) < 5:
            score += 0.12
        elif re.match(r"^(PA|AUTH|UM)-[A-Z0-9\-]+$", prior_auth):
            score -= 0.05
        else:
            score += 0.05

        # 3) Provider NPI validity checks
        # simple demo check: NPI should be 10 digits
        if not (billing_npi.isdigit() and len(billing_npi) == 10):
            score += 0.18
        if not (rendering_npi.isdigit() and len(rendering_npi) == 10):
            score += 0.18

        # 4) Taxonomy risk
        # Example heuristic:
        # 207Q... (family practice) = lower risk
        # 208D... (general practice / certain specialist buckets) = slightly higher
        # unknown/blank taxonomy = higher
        if taxonomy.startswith("207Q"):
            score -= 0.04
        elif taxonomy.startswith("208D"):
            score += 0.08
        elif taxonomy == "":
            score += 0.12
        else:
            score += 0.03

        # 5) Patient age factor
        age = calculate_age(dob)
        if age is None:
            score += 0.08
        elif age >= 70:
            score += 0.10
        elif age <= 1:
            score += 0.06

        # 6) Tiny gender sanity factor only if missing/invalid
        if gender not in {"MALE", "FEMALE", "OTHER"}:
            score += 0.03

        # -----------------------------
        # Clamp score and derive status
        # -----------------------------
        score = max(0.01, min(score, 0.99))
        status = "Rejected" if score >= 0.70 else "Approved"

        return {
            "claimId": claim_id,
            "denialScore": round(score, 4),
            "status": status
        }

    except Exception:
        # Failsafe for demo stability
        return {
            "claimId": "CLM-RESCUE",
            "denialScore": 0.12,
            "status": "Approved"
        }

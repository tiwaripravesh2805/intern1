from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import random

app = FastAPI(
    title="AI Services Layer - Claims Processing Engine",
    description="Live microservice evaluating incoming claims for Denial Probability.",
    version="1.0.0"
)

# Define sub-objects matching Boomi's nested structure
class HeaderModel(BaseModel):
    ClaimID: Optional[str] = "CLMUNKNOWN"
    SenderID: Optional[str] = None
    ReceiverID: Optional[str] = None
    Timestamp: Optional[str] = None

class PatientModel(BaseModel):
    patientId: Optional[str] = "PTUNKNOWN"
    patientAge: Optional[int] = 30
    diagnosisCode: Optional[str] = "None"

class ProviderModel(BaseModel):
    providerId: Optional[str] = "PROVUNKNOWN"
    procedureCode: Optional[str] = "None"

class FinancialModel(BaseModel):
    claimAmount: Optional[float] = 0.0
    Currency: Optional[str] = "USD"
    PriorAuth: Optional[str] = None

class AIMetadataModel(BaseModel):
    DenialScore: Optional[float] = None
    AI_Timestamp: Optional[str] = None

# Main Canonical Data Model reflecting the Boomi JSON profile
class ClaimData(BaseModel):
    Header: Optional[HeaderModel] = HeaderModel()
    Patient: Optional[PatientModel] = PatientModel()
    Provider: Optional[ProviderModel] = ProviderModel()
    Financial: Optional[FinancialModel] = FinancialModel()
    AIMetadata: Optional[AIMetadataModel] = AIMetadataModel()

class PredictionResponse(BaseModel):
    claimId: str
    denial_probability: float
    threshold_exceeded: bool
    status: str
    engine: str

@app.post("/predict/denial-probability", response_model=PredictionResponse)
async def predict_denial(claim: ClaimData):
    try:
        # Gracefully fall back to internal defaults if sub-objects or properties are missing
        header = claim.Header or HeaderModel()
        patient = claim.Patient or PatientModel()
        provider = claim.Provider or ProviderModel()
        financial = claim.Financial or FinancialModel()

        claim_id = header.ClaimID or "CLMUNKNOWN"
        claim_amount = financial.claimAmount or 0.0
        diag_code = patient.diagnosisCode or "None"

        # Core logic execution
        base_risk = 0.20
        
        # Scenario 1: High claim amounts increase denial risk
        if claim_amount > 5000:
            base_risk += 0.40
            
        # Scenario 2: Specific diagnosis prefixes add risk
        if diag_code.upper().startswith("E"):
            base_risk += 0.25
            
        # Generate final probability score bounded between 0 and 1
        final_probability = min(base_risk + random.uniform(-0.05, 0.1), 0.99)
        final_probability = max(final_probability, 0.01)
        
        # Architectural threshold rule (> 70% gets flagged for rejection)
        denial_threshold = 0.70
        is_denied = final_probability > denial_threshold
        
        return {
            "claimId": claim_id,
            "denial_probability": round(final_probability, 4),
            "threshold_exceeded": is_denied,
            "status": "Rejected" if is_denied else "Approved",
            "engine": "XGBoost-Simulation-v1"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference Engine Error: {str(e)}")

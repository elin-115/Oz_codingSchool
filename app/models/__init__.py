# alembic(env.py)이 `from app import models`로 모델을 인식하므로 모든 모델을 여기서 import
from .ai_analysis_results import AIAnalysisResult
from .medical_records import MedicalRecord
from .patients import Patient
from .users import User
from .xray_images import XrayImage

__all__ = [
    "AIAnalysisResult",
    "MedicalRecord",
    "Patient",
    "User",
    "XrayImage",
]

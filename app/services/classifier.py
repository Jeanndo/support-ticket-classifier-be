import re
import uuid
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parents[2] / "category_model.pkl"

PRIORITY_RULES: dict[str, str] = {
    "Security Issue": "High",
    "Technical Issue": "High",
    "Bug Report": "High",
    "Billing": "Medium",
    "Account Access": "Medium",
    "Feature Request": "Low",
}

TEAM_MAP: dict[str, tuple[str, str]] = {
    "Security Issue": ("Security", "security@company.com"),
    "Technical Issue": ("Engineering", "engineering@company.com"),
    "Bug Report": ("Engineering", "engineering@company.com"),
    "Billing": ("Billing", "billing@company.com"),
    "Account Access": ("Support", "support@company.com"),
    "Feature Request": ("Product", "product@company.com"),
}

SLA_MAP: dict[str, str] = {
    "High": "Respond within 1 hour",
    "Medium": "Respond within 4 hours",
    "Low": "Respond within 24 hours",
}

CRITICAL_KEYWORDS = frozenset(
    {"security", "breach", "hack", "urgent", "production", "outage", "down"}
)


class TicketClassifierService:
    _instance: "TicketClassifierService | None" = None

    def __init__(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
        self.model = joblib.load(MODEL_PATH)

    @classmethod
    def get_instance(cls) -> "TicketClassifierService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _confidence(self, proba: list[float]) -> float:
        return float(round(max(proba) * 100, 2))

    def _assessment(self, confidence: float) -> str:
        if confidence >= 90:
            return "Very High Confidence"
        if confidence >= 75:
            return "High Confidence"
        if confidence >= 60:
            return "Moderate Confidence"
        return "Low Confidence"

    def _extract_keywords(self, text: str) -> list[str]:
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        return sorted(tokens & CRITICAL_KEYWORDS)

    def _summary(self, text: str) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) <= 120:
            return cleaned
        return cleaned[:117] + "..."

    def _ticket_id(self) -> str:
        return f"TICKET-{uuid.uuid4().hex[:8].upper()}"

    def classify(self, ticket_text: str) -> dict:
        proba = self.model.predict_proba([ticket_text])[0]
        category = self.model.predict([ticket_text])[0]
        confidence = self._confidence(proba)
        priority = PRIORITY_RULES.get(category, "Medium")
        team, email = TEAM_MAP.get(category, ("Support", "support@company.com"))
        keywords = self._extract_keywords(ticket_text)
        escalation = bool(keywords)

        return {
            "ticket_id": self._ticket_id(),
            "ticket_text": ticket_text,
            "summary": self._summary(ticket_text),
            "category": category,
            "priority": priority,
            "confidence": confidence,
            "assessment": self._assessment(confidence),
            "team": team,
            "email": email,
            "sla": SLA_MAP[priority],
            "escalation": escalation,
            "keywords": keywords,
        }

"""Log type detection engine with confidence scoring."""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from core.config import get_config


@dataclass
class DetectionResult:
    """Result of log type detection."""
    log_type: str
    score: int
    confidence: str  # "high", "medium", "low"
    candidate_scores: Dict[str, int]  # all scores for debugging
    debug_breakdown: Dict[str, Any]


class DetectionEngine:
    """Detects log type based on payload fields and scoring rules."""

    def __init__(self):
        self.config = get_config()
        self.scoring = self.config.get_scoring_rules()
        self.confidence_defs = self.config.get_confidence_thresholds()

    def detect(self, payload: Dict[str, Any]) -> DetectionResult:
        """Detect log type and return result with confidence.
        
        Scoring:
        - +5 per required_all field present
        - -10 per required_all field missing
        - +2 per required_any field present (up to max benefit)
        - -100 if any forbidden_any field present
        """
        scores = {}
        breakdowns = {}
        
        for log_type in self.config.get_log_types():
            score, breakdown = self._score_type(log_type, payload)
            scores[log_type] = score
            breakdowns[log_type] = breakdown
        
        # Find winner and confidence
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        second_best_score = max(v for k, v in scores.items() if k != best_type)
        margin = best_score - second_best_score
        
        confidence = self._assess_confidence(best_score, margin)
        
        return DetectionResult(
            log_type=best_type,
            score=best_score,
            confidence=confidence,
            candidate_scores=scores,
            debug_breakdown=breakdowns
        )

    def _score_type(self, log_type: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """Score a single log type against payload."""
        rules = self.config.get_detection_rules(log_type)
        required_all = rules.get("required_all", [])
        required_any = rules.get("required_any", [])
        forbidden_any = rules.get("forbidden_any", [])
        
        score = 0
        breakdown = {
            "required_all": {},
            "required_any": {},
            "forbidden_any": {}
        }
        
        # Score required_all
        for field in required_all:
            if self._field_present(payload, field):
                score += self.scoring.get("required_all_present", 5)
                breakdown["required_all"][field] = "+5"
            else:
                score += self.scoring.get("required_all_missing", -10)
                breakdown["required_all"][field] = "-10"
        
        # Score required_any
        any_satisfied = 0
        for field in required_any:
            if self._field_present(payload, field):
                any_satisfied += 1
                breakdown["required_any"][field] = "+2"
            else:
                breakdown["required_any"][field] = "0"
        
        score += any_satisfied * self.scoring.get("required_any_present", 2)
        
        # Score forbidden_any
        for field in forbidden_any:
            if self._field_present(payload, field):
                score += self.scoring.get("forbidden_any_present", -100)
                breakdown["forbidden_any"][field] = "-100"
            else:
                breakdown["forbidden_any"][field] = "0"
        
        breakdown["total"] = score
        return score, breakdown

    def _field_present(self, payload: Dict[str, Any], field: str) -> bool:
        """Check if field is present and non-empty in payload."""
        value = payload.get(field)
        return value is not None and value != "" and value != 0

    def _assess_confidence(self, best_score: int, margin: int) -> str:
        """Determine confidence level based on score and margin."""
        # High: score >= 12 AND margin >= 5
        if best_score >= 12 and margin >= 5:
            return "high"
        # Medium: score >= 8
        if best_score >= 8:
            return "medium"
        # Low: else
        return "low"


# Singleton
_engine = None


def get_detection_engine() -> DetectionEngine:
    """Get or create detection engine singleton."""
    global _engine
    if _engine is None:
        _engine = DetectionEngine()
    return _engine

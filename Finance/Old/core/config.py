"""Load and manage log type configuration from YAML."""

import yaml
from pathlib import Path
from typing import Dict, List, Any

CONFIG_PATH = Path(__file__).parent.parent / "config" / "log_types.yml"


class LogTypeConfig:
    """Manages log type definitions and detection rules."""

    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.config = self._load_config()
        self.log_types = self.config.get("log_types", {})
        self.scoring = self.config.get("scoring", {})
        self.confidence = self.config.get("confidence", {})

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML config file."""
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def get_log_types(self) -> List[str]:
        """Return list of all log type names."""
        return list(self.log_types.keys())

    def get_fields_for_type(self, log_type: str) -> List[str]:
        """Return all fields defined for a log type."""
        if log_type not in self.log_types:
            raise ValueError(f"Unknown log type: {log_type}")
        return self.log_types[log_type].get("fields", [])

    def get_detection_rules(self, log_type: str) -> Dict[str, List[str]]:
        """Return detection rules for a log type."""
        if log_type not in self.log_types:
            raise ValueError(f"Unknown log type: {log_type}")
        return self.log_types[log_type].get("detect", {})

    def get_scoring_rules(self) -> Dict[str, int]:
        """Return scoring multipliers for detection."""
        return self.scoring

    def get_confidence_thresholds(self) -> Dict[str, str]:
        """Return confidence level definitions."""
        return self.confidence


# Singleton instance
_config_instance: LogTypeConfig = None


def get_config() -> LogTypeConfig:
    """Get or create config singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = LogTypeConfig()
    return _config_instance

import json
import os
from typing import Dict, Any

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config', 'rules')

def load_rule(filename: str) -> Dict[str, Any]:
    """Load a single JSON rule file from the config directory."""
    path = os.path.join(CONFIG_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Warning] Rule file not found: {path}")
        return {}
    except json.JSONDecodeError:
        print(f"[Error] Failed to decode JSON from {path}")
        return {}

# Load all rules into constants
SOURCE_TRUST = load_rule('source_trust.json')
SCORING_WEIGHTS = load_rule('scoring_weights.json')
ENTITY_MAP = load_rule('entity_map.json')
REGEX_PATTERNS = load_rule('regex_patterns.json')

IMPACT_HINT = SCORING_WEIGHTS.get('IMPACT_HINT', {})
CATEGORY_WEIGHT = SCORING_WEIGHTS.get('CATEGORY_WEIGHT', {})

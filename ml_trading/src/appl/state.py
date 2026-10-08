
import json
from pathlib import Path

DEFAULT = {
    "last_processed_bar": None,
    "position": 0,
    "position_notional": 0.0,
}

class StateStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return DEFAULT.copy()
        try:
            data = json.loads(self.path.read_text())
            result = DEFAULT.copy()
            result.update(data)
            return result
        except Exception:
            return DEFAULT.copy()

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, default=str))
        tmp.replace(self.path)

"""
Simple feedback system for chat responses (thumbs up/down).

Allows users to rate individual assistant messages.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class FeedbackManager:
    def __init__(self, storage_path: str = "data/feedback"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_user_file(self, user_id: str) -> Path:
        return self.storage_path / f"{user_id}.json"

    def record_feedback(
        self,
        user_id: str,
        message_index: int,
        rating: int,           # 1 for thumbs up, -1 for thumbs down
        comment: Optional[str] = None
    ):
        """Record feedback for a specific message in the user's chat history."""
        if rating not in (1, -1):
            raise ValueError("rating must be 1 (up) or -1 (down)")

        user_file = self._get_user_file(user_id)
        data = {"feedback": []}

        if user_file.exists():
            try:
                data = json.loads(user_file.read_text(encoding="utf-8"))
            except:
                pass

        if "feedback" not in data:
            data["feedback"] = []

        feedback_entry = {
            "message_index": message_index,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        }

        # Remove previous feedback for the same message_index (user can change mind)
        data["feedback"] = [
            f for f in data["feedback"]
            if f.get("message_index") != message_index
        ]

        data["feedback"].append(feedback_entry)

        user_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_user_feedback(self, user_id: str) -> List[Dict]:
        """Get all feedback given by a user."""
        user_file = self._get_user_file(user_id)
        if not user_file.exists():
            return []

        try:
            data = json.loads(user_file.read_text(encoding="utf-8"))
            return data.get("feedback", [])
        except:
            return []

    def get_feedback_summary(self, user_id: str) -> Dict:
        """Get a quick summary of user's feedback."""
        feedback = self.get_user_feedback(user_id)
        if not feedback:
            return {"total": 0, "positive": 0, "negative": 0, "with_comment": 0}

        positive = sum(1 for f in feedback if f["rating"] == 1)
        negative = sum(1 for f in feedback if f["rating"] == -1)
        with_comment = sum(1 for f in feedback if f.get("comment"))

        return {
            "total": len(feedback),
            "positive": positive,
            "negative": negative,
            "with_comment": with_comment
        }


# Singleton
feedback_manager = FeedbackManager()

"""
Simple tool usage tracking for metrics.

Stores per-user tool call counts and timestamps.
For now uses JSON files (easy to swap later).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


class ToolUsageTracker:
    def __init__(self, storage_path: str = "data/tool_usage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_user_file(self, user_id: str) -> Path:
        return self.storage_path / f"{user_id}.json"

    def _get_global_file(self) -> Path:
        return self.storage_path / "_global.json"

    def record_tool_use(self, user_id: str, tool_name: str):
        """Record that a user used a specific tool."""
        now = datetime.now().isoformat()

        # Per-user stats
        user_file = self._get_user_file(user_id)
        user_data = {"tools": {}, "last_updated": now}

        if user_file.exists():
            try:
                user_data = json.loads(user_file.read_text(encoding="utf-8"))
            except:
                pass

        if "tools" not in user_data:
            user_data["tools"] = {}

        if tool_name not in user_data["tools"]:
            user_data["tools"][tool_name] = {"count": 0, "last_used": None}

        user_data["tools"][tool_name]["count"] += 1
        user_data["tools"][tool_name]["last_used"] = now
        user_data["last_updated"] = now

        user_file.write_text(json.dumps(user_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Global stats
        global_file = self._get_global_file()
        global_data = {"tools": {}, "last_updated": now}

        if global_file.exists():
            try:
                global_data = json.loads(global_file.read_text(encoding="utf-8"))
            except:
                pass

        if "tools" not in global_data:
            global_data["tools"] = {}

        if tool_name not in global_data["tools"]:
            global_data["tools"][tool_name] = {"total_count": 0, "users": []}

        global_data["tools"][tool_name]["total_count"] += 1
        global_data["last_updated"] = now

        if user_id not in global_data["tools"][tool_name]["users"]:
            global_data["tools"][tool_name]["users"].append(user_id)

        global_file.write_text(json.dumps(global_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_user_stats(self, user_id: str) -> Dict:
        """Get tool usage stats for a specific user."""
        user_file = self._get_user_file(user_id)
        if not user_file.exists():
            return {"user_id": user_id, "tools": {}, "total_tool_calls": 0}

        try:
            data = json.loads(user_file.read_text(encoding="utf-8"))
            total = sum(t.get("count", 0) for t in data.get("tools", {}).values())
            return {
                "user_id": user_id,
                "tools": data.get("tools", {}),
                "total_tool_calls": total,
                "last_updated": data.get("last_updated")
            }
        except:
            return {"user_id": user_id, "tools": {}, "total_tool_calls": 0}

    def get_global_stats(self, top_n: int = 10) -> Dict:
        """Get global tool usage stats."""
        global_file = self._get_global_file()
        if not global_file.exists():
            return {"tools": {}, "total_tool_calls": 0, "unique_users": 0}

        try:
            data = json.loads(global_file.read_text(encoding="utf-8"))
            tools = data.get("tools", {})

            # Sort by usage
            sorted_tools = sorted(
                tools.items(),
                key=lambda x: x[1].get("total_count", 0),
                reverse=True
            )[:top_n]

            total_calls = sum(t.get("total_count", 0) for t in tools.values())
            all_users = set()
            for t in tools.values():
                all_users.update(t.get("users", []))

            return {
                "top_tools": [
                    {"tool": name, "count": stats.get("total_count", 0), "unique_users": len(stats.get("users", []))}
                    for name, stats in sorted_tools
                ],
                "total_tool_calls": total_calls,
                "unique_users": len(all_users),
                "last_updated": data.get("last_updated")
            }
        except:
            return {"tools": {}, "total_tool_calls": 0, "unique_users": 0}


# Singleton
tool_usage_tracker = ToolUsageTracker()

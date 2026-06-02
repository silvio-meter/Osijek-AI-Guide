"""
User Context & Personalization module for Osijek AI Guide (Lega)

This is the foundation for mobile-app readiness (option 2 from the vision).

Current minimal design:
- UserProfile: Basic persistent user identity + preferences
- Simple in-memory + file-based storage (can be replaced with DB later)
- Helper to inject user context into system prompts

Future extensions (when needed):
- Interests (fish, history, walking, family-friendly, etc.)
- Visited places history
- Preferred areas (Tvrđa, centar, Baranja...)
- Dietary preferences
- Notification settings
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

@dataclass
class UserProfile:
    user_id: str
    display_name: Optional[str] = None
    interests: List[str] = field(default_factory=list)          # e.g. ["fish", "history", "walking"]
    preferred_areas: List[str] = field(default_factory=list)    # e.g. ["Tvrđa", "centar", "Baranja"]
    dietary: List[str] = field(default_factory=list)            # e.g. ["fish", "vegetarian"]
    visited_places: List[str] = field(default_factory=list)
    notes: str = ""                                             # free text for future memory

    def to_prompt_context(self) -> str:
        """
        Returns a well-structured context string for the system prompt.
        Designed to be clear and actionable for the LLM.
        """
        lines = []

        if self.display_name:
            lines.append(f"- Ime korisnika: {self.display_name}")

        if self.interests:
            lines.append(f"- Interesi: {', '.join(self.interests)}")

        if self.preferred_areas:
            lines.append(f"- Preferirana područja u Osijeku: {', '.join(self.preferred_areas)}")

        if self.dietary:
            lines.append(f"- Dijetetske preferencije / ograničenja: {', '.join(self.dietary)}")

        if self.visited_places:
            recent = self.visited_places[-5:]
            lines.append(f"- Već posjetio: {', '.join(recent)}")

        if self.notes:
            lines.append(f"- Dodatne napomene: {self.notes}")

        if not lines:
            return "Korisnik još nema spremljene osobne preferencije."

        return "Korisničke preferencije i kontekst:\n" + "\n".join(lines)


class UserContextManager:
    """Simple manager for loading/saving user profiles.
    
    For now uses JSON files in a local folder. Easy to swap for SQLite or real DB later.
    """

    def __init__(self, storage_path: str = "data/user_profiles"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, user_id: str) -> Path:
        return self.storage_path / f"{user_id}.json"

    def load_profile(self, user_id: str) -> UserProfile:
        path = self._get_file_path(user_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return UserProfile(**data)
        else:
            return UserProfile(user_id=user_id)

    def save_profile(self, profile: UserProfile):
        path = self._get_file_path(profile.user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.__dict__, f, ensure_ascii=False, indent=2)

    def update_interests(self, user_id: str, interests: List[str]):
        profile = self.load_profile(user_id)
        profile.interests = list(set(profile.interests + interests))
        self.save_profile(profile)
        return profile

    def add_visited_place(self, user_id: str, place: str):
        profile = self.load_profile(user_id)
        if place not in profile.visited_places:
            profile.visited_places.append(place)
        self.save_profile(profile)
        return profile


# Global instance for easy import
user_context_manager = UserContextManager()


def get_user_context_for_prompt(user_id: str) -> str:
    """Convenience function to get context string for system prompt."""
    profile = user_context_manager.load_profile(user_id)
    return profile.to_prompt_context()


# ============================================================
# CHAT HISTORY MANAGER (for /chat endpoint persistence)
# ============================================================

@dataclass
class ChatMessage:
    role: str          # "user" or "assistant"
    content: str

class ChatHistoryManager:
    """
    Enhanced persistent chat history per user.
    Supports full tool-calling memory:
    - user messages
    - assistant messages (with tool_calls)
    - tool results
    """

    def __init__(self, storage_path: str = "data/chat_history"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_messages = 30  # Limit total messages to control context size

    def _get_file_path(self, user_id: str) -> Path:
        return self.storage_path / f"{user_id}.json"

    def load_history(self, user_id: str) -> List[Dict]:
        """Returns the full list of messages in a serializable format.

        Defensive: if the per-user JSON file is corrupted (common after previous
        bad tool_calls serializations), we log the problem, preserve the bad file
        for diagnostics (rename to .bad.{ts}.json), and return [] so the chat
        request doesn't explode with 500.
        """
        path = self._get_file_path(user_id)
        if not path.exists():
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("messages", []) if isinstance(data, dict) else []
        except Exception as e:
            logger = logging.getLogger("lega.api")
            try:
                bad_snippet = path.read_text(encoding="utf-8")[:300]
            except Exception:
                bad_snippet = "<could not read file>"
            logger.exception(
                f"[HISTORY] Corrupted history file for user={user_id} at {path}. "
                f"Error: {e}. First 300 chars of bad file:\n{bad_snippet}"
            )
            # Preserve the bad file so we can debug the exact corruption
            try:
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                bad_path = path.with_suffix(f".bad.{ts}.json")
                path.rename(bad_path)
                logger.info(f"[HISTORY] Bad history preserved as {bad_path}")
            except Exception as rename_err:
                logger.warning(f"[HISTORY] Could not rename bad file: {rename_err}")
            return []

    def save_history(self, user_id: str, messages: List[Dict]):
        """Saves messages, trimming to max_messages if necessary."""
        if len(messages) > self.max_messages:
            messages = messages[-self.max_messages:]

        path = self._get_file_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"messages": messages}, f, ensure_ascii=False, indent=2)

    def add_full_turn(
        self,
        user_id: str,
        user_message: str,
        ai_tool_call_message: Optional[Dict] = None,   # AI message that requested tools
        tool_messages: Optional[List[Dict]] = None,    # List of tool results
        final_ai_message: Optional[str] = None,        # Final natural language response
        performance: Optional[Dict] = None             # Dan 17: {time_to_first_token, total_duration}
    ):
        """
        Saves a complete turn, including tool usage if it happened.
        This enables the model to continue tool use in future turns.
        """
        history = self.load_history(user_id)

        # Always add the user message
        history.append({"role": "user", "content": user_message})

        if ai_tool_call_message:
            # === DIAGNOSTIC LOGGING for tool_calls JSON roundtrip (root cause of post-tool 500s) ===
            tc = ai_tool_call_message.get("tool_calls") if isinstance(ai_tool_call_message, dict) else None
            tc_info = f"present={bool(tc)} len={len(tc) if tc else 0}"
            if tc and isinstance(tc, (list, tuple)) and tc:
                t0 = tc[0]
                tc_info += f" t0_type={type(t0).__name__} t0_repr[:180]={str(t0)[:180]}"
            print(f"[DIAG][HISTORY][SAVE] add_full_turn tool_calls | {tc_info}", flush=True)
            history.append(ai_tool_call_message)

        if tool_messages:
            history.extend(tool_messages)

        if final_ai_message:
            assistant_msg = {"role": "assistant", "content": final_ai_message}
            if performance:
                assistant_msg["performance"] = performance
            history.append(assistant_msg)

        self.save_history(user_id, history)

    def delete_history(self, user_id: str) -> bool:
        """Deletes the entire chat history for a user. Returns True if file was deleted."""
        path = self._get_file_path(user_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def delete_last_message(self, user_id: str) -> bool:
        """
        Deletes the last message in the history.
        Tries to keep conversation turns clean (removes trailing user message if left alone).
        Returns True if something was deleted.
        """
        history = self.load_history(user_id)
        if not history:
            return False

        history.pop()  # remove last message

        # If after popping we left a user message without a following assistant/tool response,
        # remove the user message too to keep clean pairs.
        if history and history[-1]["role"] == "user":
            history.pop()

        self.save_history(user_id, history)
        return True


# Global instance
chat_history_manager = ChatHistoryManager()


# ============================================================
# SAFE HISTORY NORMALIZATION (added 2026-06 during autonomous fix session)
# This is the recommended mitigation for the post-tool-turn 500 root cause.
# ============================================================

from typing import Any

try:
    from langchain_core.messages import AIMessage, ToolMessage
    from langchain_core.messages.tool import ToolCall
except ImportError:
    AIMessage = ToolMessage = ToolCall = None  # type: ignore


def _safe_tool_calls(raw: Any) -> list[dict] | list:
    """
    Normalize whatever we got from JSON (or from LangChain on save) into
    a list of plain dicts with stable keys: id, name, args.
    This is the single most important function for fixing the 500s.
    """
    if not raw:
        return []

    result = []
    for tc in raw if isinstance(raw, (list, tuple)) else [raw]:
        if isinstance(tc, dict):
            result.append({
                "id": tc.get("id") or tc.get("tool_call_id") or "",
                "name": tc.get("name") or tc.get("function", {}).get("name", ""),
                "args": tc.get("args") or tc.get("function", {}).get("arguments", {}) or {},
            })
        elif hasattr(tc, "name"):  # LangChain ToolCall or similar
            result.append({
                "id": getattr(tc, "id", "") or getattr(tc, "tool_call_id", ""),
                "name": getattr(tc, "name", ""),
                "args": getattr(tc, "args", {}) or {},
            })
        else:
            # Last resort – keep it, the diag logs will catch the weird case
            result.append(tc)
    return result


def normalize_to_langchain_messages(raw_history: List[Dict[str, Any]]) -> List[Any]:
    """
    The single source of truth for turning stored JSON history into
    something safe to feed LangChain.

    Use this in BOTH /chat and /chat/stream paths instead of the inline fragile loops.
    """
    if AIMessage is None or ToolMessage is None:
        # LangChain not available in this environment – return something that at least doesn't crash
        return raw_history

    out: List[Any] = []
    for msg in raw_history:
        role = msg.get("role")
        if role == "user":
            out.append(("human", msg.get("content", "")))
        elif role == "assistant":
            if msg.get("tool_calls"):
                clean_calls = _safe_tool_calls(msg["tool_calls"])
                out.append(AIMessage(content=msg.get("content") or "", tool_calls=clean_calls))
            else:
                out.append(("assistant", msg.get("content", "")))
        elif role == "tool":
            out.append(
                ToolMessage(
                    content=msg.get("content", ""),
                    tool_call_id=msg.get("tool_call_id", ""),
                    name=msg.get("name", ""),
                )
            )
    return out


def get_safe_history_for_llm(user_id: str, max_history: int | None = None) -> List[Any]:
    """
    Convenience wrapper used by api.py.
    Load + trim + normalize in one call.
    """
    raw = chat_history_manager.load_history(user_id)
    if max_history and max_history > 0:
        raw = raw[-max_history:]
    return normalize_to_langchain_messages(raw)
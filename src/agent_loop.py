"""
Phase 3 multi-turn agent loop (hybrid server + client tools).
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Callable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agent_prompts_v36 import get_agent_system_prompt
from agent_registry import get_all_agent_tools, get_tool_execution, is_client_tool, is_server_tool
from agent_sessions import AgentSession, agent_session_store

logger = logging.getLogger("lega.agent")

MAX_AGENT_ITERATIONS = 5

AGENT_TOOL_INSTRUCTIONS = """
**Alati (function calling):**
- vrijeme → get_current_weather_osijek | događaji/kino → search_osijek_events | restorani (web) → search_restaurants_or_food
- mjesta iz appa → search_places, get_place_details | blizu mene → get_nearby_places
- preporuke → get_recommended_places | plan → get_user_active_plan
Uvijek pozovi relevantni alat prije nego izmišljaš činjenice. Rezultate alata MORAŠ koristiti u finalnom odgovoru.
"""


def sse_agent_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _normalize_tool_call(tc: Any) -> dict:
    if isinstance(tc, dict):
        return {
            "id": tc.get("id") or tc.get("tool_call_id") or "",
            "name": tc.get("name") or (tc.get("function") or {}).get("name", ""),
            "args": tc.get("args") or (tc.get("function") or {}).get("arguments", {}) or {},
        }
    return {
        "id": getattr(tc, "id", "") or getattr(tc, "tool_call_id", ""),
        "name": getattr(tc, "name", ""),
        "args": getattr(tc, "args", {}) or {},
    }


def _execute_server_tool(tool_name: str, tool_args: dict, server_tools: dict) -> str:
    fn = server_tools.get(tool_name)
    if fn is None:
        return f"Nepoznat server alat: {tool_name}"
    try:
        return str(fn.invoke(tool_args) if tool_args else fn.invoke({}))
    except Exception as e:
        logger.exception("Server tool %s failed", tool_name)
        return f"Greška pri izvršavanju {tool_name}: {e}"


def build_agent_system_prompt(language: str, client_context: dict | None) -> str:
    prompt = get_agent_system_prompt(language) + "\n\n" + AGENT_TOOL_INSTRUCTIONS
    if not client_context:
        return prompt
    lines = ["**Kontekst iz mobilne aplikacije (pouzdano):**"]
    for key, value in client_context.items():
        if value is None or value == "" or value == []:
            continue
        lines.append(f"- {key}: {value}")
    if len(lines) > 1:
        prompt += "\n\n" + "\n".join(lines)
    prefetch = (client_context or {}).get("tool_results_prefetch")
    if prefetch:
        prompt += (
            f"\n\n{prefetch}\n\n"
            "**KRITIČNO (v3.6):** Gornji TOOL_RESULTS su pouzdani podaci iz app kataloga. "
            "Svaka preporuka MORA imati konkretan razlog iz opisa (hrana, atmosfera, lokacija). "
            "ZABRANJENO: 'Vrijedi posjetiti', 'Lijepo mjesto' bez objašnjenja."
        )
    return prompt


class AgentLoopResult:
    def __init__(
        self,
        *,
        messages: list[BaseMessage],
        done: bool = False,
        session_id: str | None = None,
        pending_client: list[dict] | None = None,
        tools_used: list[str] | None = None,
        final_text: str = "",
    ):
        self.messages = messages
        self.done = done
        self.session_id = session_id
        self.pending_client = pending_client or []
        self.tools_used = tools_used or []
        self.final_text = final_text


def run_agent_iteration(
    *,
    llm_with_tools,
    messages: list[BaseMessage],
    server_tools: dict,
    iteration: int,
) -> AgentLoopResult:
    """Blocking single-pass iteration (legacy). Prefer iterate_agent_events for SSE UX."""
    result_messages = messages
    tools_used: list[str] = []
    pending_client: list[dict] = []
    done = False
    final_text = ""

    for event in iterate_agent_events(
        llm_with_tools=llm_with_tools,
        messages=messages,
        server_tools=server_tools,
        iteration=iteration,
    ):
        kind = event.get("type")
        if kind == "agent_status":
            continue
        if kind == "tool_call":
            tools_used.append(event.get("name", ""))
        elif kind == "tool_request_client":
            pending_client.append(
                {
                    "id": event.get("tool_call_id", ""),
                    "name": event.get("name", ""),
                    "args": event.get("args") or {},
                }
            )
        elif kind == "awaiting_client":
            result_messages = event["messages"]
            break
        elif kind == "done_messages":
            result_messages = event["messages"]
            done = True
            final_text = event.get("final_text", "")
            break

    if pending_client:
        return AgentLoopResult(
            messages=result_messages,
            done=False,
            pending_client=pending_client,
            tools_used=tools_used,
        )
    return AgentLoopResult(
        messages=result_messages,
        done=done,
        tools_used=tools_used,
        final_text=final_text,
    )


def iterate_agent_events(
    *,
    llm_with_tools,
    messages: list[BaseMessage],
    server_tools: dict,
    iteration: int,
):
    """
    Yield progressive agent events so the client can show tool status BEFORE work runs.
    Event dicts: agent_status, tool_call, tool_request_client, awaiting_client, done_messages.
    """
    if iteration >= MAX_AGENT_ITERATIONS:
        yield {"type": "done_messages", "messages": messages, "final_text": ""}
        return

    yield {"type": "agent_status", "phase": "thinking", "message": "Lega analizira upit…"}

    ai_response = llm_with_tools.invoke(messages)

    if not getattr(ai_response, "tool_calls", None):
        # Always let plain_llm stream the final answer (avoids weak draft + generic lists).
        yield {"type": "done_messages", "messages": list(messages), "final_text": ""}
        return

    normalized = [_normalize_tool_call(tc) for tc in ai_response.tool_calls]
    client_pending = [tc for tc in normalized if is_client_tool(tc["name"])]
    server_calls = [tc for tc in normalized if is_server_tool(tc["name"])]
    unknown = [tc for tc in normalized if get_tool_execution(tc["name"]) is None]

    out_messages = messages + [ai_response]

    for tc in server_calls:
        yield {
            "type": "tool_call",
            "name": tc["name"],
            "execution": "server",
            "args": tc.get("args") or {},
        }
        result = _execute_server_tool(tc["name"], tc["args"], server_tools)
        out_messages.append(
            ToolMessage(content=result, tool_call_id=tc["id"], name=tc["name"])
        )

    for tc in unknown:
        out_messages.append(
            ToolMessage(
                content=f"Alat {tc['name']} nije dostupan.",
                tool_call_id=tc["id"],
                name=tc["name"],
            )
        )

    if client_pending:
        for tc in client_pending:
            yield {
                "type": "tool_request_client",
                "tool_call_id": tc["id"],
                "name": tc["name"],
                "args": tc.get("args") or {},
            }
        yield {
            "type": "awaiting_client",
            "messages": out_messages,
            "pending_client": client_pending,
        }
        return

    yield from iterate_agent_events(
        llm_with_tools=llm_with_tools,
        messages=out_messages,
        server_tools=server_tools,
        iteration=iteration + 1,
    )


def format_tool_results_block(messages: list[BaseMessage]) -> str | None:
    """Structured TOOL_RESULTS text for the final LLM hop (v3.6)."""
    lines: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            name = getattr(m, "name", "") or "tool"
            content = (getattr(m, "content", "") or "").strip()
            if len(content) > 1200:
                content = content[:1197] + "..."
            lines.append(f"- alat: {name}\n  rezultat: {content}")
    if not lines:
        return None
    return (
        "TOOL_RESULTS (pouzdani podaci — OBAVEZNO koristi u odgovoru, zadrži osječki/topao ton):\n"
        + "\n".join(lines)
    )


def _extract_prefetch_from_messages(messages: list[BaseMessage]) -> str | None:
    for m in messages:
        if isinstance(m, SystemMessage):
            content = (getattr(m, "content", "") or "")
            marker = "TOOL_RESULTS ("
            idx = content.find(marker)
            if idx >= 0:
                return content[idx:].split("\n\n**KRITIČNO")[0].strip()
    return None


def prepare_final_generation_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Inject structured TOOL_RESULTS reminder before streaming the final answer."""
    block = format_tool_results_block(messages)
    if not block:
        block = _extract_prefetch_from_messages(messages)
    if not block:
        return messages
    reminder = (
        f"{block}\n\n"
        "Uputa: Odgovori koristeći gornje TOOL_RESULTS. Svaka preporuka = konkretan razlog. "
        "Bez 'Vrijedi posjetiti'. Završi pitanjem."
    )
    return list(messages) + [HumanMessage(content=reminder)]


def extract_tool_history_payload(messages: list[BaseMessage]) -> tuple[dict | None, list[dict]]:
    """Serialize latest tool turn for chat history (multi-turn memory)."""
    ai_tool: dict | None = None
    tool_rows: list[dict] = []
    for m in messages:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            tc_raw = m.tool_calls
            tc_list = []
            for tc in tc_raw or []:
                if isinstance(tc, dict):
                    tc_list.append(tc)
                else:
                    tc_list.append({
                        "id": getattr(tc, "id", ""),
                        "name": getattr(tc, "name", ""),
                        "args": getattr(tc, "args", {}) or {},
                    })
            ai_tool = {"role": "assistant", "content": m.content or "", "tool_calls": tc_list}
        if isinstance(m, ToolMessage):
            tool_rows.append({
                "role": "tool",
                "content": m.content,
                "tool_call_id": getattr(m, "tool_call_id", ""),
                "name": getattr(m, "name", ""),
            })
    return ai_tool, tool_rows


def apply_client_tool_results(
    messages: list[BaseMessage],
    tool_results: list[dict],
) -> list[BaseMessage]:
    out = list(messages)
    for tr in tool_results:
        out.append(
            ToolMessage(
                content=str(tr.get("content", "")),
                tool_call_id=tr.get("tool_call_id", ""),
                name=tr.get("name", ""),
            )
        )
    return out


async def stream_final_answer(plain_llm, messages: list[BaseMessage]) -> AsyncGenerator[str, None]:
    accumulated = ""
    final_input = prepare_final_generation_messages(messages)
    async for chunk in plain_llm.astream(final_input):
        if chunk.content:
            accumulated += chunk.content
            yield sse_agent_event({"type": "content", "content": chunk.content})
    yield sse_agent_event({"type": "done", "full_content": accumulated})
    yield "data: [DONE]\n\n"
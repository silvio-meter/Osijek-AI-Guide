"""
Phase 3 multi-turn agent loop (hybrid server + client tools).
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Callable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from agent_registry import get_all_agent_tools, get_tool_execution, is_client_tool, is_server_tool
from agent_sessions import AgentSession, agent_session_store

logger = logging.getLogger("lega.agent")

MAX_AGENT_ITERATIONS = 5

AGENT_TOOL_INSTRUCTIONS = """
**Faza 3 — alati (function calling):**
- Za **vrijeme** → get_current_weather_osijek (server)
- Za **događaje, kino, raspored** → search_osijek_events (server)
- Za **restorane / hranu (web)** → search_restaurants_or_food (server)
- Za **mjesta iz app kataloga** → search_places, get_place_details (client — app će izvršiti)
- Za **blizu mene** → get_nearby_places (client)
- Za **personalizirane preporuke** → get_recommended_places (client)
- Za **aktivni plan** → get_user_active_plan (client)
Koristi alate prije nego izmišljaš činjenice. Možeš pozvati više alata u nizu.
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


def build_agent_system_prompt(base_system: str, client_context: dict | None) -> str:
    prompt = base_system + "\n\n" + AGENT_TOOL_INSTRUCTIONS
    if not client_context:
        return prompt
    lines = ["**Kontekst iz mobilne aplikacije (pouzdano):**"]
    for key, value in client_context.items():
        if value is None or value == "" or value == []:
            continue
        lines.append(f"- {key}: {value}")
    if len(lines) > 1:
        prompt += "\n\n" + "\n".join(lines)
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
        content = getattr(ai_response, "content", "") or ""
        out = messages + [ai_response]
        yield {"type": "done_messages", "messages": out, "final_text": content}
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
    async for chunk in plain_llm.astream(messages):
        if chunk.content:
            accumulated += chunk.content
            yield sse_agent_event({"type": "content", "content": chunk.content})
    yield sse_agent_event({"type": "done", "full_content": accumulated})
    yield "data: [DONE]\n\n"
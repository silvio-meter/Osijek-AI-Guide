"""
Minimal FastAPI backend for Osijek AI Guide (Lega) - Mobile App Support

This provides the foundation for the mobile application (option 2 + C).

Endpoints:

Authentication:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout

Chat (requires JWT):
- POST /chat
- POST /chat/stream
- POST /chat/reset
- GET  /chat/history/{user_id}
- GET  /chat/history/{user_id}/summary   (LLM-generated)
- POST /chat/history/{user_id}/reset
- POST /chat/feedback
- GET  /chat/feedback
- GET  /chat/metrics

Public:
- GET  /events
- GET  /restaurants
- GET  /points_of_interest

User (requires JWT):
- GET  /user/me
- POST /user/me/preferences

Admin / Protected:
- POST /admin/events
- PUT  /admin/events/{id}
- GET  /admin/events
- DELETE /admin/events/{id}

Run with: PYTHONPATH=src uvicorn src.api:app --reload --port 8000
"""

import logging

# Basic logging configuration for Dan 5
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from fastapi import FastAPI, HTTPException, Query, Depends, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
import json
import os

# LangChain + LLM imports for full chat
from langchain_xai import ChatXAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage, AIMessage

# Import existing Lega logic
from tools import (
    get_all_tools,
    search_restaurants_or_food,
    search_osijek_events,
    get_hybrid_upcoming_events,
)
from prompts import get_system_prompt
from user_context import (
    user_context_manager,
    get_user_context_for_prompt,
    chat_history_manager,
)
from tool_usage import tool_usage_tracker
from feedback import feedback_manager

# Authentication
from routers.auth import router as auth_router
from dependencies.auth import get_current_active_user
from src.models.user import User

# Points of Interest (Week 3)
from routers.points_of_interest import router as poi_router

# Events (Week 4 - hybrid model)
from routers.events import router as events_router

# Rate Limiting (Week 2)
from core.rate_limiter import conditional_limit, rate_limit_exceeded_handler, CHAT_RATE_LIMIT, IS_TESTING, limiter
from slowapi.errors import RateLimitExceeded

# Standardized Error Handling (Week 2 - Dan 3)
from schemas.error import ErrorResponse
from core.exceptions import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    RateLimitException,
)

# Security Middleware (Week 2 - Dan 4)
from core.security_middleware import SecurityHeadersMiddleware, PayloadSizeLimitMiddleware

# Logging + Correlation ID (Week 2 - Dan 5)
from core.logging_middleware import LoggingMiddleware

# For full chat we would need the LLM + tool calling loop.
# For MVP we expose the specialized tools directly + a simple chat stub.

app = FastAPI(
    title="Osijek AI Guide API (Lega)",
    version="0.6.0",
    description="""
## Osijek AI Guide - Lega API

Profesionalni backend za mobilnu aplikaciju "Lega" — AI vodič za grad Osijek.

### Glavne značajke
- **Hibridni podaci**: Kurirani + scrapirani podaci za restorane i događaje (najviša kvaliteta)
- **Pametan chat**: Puni kontekst razgovora, tool calling, personalizacija preko korisničkih preferencija
- **Javni podaci za mapu**: Points of Interest + Events s filtrima i proximity pretragom
- **Sigurnost**: JWT autentifikacija s refresh rotacijom + blacklistom, rate limiting, security headers

### Za mobilne developere
Većina javnih endpointa ne zahtijeva autentifikaciju (`/events`, `/restaurants`, `/points_of_interest`).
Chat i korisnički podaci zahtijevaju JWT token (vidi sekciju Authentication).

Svi odgovori koriste strukturirani JSON pogodak za mobilne aplikacije (Flutter / React Native).

### Baza
- **Jezik**: Primarno hrvatski (essekerizmi), podržan EN i DE
- **LLM**: Grok-3-mini (xAI)
""",
    contact={
        "name": "Lega Team",
        "url": "https://github.com/silviometer/Osijek-AI-Guide",
    },
    license_info={
        "name": "Personal / Educational Use",
    },
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Registracija, login, refresh token i logout. JWT + refresh rotation + blacklist.",
        },
        {
            "name": "Chat",
            "description": "Glavni chat s Legom. Podržava tool calling, memoriju, personalizaciju, summary i feedback.",
        },
        {
            "name": "Public Data",
            "description": "Javni podaci za mobilnu mapu i listove: Events (hibridni), Restaurants, Points of Interest.",
        },
        {
            "name": "User",
            "description": "Korisnički profil i preferencije (zahtijeva autentifikaciju).",
        },
        {
            "name": "Admin - Curated Events (protected)",
            "description": "Upravljanje kuriranim događajima. Samo za ovlaštene korisnike (admin).",
        },
        {
            "name": "Admin & Metrics (protected)",
            "description": "Interni admin endpointi za statistike, tool usage i feedback.",
        },
    ],
)

# ======================
# CORS - Hardened for mobile app (Week 2 - Dan 6)
# ======================
# For production, replace with specific allowed origins (e.g. your app domains or specific IPs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict this in production!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# ======================
# Rate Limiting (Week 2 - Dan 1)
# ======================
app.state.limiter = limiter

# Only register custom rate limit handler when we're not in test mode
if not IS_TESTING:
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ======================
# Standardized Error Handling (Week 2 - Dan 3)
# ======================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handles all custom AppException subclasses."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.error_code,
            message=exc.message,
            details=exc.details,
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Converts standard FastAPI HTTPException into our ErrorResponse format."""
    # Try to use a sensible error code
    error_code = "http_error"
    if exc.status_code == 401:
        error_code = "unauthorized"
    elif exc.status_code == 403:
        error_code = "forbidden"
    elif exc.status_code == 404:
        error_code = "not_found"
    elif exc.status_code == 422:
        error_code = "validation_error"

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=error_code,
            message=exc.detail if isinstance(exc.detail, str) else "An error occurred",
            details=exc.detail if not isinstance(exc.detail, str) else None,
        ).model_dump(),
    )


# ======================
# Security Middleware (Week 2 - Dan 4)
# ======================
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PayloadSizeLimitMiddleware, max_size=2_000_000)  # 2 MB max body

# ======================
# Logging + Correlation ID (Week 2 - Dan 5)
# ======================
app.add_middleware(LoggingMiddleware)


# ======================
# Routers
# ======================
app.include_router(auth_router)
app.include_router(poi_router)
# Management of curated events (separate from public /events discovery)
app.include_router(events_router, prefix="/admin/events")

# ======================
# LLM Setup (for full chat)
# ======================
llm_with_tools = ChatXAI(
    model="grok-3-mini",
    temperature=0.7,
    max_tokens=900,
    xai_api_key=os.getenv("XAI_API_KEY")
).bind_tools(get_all_tools())

plain_llm = ChatXAI(
    model="grok-3-mini",
    temperature=0.7,
    max_tokens=800,
    xai_api_key=os.getenv("XAI_API_KEY")
)

# ======================
# Pydantic Models
# ======================

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User message to Lega. Maximum 4000 characters."
    )
    user_id: Optional[str] = Field(
        None,
        description="Deprecated. Authenticated user ID is used automatically."
    )
    language: str = Field("hr", description="hr / en / de")
    max_history: Optional[int] = Field(
        None,
        ge=1,
        le=50,
        description="Optional limit on how many previous messages to include"
    )

class ChatResponse(BaseModel):
    response: str
    tools_used: List[str] = []

class PreferenceUpdate(BaseModel):
    interests: Optional[List[str]] = None
    preferred_areas: Optional[List[str]] = None
    dietary: Optional[List[str]] = None

# ======================
# Endpoints
# ======================

@app.get("/")
def root():
    return {"message": "Osijek AI Guide API is running. Ready for mobile app."}


@app.get("/health", tags=["Public Data"])
def health_check():
    """Health check endpoint for Docker / Railway / monitoring."""
    try:
        # Quick DB connectivity check
        from src.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"

    return {
        "status": "healthy",
        "version": "0.6.0",
        "service": "lega-api",
        "db": db_status
    }


@app.post(
    "/chat",
    tags=["Chat"],
    summary="Send a message to Lega (full tool-calling chat)",
    description="""Glavni chat endpoint.

Podržava:
- Potpunu memoriju razgovora (uključujući tool calls)
- Personalizaciju na temelju korisničkih preferencija
- Automatsko korištenje toolova (restorani, događaji, vrijeme, itd.)
- Opcionalno streaming (`?stream=true`)

Zahtijeva validan JWT token.
""",
)
@conditional_limit(CHAT_RATE_LIMIT)
async def chat_with_lega(
    request: Request,
    response: Response,
    chat_request: ChatRequest,
    stream: bool = Query(False, description="If true, returns Server-Sent Events stream of the final answer"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Full chat endpoint with **complete tool-calling memory**.
    Requires valid JWT authentication.
    Uses the authenticated user's ID for chat history and personalization.
    """
    # Prefer authenticated user ID, fall back to request body only for legacy/testing
    user_id = str(current_user.id)
    if chat_request.user_id and chat_request.user_id != "default_user":
        user_id = chat_request.user_id  # allow override in special cases

    language = chat_request.language

    # Load full previous message history (now supports tool calls)
    raw_history = chat_history_manager.load_history(user_id)

    # Apply client-requested history limit (for token / cost control)
    if request.max_history and request.max_history > 0:
        raw_history = raw_history[-request.max_history:]

    # Rebuild LangChain messages (including tool calls and tool results)
    chat_history_messages = []
    for msg in raw_history:
        if msg["role"] == "user":
            chat_history_messages.append(("human", msg["content"]))
        elif msg["role"] == "assistant":
            if msg.get("tool_calls"):
                chat_history_messages.append(
                    AIMessage(content=msg.get("content") or "", tool_calls=msg["tool_calls"])
                )
            else:
                chat_history_messages.append(("assistant", msg["content"]))
        elif msg["role"] == "tool":
            chat_history_messages.append(
                ToolMessage(
                    content=msg["content"],
                    tool_call_id=msg.get("tool_call_id", ""),
                    name=msg.get("name", "")
                )
            )

    # User context + system prompt
    user_context_str = get_user_context_for_prompt(user_id)
    system_prompt = get_system_prompt(language)

    if user_context_str and "Korisnik još nema spremljene osobne preferencije" not in user_context_str:
        system_prompt += (
            f"\n\n**VAŽNO - Korisničke preferencije:**\n"
            f"{user_context_str}\n\n"
            f"Uputa: Prilikom davanja preporuka (restorani, događaji, lokacije...) "
            f"uvijek uzimaj u obzir gore navedene preferencije korisnika. "
            f"Ako je relevantno, možeš eksplicitno spomenuti zašto nešto preporučuješ na temelju njegovih preferencija."
        )

    prompt_messages = [
        ("system", system_prompt),
        *chat_history_messages,
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ]
    prompt = ChatPromptTemplate.from_messages(prompt_messages)

    # First LLM call
    chain = prompt | llm_with_tools
    ai_response = chain.invoke({
        "input": chat_request.message,
        "chat_history": []
    })

    tools_used = []
    tool_messages_for_storage = []

    if hasattr(ai_response, "tool_calls") and ai_response.tool_calls:
        tools = {t.name: t for t in get_all_tools()}
        executed_tool_messages = []

        for tool_call in ai_response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            tool_id = tool_call["id"]
            tools_used.append(tool_name)

            # Record tool usage for metrics (Dan 4)
            try:
                tool_usage_tracker.record_tool_use(user_id, tool_name)
            except Exception as e:
                print(f"[metrics] Failed to record tool usage: {e}")

            if tool_name in tools:
                try:
                    tool_func = tools[tool_name]
                    tool_result = tool_func.invoke(tool_args) if tool_args else tool_func.invoke({})
                except Exception as e:
                    tool_result = f"Greška: {str(e)}"
            else:
                tool_result = f"Tool {tool_name} nije dostupan."

            executed_tool_messages.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_id, name=tool_name)
            )

            tool_messages_for_storage.append({
                "role": "tool",
                "content": str(tool_result),
                "tool_call_id": tool_id,
                "name": tool_name
            })

        ai_tool_call_msg = {
            "role": "assistant",
            "content": ai_response.content or "",
            "tool_calls": ai_response.tool_calls
        }

        # Prepare final messages for the answer (whether we stream or not)
        final_messages = prompt.invoke({
            "input": request.message,
            "chat_history": []
        }).to_messages()

        final_messages.append(ai_response)
        final_messages.extend(executed_tool_messages)

        if stream:
            # Real streaming using astream
            async def stream_real():
                async for chunk in plain_llm.astream(final_messages):
                    if chunk.content:
                        yield f"data: {json.dumps({'content': chunk.content})}\n\n"
                yield "data: [DONE]\n\n"

            # We still need to save the history. We have to generate the full answer once for saving.
            # (Trade-off: one extra generation for history. Acceptable for now.)
            final_response_obj = plain_llm.invoke(final_messages)
            final_answer = final_response_obj.content

            chat_history_manager.add_full_turn(
                user_id=user_id,
                user_message=chat_request.message,
                ai_tool_call_message=ai_tool_call_msg,
                tool_messages=tool_messages_for_storage,
                final_ai_message=final_answer
            )

            return StreamingResponse(stream_real(), media_type="text/event-stream")
        else:
            final_response_obj = plain_llm.invoke(final_messages)
            final_answer = final_response_obj.content

            chat_history_manager.add_full_turn(
                user_id=user_id,
                user_message=chat_request.message,
                ai_tool_call_message=ai_tool_call_msg,
                tool_messages=tool_messages_for_storage,
                final_ai_message=final_answer
            )

            return ChatResponse(response=final_answer, tools_used=tools_used)

    else:
        # No tools used
        final_messages = prompt.invoke({
            "input": request.message,
            "chat_history": []
        }).to_messages()

        if stream:
            async def stream_direct():
                async for chunk in plain_llm.astream(final_messages):
                    if chunk.content:
                        yield f"data: {json.dumps({'content': chunk.content})}\n\n"
                yield "data: [DONE]\n\n"

            # Generate once for history
            final_response_obj = plain_llm.invoke(final_messages)
            final_answer = final_response_obj.content

            chat_history_manager.add_full_turn(
                user_id=user_id,
                user_message=chat_request.message,
                final_ai_message=final_answer
            )

            return StreamingResponse(stream_direct(), media_type="text/event-stream")
        else:
            final_response_obj = plain_llm.invoke(final_messages)
            final_answer = final_response_obj.content

            chat_history_manager.add_full_turn(
                user_id=user_id,
                user_message=chat_request.message,
                final_ai_message=final_answer
            )

            return ChatResponse(response=final_answer, tools_used=tools_used)


# =============================================
# Streaming Chat Endpoint (SSE) - Recommended for Mobile
# =============================================

@app.post(
    "/chat/stream",
    tags=["Chat"],
    summary="Streaming chat with Lega (SSE)",
    description="""Preporučeni endpoint za mobilne aplikacije.

Vraća Server-Sent Events stream token-po-token nakon što se toolovi izvrše na serveru.
Idealno za glatko korisničko iskustvo u Flutteru.
""",
)
@conditional_limit(CHAT_RATE_LIMIT)
async def chat_stream(
    request: Request,
    response: Response,
    message: str,
    user_id: str = "default_user",
    language: str = "hr",
    max_history: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Streaming chat using Server-Sent Events.
    Tools are resolved on the server first.
    Then only the final answer is streamed token-by-token.
    Perfect for smooth mobile chat UX.
    """
    # Use authenticated user when possible
    effective_user_id = str(current_user.id)
    if user_id and user_id != "default_user":
        effective_user_id = user_id

    # Load history (respecting max_history)
    raw_history = chat_history_manager.load_history(effective_user_id)
    if max_history and max_history > 0:
        raw_history = raw_history[-max_history:]

    # Rebuild messages
    chat_history_messages = []
    for msg in raw_history:
        if msg["role"] == "user":
            chat_history_messages.append(("human", msg["content"]))
        elif msg["role"] == "assistant":
            if msg.get("tool_calls"):
                chat_history_messages.append(
                    AIMessage(content=msg.get("content") or "", tool_calls=msg["tool_calls"])
                )
            else:
                chat_history_messages.append(("assistant", msg["content"]))
        elif msg["role"] == "tool":
            chat_history_messages.append(
                ToolMessage(content=msg["content"], tool_call_id=msg.get("tool_call_id", ""), name=msg.get("name", ""))
            )

    # Context
    user_context_str = get_user_context_for_prompt(effective_user_id)
    system_prompt = get_system_prompt(language)
    if user_context_str and "Korisnik još nema spremljene osobne preferencije" not in user_context_str:
        system_prompt += (
            f"\n\n**VAŽNO - Korisničke preferencije:**\n{user_context_str}\n\n"
            f"Uputa: Prilikom davanja preporuka uvijek uzimaj u obzir ove preferencije."
        )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        *chat_history_messages,
        ("human", "{input}")
    ])

    # Resolve tools first (non-streaming)
    chain = prompt | llm_with_tools
    ai_response = chain.invoke({"input": message, "chat_history": []})

    if hasattr(ai_response, "tool_calls") and ai_response.tool_calls:
        # Execute tools
        tools = {t.name: t for t in get_all_tools()}
        tool_msgs = []
        for tc in ai_response.tool_calls:
            tool_name = tc["name"]
            try:
                # Record tool usage for metrics
                tool_usage_tracker.record_tool_use(effective_user_id, tool_name)
            except Exception as e:
                print(f"[metrics] Failed to record tool usage: {e}")

            try:
                res = tools[tool_name].invoke(tc.get("args", {})) if tc.get("args") else tools[tool_name].invoke({})
            except Exception as e:
                res = f"Greška: {e}"
            tool_msgs.append(ToolMessage(content=str(res), tool_call_id=tc["id"], name=tool_name))

        full_msgs = prompt.invoke({"input": message, "chat_history": []}).to_messages()
        full_msgs.append(ai_response)
        full_msgs.extend(tool_msgs)

        async def stream_after_tools():
            async for chunk in plain_llm.astream(full_msgs):
                if chunk.content:
                    yield f"data: {json.dumps({'content': chunk.content})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_after_tools(), media_type="text/event-stream")
    else:
        # No tools needed - stream directly
        async def stream_direct():
            async for chunk in plain_llm.astream(prompt.invoke({"input": message, "chat_history": []})):
                if chunk.content:
                    yield f"data: {json.dumps({'content': chunk.content})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_direct(), media_type="text/event-stream")

@app.get(
    "/restaurants",
    tags=["Public Data"],
    summary="Get restaurants and food recommendations in Osijek",
    description="""Vraća podatke o restoranima i preporukama za hranu u Osijeku.

Koristi hibridni model (kurirani podaci + scraper).
Preporučeno za mobilne karte i liste restorana.
""",
)
def get_restaurants(structured: bool = Query(True, description="Return structured data for mobile (recommended)")):
    """Returns restaurant data. Use structured=true for mobile map/cards."""
    result = search_restaurants_or_food.invoke({
        "query": "restorani",
        "structured": structured
    })
    if structured:
        return json.loads(result)
    return {"text": result}

@app.get(
    "/events",
    tags=["Public Data"],
    summary="Get upcoming events in Osijek (hybrid curated + scraped)",
    description="""Glavni endpoint za dohvat događaja u Osijeku.

**Preporučeno za mobilne aplikacije:** `structured=true` (default).

Koristi hibridnu strategiju:
1. Kurirani događaji (najviša kvaliteta, ručno održavani)
2. Scrapirani s lokalnih portala (osijek031, sib, osijeknews)
3. Samo po potrebi Tavily fallback

Podržava filtriranje po kategoriji/tagovima i vremenskom prozoru.
""",
    responses={
        200: {
            "description": "Lista događaja",
            "content": {
                "application/json": {
                    "example": {
                        "events": [
                            {
                                "title": "Paulinafest 2026",
                                "date_text": "15. lipnja 2026. od 18h",
                                "location": "Tvrđa",
                                "category": "Festival",
                                "source": "curated",
                                "has_reliable_date": True
                            }
                        ],
                        "count": 12,
                        "days_ahead": 14,
                        "source": "hybrid_curated_scraped"
                    }
                }
            }
        }
    }
)
def get_events(
    query: str = Query("događaji", description="Natural language query (used by chat/LLM path)"),
    structured: bool = Query(True, description="Return clean JSON list (recommended for mobile)"),
    category: Optional[str] = Query(None, description="Filter by category or tag (npr. festival, koncert, besplatno)"),
    days_ahead: int = Query(14, ge=1, le=60, description="How many days ahead to look"),
    limit: int = Query(30, ge=1, le=100),
):
    """
    Public events endpoint for the mobile app and direct use.

    **Best practice for mobile:**
    - Use `structured=true` + `category` + `days_ahead` for clean lists and maps.
    - The response is optimized for Flutter cards and map pins.
    """
    # Fast path for clean mobile lists (most common case)
    if structured:
        try:
            events = get_hybrid_upcoming_events(
                days_ahead=days_ahead,
                category=category,
                limit=limit
            )
            # Light post-filter if free-text search in title/desc was provided
            if query and query.lower() not in ("događaji", "events", "dogadjaji"):
                q = query.lower()
                events = [
                    e for e in events
                    if q in (e.get("title", "") or "").lower()
                    or q in (e.get("description", "") or "").lower()
                    or q in (e.get("short_description", "") or "").lower()
                ][:limit]

            return {
                "events": events,
                "count": len(events),
                "days_ahead": days_ahead,
                "category": category,
                "source": "hybrid_curated_scraped"
            }
        except Exception as e:
            # Graceful degradation: fall back to tool
            print(f"[public /events] direct hybrid failed, falling back to tool: {e}")

    # LLM / natural language path (or fallback)
    effective_query = query
    if category:
        effective_query = f"{query} {category}"

    result = search_osijek_events.invoke({
        "query": effective_query,
        "structured": structured
    })

    if structured:
        try:
            parsed = json.loads(result)
            return {
                "events": parsed if isinstance(parsed, list) else [],
                "count": len(parsed) if isinstance(parsed, list) else 0,
                "days_ahead": days_ahead,
                "category": category,
                "source": "tool_hybrid"
            }
        except Exception:
            return {"events": [], "count": 0, "error": "Failed to parse result"}

    return {"text": result, "source": "tool"}


# ======================
# Points of Interest (for Map in Mobile App)
# ======================

POINTS_OF_INTEREST = [
    {
        "name": "Tvrđa",
        "category": "Povijest",
        "description": "Barokna tvrđava i najljepši dio Osijeka. Mnogo kafića, restorana i kulturnih događaja.",
        "lat": 45.560,
        "lng": 18.695,
        "address": "Tvrđa, Osijek"
    },
    {
        "name": "Katedrala sv. Petra i Pavla",
        "category": "Povijest",
        "description": "Najveća i najljepša crkva u Osijeku s visokim tornjem.",
        "lat": 45.557,
        "lng": 18.695,
        "address": "Trg Jurja Strossmayera, Osijek"
    },
    {
        "name": "Europska avenija",
        "category": "Šetnja",
        "description": "Prekrasna avenija s secesijskim zgradama, idealna za šetnju.",
        "lat": 45.554,
        "lng": 18.690,
        "address": "Europska avenija, Osijek"
    },
    {
        "name": "Muzej Slavonije",
        "category": "Kultura",
        "description": "Glavni muzej Osijeka s bogatom zbirkom povijesti Slavonije.",
        "lat": 45.561,
        "lng": 18.696,
        "address": "Trg Jurja Strossmayera 6, Osijek"
    },
    {
        "name": "Zimska luka / Šetnica uz Dravu",
        "category": "Priroda",
        "description": "Lijepa šetnica uz rijeku Dravu, popularna za rekreaciju i romantične šetnje.",
        "lat": 45.555,
        "lng": 18.685,
        "address": "Gornjodravska obala, Osijek"
    },
    {
        "name": "Co-cathedral of St. Peter and St. Paul",
        "category": "Povijest",
        "description": "The iconic neo-Gothic cathedral, a symbol of Osijek.",
        "lat": 45.557,
        "lng": 18.695,
        "address": "Trg Jurja Strossmayera, Osijek"
    }
]

@app.get("/points_of_interest")
def get_points_of_interest():
    """Returns structured list of key locations in Osijek for the mobile map."""
    return POINTS_OF_INTEREST

@app.get("/user/me")
def get_my_profile(current_user: User = Depends(get_current_active_user)):
    """Returns the profile of the currently authenticated user."""
    profile = user_context_manager.load_profile(str(current_user.id))
    if not profile.display_name:
        profile.display_name = current_user.full_name or current_user.email.split("@")[0]
    return profile.__dict__


@app.get("/user/{user_id}")
def get_user_profile(user_id: str, current_user: User = Depends(get_current_active_user)):
    # For now only allow users to access their own profile (or make admin check later)
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own profile")
    profile = user_context_manager.load_profile(user_id)
    return profile.__dict__


# ======================
# Chat History Endpoint
# ======================

@app.get("/chat/history/{user_id}")
def get_chat_history(user_id: str, limit: Optional[int] = None):
    """Returns the full conversation history for a user (including tool calls if present).
    
    Optional `limit` parameter returns only the last N messages.
    """
    history = chat_history_manager.load_history(user_id)
    
    if limit and limit > 0:
        history = history[-limit:]
    
    return {
        "user_id": user_id,
        "message_count": len(history),
        "history": history
    }


@app.get("/chat/history/{user_id}/last")
def get_last_message(user_id: str):
    """Returns only the last message in the user's chat history (if any)."""
    history = chat_history_manager.load_history(user_id)
    if not history:
        return {"user_id": user_id, "last_message": None}
    
    last_msg = history[-1]
    return {
        "user_id": user_id,
        "last_message": last_msg
    }


@app.get("/chat/history/{user_id}/summary")
def get_chat_summary(
    user_id: str,
    format: str = Query("medium", description="Summary length: short, medium, detailed"),
    max_messages: int = Query(30, description="Max number of recent messages to analyze")
):
    """
    Returns an LLM-generated summary of the conversation with Lega.

    The summary is much more useful than simple message counting.
    It captures main topics, key questions, and recommendations.
    """
    history = chat_history_manager.load_history(user_id)

    if not history:
        return {
            "user_id": user_id,
            "message_count": 0,
            "summary": "No conversation history yet.",
            "format": format
        }

    # Take only the most recent messages to avoid token limits
    recent_history = history[-max_messages:] if len(history) > max_messages else history

    # Build a clean conversation transcript for the LLM
    transcript_lines = []
    for msg in recent_history:
        role = "User" if msg["role"] == "user" else "Lega"
        content = msg.get("content", "")[:800]  # truncate very long messages
        transcript_lines.append(f"{role}: {content}")

    transcript = "\n\n".join(transcript_lines)

    # Prompt for summarization
    summary_prompt = f"""You are helping summarize a conversation between a user and "Lega", an AI guide for the city of Osijek, Croatia.

Please create a clear, useful summary of the conversation below.

Summary guidelines:
- Write in Croatian.
- Focus on the main topics the user asked about.
- Mention key recommendations or information Lega provided.
- Note any personal preferences the user mentioned.
- Keep it objective and concise.

Conversation:
{transcript}

Now provide the summary:"""

    try:
        # Use plain_llm for summarization (cheaper and faster than tool-calling model)
        llm_response = plain_llm.invoke(summary_prompt)
        summary_text = llm_response.content.strip()
    except Exception as e:
        summary_text = f"Greška pri generiranju sažetka: {str(e)}"

    # Basic statistics
    user_messages = [m for m in history if m["role"] == "user"]
    assistant_messages = [m for m in history if m["role"] == "assistant"]

    last_user_msg = next((m["content"] for m in reversed(history) if m["role"] == "user"), None)
    last_assistant_msg = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), None)

    return {
        "user_id": user_id,
        "message_count": len(history),
        "user_messages": len(user_messages),
        "assistant_messages": len(assistant_messages),
        "analyzed_messages": len(recent_history),
        "last_user_message": last_user_msg[:150] + "..." if last_user_msg and len(last_user_msg) > 150 else last_user_msg,
        "last_assistant_message": last_assistant_msg[:150] + "..." if last_assistant_msg and len(last_assistant_msg) > 150 else last_assistant_msg,
        "summary": summary_text,
        "format": format
    }


@app.delete("/chat/history/{user_id}")
def delete_chat_history(user_id: str):
    """Deletes the entire chat history for the given user."""
    deleted = chat_history_manager.delete_history(user_id)
    if deleted:
        return {"message": f"Chat history for user '{user_id}' has been deleted."}
    else:
        return {"message": f"No chat history found for user '{user_id}'."}


@app.post("/chat/history/{user_id}/reset")
def reset_chat_history(
    user_id: str,
    keep_preferences: bool = Query(True, description="Whether to keep user preferences after reset")
):
    """
    Resets the user's chat history.
    This is the recommended way for a user to start a fresh conversation with Lega.
    
    By default, user preferences are preserved.
    """
    deleted = chat_history_manager.delete_history(user_id)
    
    if deleted:
        msg = f"Chat history for user '{user_id}' has been reset."
        if keep_preferences:
            msg += " Preferences have been preserved."
        else:
            # Future: could clear preferences here if needed
            msg += " Preferences were also cleared (not yet implemented)."
        return {"message": msg, "user_id": user_id, "keep_preferences": keep_preferences}
    else:
        return {
            "message": f"No chat history found for user '{user_id}'. Nothing to reset.",
            "user_id": user_id
        }


@app.post("/chat/reset")
def reset_my_chat(
    keep_preferences: bool = Query(True, description="Keep user preferences after reset"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Convenience endpoint for authenticated users to reset their own chat.
    Uses the user_id from the JWT token.
    """
    user_id = str(current_user.id)
    deleted = chat_history_manager.delete_history(user_id)
    
    if deleted:
        msg = "Your chat history has been reset."
        if keep_preferences:
            msg += " Your preferences have been preserved."
        return {"message": msg, "keep_preferences": keep_preferences}
    else:
        return {"message": "You had no chat history to reset."}


@app.delete("/chat/history/{user_id}/last")
def delete_last_chat_message(user_id: str):
    """Deletes only the last message (and cleans up if a user message is left without response)."""
    deleted = chat_history_manager.delete_last_message(user_id)
    if deleted:
        return {"message": f"Last message for user '{user_id}' has been deleted."}
    else:
        return {"message": f"No messages found for user '{user_id}'."}

# ======================
# Tool Usage Metrics (Week 5 - Dan 4)
# ======================

@app.get("/chat/metrics")
def get_my_tool_metrics(
    current_user: User = Depends(get_current_active_user),
    include_global: bool = Query(False, description="Include global top tools (for power users)")
):
    """Returns tool usage statistics for the authenticated user."""
    user_id = str(current_user.id)
    user_stats = tool_usage_tracker.get_user_stats(user_id)

    response = {
        "user_id": user_id,
        "your_tool_usage": user_stats.get("tools", {}),
        "total_tool_calls": user_stats.get("total_tool_calls", 0),
        "last_updated": user_stats.get("last_updated")
    }

    if include_global:
        global_stats = tool_usage_tracker.get_global_stats(top_n=10)
        response["global_top_tools"] = global_stats.get("top_tools", [])
        response["global_total_tool_calls"] = global_stats.get("total_tool_calls", 0)

    return response


@app.get("/admin/metrics/tool_usage")
def get_global_tool_metrics(current_user: User = Depends(get_current_active_user)):
    """Global tool usage stats (protected)."""
    # In a real app you would check if user is admin
    stats = tool_usage_tracker.get_global_stats(top_n=15)
    return stats


# ======================
# Feedback (Week 5 - Dan 5)
# ======================

@app.post("/chat/feedback")
def submit_feedback(
    message_index: int,
    rating: int,                    # 1 = thumbs up, -1 = thumbs down
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Submit feedback on a specific assistant message in your chat history.
    `message_index` refers to the position in your chat history (0-based).
    """
    user_id = str(current_user.id)

    if rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating must be 1 (up) or -1 (down)")

    try:
        feedback_manager.record_feedback(
            user_id=user_id,
            message_index=message_index,
            rating=rating,
            comment=comment
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Feedback recorded. Thank you!",
        "user_id": user_id,
        "message_index": message_index,
        "rating": rating
    }


@app.get("/chat/feedback")
def get_my_feedback(current_user: User = Depends(get_current_active_user)):
    """Returns all feedback you have given."""
    user_id = str(current_user.id)
    feedback = feedback_manager.get_user_feedback(user_id)
    summary = feedback_manager.get_feedback_summary(user_id)

    return {
        "user_id": user_id,
        "feedback": feedback,
        "summary": summary
    }


# ======================
# User Preferences
# ======================

@app.post("/user/me/preferences")
def update_my_preferences(prefs: PreferenceUpdate, current_user: User = Depends(get_current_active_user)):
    """Update preferences for the authenticated user."""
    user_id = str(current_user.id)
    profile = user_context_manager.load_profile(user_id)

    if prefs.interests is not None:
        profile.interests = list(set(profile.interests + prefs.interests))
    if prefs.preferred_areas is not None:
        profile.preferred_areas = list(set(profile.preferred_areas + prefs.preferred_areas))
    if prefs.dietary is not None:
        profile.dietary = list(set(profile.dietary + prefs.dietary))

    user_context_manager.save_profile(profile)
    return {"message": "Preferences updated", "profile": profile.__dict__}

# ======================
# Run instruction
# ======================
# uvicorn src.api:app --reload --port 8000
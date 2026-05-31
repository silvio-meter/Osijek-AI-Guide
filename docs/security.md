# Security & Hardening (Week 2)

This document summarizes the security improvements implemented during **Tjedan 2** of Phase 1.

## Goals of the Week

- Protect the API from abuse (rate limiting)
- Provide consistent, developer-friendly error responses
- Reduce attack surface (input validation + payload limits)
- Improve observability (logging + correlation IDs)
- Establish basic security best practices (headers, CORS)

---

## 1. Rate Limiting

**Library:** `slowapi`

**Key Features:**
- Smart key function: Prefers authenticated `user_id` when available, falls back to IP address.
- Different limits for sensitive vs. expensive endpoints.

**Current Limits (as of end of Week 2):**

| Endpoint Group     | Limit          | Reason                          |
|--------------------|----------------|---------------------------------|
| `/auth/register`   | 4 / minute     | Anti brute-force / spam         |
| `/auth/login`      | 8 / minute     | Anti brute-force                |
| `/auth/refresh`    | 15 / minute    | Still sensitive                 |
| `/chat`, `/chat/stream` | 25 / minute | LLM calls are expensive         |
| Default            | 120 / minute   | General protection              |

**Response on limit exceeded:** `429 Too Many Requests` with standardized `ErrorResponse` + `Retry-After` header.

---

## 2. Standardized Error Responses

All errors now return a consistent structure:

```json
{
  "error": "rate_limit_exceeded",
  "message": "Previše zahtjeva u kratkom vremenu...",
  "details": { "retry_after_seconds": 60 }
}
```

**Custom exceptions** exist in `src/core/exceptions.py`:
- `AppException` (base)
- `UnauthorizedException`
- `ForbiddenException`
- `ValidationException`
- `NotFoundException`
- `RateLimitException`

Global exception handlers in `src/api.py` convert both custom exceptions and standard `HTTPException` into the `ErrorResponse` format.

---

## 3. Input Validation & Payload Protection

- Chat messages limited to **4000 characters**
- Login/Register passwords have length limits
- Request body size limited to **2 MB** (returns `413 Payload Too Large`)
- Basic Pydantic validation improvements across schemas

---

## 4. Security Headers

The following headers are added to every response via middleware:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (restricts camera, microphone, geolocation, etc.)

---

## 5. Logging & Correlation ID

- Every request gets a `X-Request-ID` (generated if not provided by client).
- Requests are logged with: method, path, status, duration, IP, user (if authenticated), and request ID.
- Logs use different levels (INFO / WARNING / ERROR) based on response status.

This makes debugging and incident response much easier.

---

## 6. CORS Configuration

`CORSMiddleware` is configured with:

- Allowed methods: `GET, POST, PUT, DELETE, OPTIONS, PATCH`
- `max_age=600` (preflight caching)
- Currently set to `allow_origins=["*"]` for development.

**TODO for production:** Restrict `allow_origins` to trusted domains only.

---

## Error Codes Reference (for Mobile App)

| error code                | HTTP | Meaning                              |
|---------------------------|------|--------------------------------------|
| `unauthorized`            | 401  | Missing or invalid authentication    |
| `forbidden`               | 403  | Authenticated but no permission      |
| `not_found`               | 404  | Resource does not exist              |
| `validation_error`        | 422  | Bad input data                       |
| `rate_limit_exceeded`     | 429  | Too many requests                    |
| `payload_too_large`       | 413  | Request body exceeds size limit      |
| `http_error`              | *    | Generic / unexpected HTTP error      |

---

## Current State & Recommendations

**Good:**
- Rate limiting is user-aware and protects expensive operations
- Errors are consistent and useful for mobile clients
- Basic security headers and payload protection are in place
- Request tracing via `X-Request-ID` is working

**Needs attention before production:**
- Tighten CORS origins
- Consider moving rate limit storage to Redis (currently in-memory via slowapi)
- Add more granular logging (e.g. structured logs with structlog)
- Implement proper secret management for `JWT_SECRET_KEY`

---

## Next Steps (Tjedan 3+)

Security improvements will continue, but the foundation is now solid enough to move on to richer domain features (Points of Interest, better event strategy, etc.).

Week 2 significantly raised the professional level of the backend.

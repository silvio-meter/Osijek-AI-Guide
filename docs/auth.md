# Authentication (JWT) - Osijek AI Guide

This document describes the authentication system implemented during Week 1.

## Overview

- Custom JWT-based authentication (no external auth providers in Phase 1)
- Access tokens (short-lived, 30 minutes)
- Refresh tokens with rotation + database blacklist (7 days)
- Bcrypt password hashing
- SQLite for development (easy migration to PostgreSQL later)

## Endpoints

| Method | Endpoint                  | Auth Required | Description                          |
|--------|---------------------------|---------------|--------------------------------------|
| POST   | `/auth/register`          | No            | Register new user                    |
| POST   | `/auth/login`             | No            | Login and receive tokens             |
| POST   | `/auth/refresh`           | No            | Exchange refresh token for new pair  |
| POST   | `/auth/logout`            | No            | Revoke a refresh token               |
| GET    | `/user/me`                | Yes           | Get current user's profile           |
| POST   | `/user/me/preferences`    | Yes           | Update current user's preferences    |
| POST   | `/chat`                   | Yes           | Chat with Lega (personalized)        |
| POST   | `/chat/stream`            | Yes           | Streaming chat                       |

## Token Format

Both tokens are standard JWTs signed with `HS256`.

### Access Token Claims
- `sub`: user ID
- `type`: "access"
- `email`: user's email
- `exp`: expiration

### Refresh Token Claims
- `sub`: user ID
- `type`: "refresh"
- `jti`: unique token identifier (used for revocation)
- `exp`: expiration

## Refresh Token Rotation

Every time a refresh token is used successfully:
1. The old token is immediately revoked in the database.
2. A new refresh token + new access token is issued.

This significantly reduces the risk of token theft.

## Running Tests

```bash
PYTHONPATH=src python -m pytest tests/test_auth.py -v
```

All 18 auth-related tests should pass.

## Environment Variables

See [.env.example](../.env.example) for required variables.

**Critical**: In production, always set a strong `JWT_SECRET_KEY`.

## Current Limitations (to be improved in later weeks)

- No password reset / email verification yet
- Chat history endpoints (`/chat/history/...`) are not yet protected
- No admin roles yet

**Note:** Most rate limiting and general security improvements have been implemented in **Week 2**. See [docs/security.md](security.md) for details.

## Future Migration Path

The system is designed to be replaceable later with:
- Firebase Auth
- Auth0 / Clerk
- FastAPI Users + SQLAlchemy

The current custom implementation gives full control during the early phase.

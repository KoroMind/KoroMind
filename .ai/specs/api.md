# API Service Specification

## Overview

The REST API provides programmatic access to KoroMind for message processing,
session management, and user settings. It is intended for single-tenant use by
default and relies on API key authentication.

## Architecture

- FastAPI application in `src/koro/api/app.py`.
- Middleware in `src/koro/api/middleware.py` handles authentication and rate
  limiting.
- Route handlers in `src/koro/api/routes/*` delegate to `koro.core.brain`.

## Data Models

- User identity is derived from the authenticated API key and persisted in the
  database as a stable user ID string.
- Session and settings storage is handled by the core state manager; the API
  does not define its own database schema.

## API Contracts

### /api/v1/messages
- POST `/messages`: process text or voice input and return text response plus
  optional audio (base64-encoded).
- POST `/messages/text`: text-only convenience endpoint.

### /api/v1/sessions
- GET `/sessions`: list sessions for the authenticated user.
- POST `/sessions`: create a new session and set it current.
- GET `/sessions/current`: fetch current session or null.
- PUT `/sessions/current`: switch to an existing session.

### /api/v1/settings
- GET `/settings`: fetch user settings.
- PUT `/settings`: update user settings.
- POST `/settings/reset`: reset settings to defaults.

### /api/v1/health
- GET `/health`: health check (public).

## Configuration

- `KOROMIND_API_KEY`: API key required for authentication.
- `KOROMIND_ALLOW_NO_AUTH`: allow unauthenticated access (development only).
- `KOROMIND_CORS_ORIGINS`: comma-separated allowlist for CORS origins.
- `KOROMIND_HOST` / `KOROMIND_PORT`: server bind address/port.

## Security

- Authentication is enforced by `api_key_middleware`.
- User identity is derived from the API key (SHA-256) and stored in
  `request.state.user_id`.
- Rate limiting is enforced by `rate_limit_middleware` for all non-public
  endpoints.
- CORS uses an allowlist; wildcard origins are not permitted with credentials.

## Changelog

### 2026-01-28
- Enforced API key authentication with optional dev bypass.
- Derived user identity from API key to prevent header-based impersonation.
- Added CORS allowlist and API-wide rate limiting middleware.

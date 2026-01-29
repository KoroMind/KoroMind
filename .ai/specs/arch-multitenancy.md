---
id: ARCH-001
type: feature
status: open
severity: critical
location: multiple
issue: null
validated: 2026-01-28
---

# Multi-Tenancy Architecture

## Goal
- Transform KoroMind from single-user to multi-tenant
- Zero-knowledge encryption for user data privacy
- Scale to 1000+ users with worker pool architecture

## Architecture Decisions
- Pre-warmed worker pool (no cold start)
- User PIN derives encryption key (MVP)
- Session locked to one device at a time
- Force-close old session when new device connects
- Anthropic API key rotation across Max accounts

## System Overview

```mermaid
flowchart TB
    subgraph Clients
        TG1[Telegram App - Device A]
        TG2[Telegram App - Device B]
        CLI[CLI Client]
        API[REST API Client]
    end

    subgraph Gateway
        AUTH[Authentication]
        RL[Rate Limiter - Redis]
    end

    subgraph Core
        BRAIN[Brain Orchestrator]
        ROUTER[Session Router]

        subgraph Workers
            W1[Worker 1]
            W2[Worker 2]
            W3[Worker N]
        end
    end

    subgraph Anthropic
        KEY1[Max Account 1]
        KEY2[Max Account 2]
        KEY3[Max Account 3]
    end

    EL[ElevenLabs STT/TTS]

    subgraph Storage
        PG[(PostgreSQL)]

        subgraph UserData
            US1[User 1 - Encrypted]
            US2[User 2 - Encrypted]
            USN[User N - Encrypted]
        end

        subgraph Sandboxes
            SB1[/sandbox/user1/]
            SB2[/sandbox/user2/]
            SBN[/sandbox/userN/]
        end
    end

    TG1 --> AUTH
    TG2 --> AUTH
    CLI --> AUTH
    API --> AUTH
    AUTH --> RL
    RL --> BRAIN
    BRAIN --> ROUTER
    ROUTER --> W1
    ROUTER --> W2
    ROUTER --> W3
    W1 --> KEY1
    W2 --> KEY2
    W3 --> KEY3
    W1 --> EL
    W2 --> EL
    W3 --> EL
    BRAIN --> PG
    W1 --> SB1
    W2 --> SB2
    W3 --> SBN
    BRAIN --> UserData
```

## Session & Device Locking

Sessions are locked to one device at a time. When a new device connects, the old session is force-closed.

```mermaid
sequenceDiagram
    participant D1 as Device A
    participant D2 as Device B
    participant API as KoroMind API
    participant DB as Database
    participant W as Worker

    Note over D1,W: Device A starts session
    D1->>API: Connect with PIN
    API->>DB: Check active sessions
    DB-->>API: No active session
    API->>DB: Create session locked to Device A
    API->>W: Assign worker
    API-->>D1: Session started

    Note over D1,W: Device A sends message
    D1->>API: Message + session_id
    API->>DB: Validate session ownership
    API->>W: Process message
    W-->>D1: Response

    Note over D2,W: Device B tries to connect
    D2->>API: Connect same user different device
    API->>DB: Check active sessions
    DB-->>API: Active session on Device A
    API->>D1: Force disconnect notification
    API->>DB: Transfer session to Device B
    API->>W: Reassign worker
    API-->>D2: Session started and took over
```

## Zero-Knowledge Encryption

Server never sees plaintext user data. PIN-derived key encrypts on client, server is relay only.

```mermaid
flowchart LR
    subgraph Client
        PIN[User PIN]
        KDF[Key Derivation]
        EK[Encryption Key]
        PIN --> KDF --> EK
    end

    subgraph Encryption
        DATA[User Data]
        ENC[AES-256-GCM Encrypt]
        CIPHER[Ciphertext]
        DATA --> ENC
        EK --> ENC
        ENC --> CIPHER
    end

    subgraph Server
        STORE[(Encrypted Storage)]
        RELAY[Relay Only]
        CIPHER --> STORE
        STORE --> RELAY
    end

    subgraph Decryption
        CIPHER2[Ciphertext]
        DEC[AES-256-GCM Decrypt]
        PLAIN[Plaintext Data]
        RELAY --> CIPHER2
        CIPHER2 --> DEC
        EK -.-> DEC
        DEC --> PLAIN
    end
```

## Data Model

```mermaid
erDiagram
    TENANT {
        uuid id PK
        string name
        datetime created_at
        boolean active
    }

    USER {
        uuid id PK
        uuid tenant_id FK
        string telegram_id UK
        string encrypted_settings
        datetime created_at
    }

    DEVICE {
        uuid id PK
        uuid user_id FK
        string device_fingerprint
        datetime last_seen
        boolean is_active
    }

    SESSION {
        uuid id PK
        uuid user_id FK
        uuid device_id FK
        string claude_session_id
        datetime started_at
        datetime ended_at
        boolean is_active
    }

    TELEMETRY {
        uuid id PK
        uuid session_id FK
        int input_tokens
        int output_tokens
        int tool_calls
        int tts_characters
        decimal cost_estimate
        datetime recorded_at
    }

    MEMORY {
        uuid id PK
        uuid user_id FK
        blob encrypted_content
        datetime created_at
    }

    TENANT ||--o{ USER : has
    USER ||--o{ DEVICE : owns
    USER ||--o{ SESSION : has
    USER ||--o{ MEMORY : stores
    DEVICE ||--o{ SESSION : runs
    SESSION ||--o{ TELEMETRY : tracks
```

## Worker Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Idle: Worker started

    Idle --> Assigned: User request
    Assigned --> Processing: Context injected
    Processing --> Responding: Claude response
    Responding --> Idle: Response sent
    Processing --> Error: Exception
    Error --> Idle: Cleanup
```

## Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: PIN verified
    Created --> Active: Worker assigned
    Active --> Suspended: Timeout or disconnect
    Suspended --> Active: Reconnect same device
    Active --> Transferred: New device connects
    Transferred --> Active: Session continues
    Active --> Ended: User logout
    Ended --> [*]
```

## Readiness Score: 1.5/10

| Category | Score | Blocker |
|----------|-------|---------|
| Data Isolation | 1/10 | Shared database, sandbox |
| Security | 2/10 | Session hijacking, plaintext |
| Scalability | 2/10 | SQLite, in-memory state |
| Token Tracking | 0/10 | Not implemented |
| Encryption | 0/10 | No zero-knowledge |

## Dependencies
- SEC-001: Session hijacking fix
- SEC-002: Per-user sandbox
- FEAT-001: Token tracking
- BUG-001, BUG-002: Race conditions

## Estimate
8-12 weeks for production-ready multi-tenancy

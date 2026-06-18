# MCP Server Generator

## Purpose

This skill generates production-ready MCP (Model Context Protocol) servers following a consistent architecture.

Use this skill whenever the user asks to create:

* MCP servers
* AI agent tools
* Data intelligence services
* Market data servers
* Analytics servers
* Monitoring servers
* Research servers
* Recommendation engines
* Retrieval services
* Agent-accessible APIs

The generated solution must be production-oriented rather than demo-oriented.

---

# Design Principles

Always generate:

1. Complete implementations.
2. Production-ready code.
3. No TODO placeholders.
4. Strong typing.
5. Unit tests.
6. Structured logging.
7. Configuration-driven architecture.
8. Provider abstraction.
9. Retry mechanisms.
10. Local persistence.
11. Docker support.
12. MCP-compliant tool registration.

---

# Default Technology Stack

Unless explicitly overridden:

Backend:

* Python 3.12+
* FastMCP

Configuration:

* Pydantic Settings
* YAML configuration

Database:

* SQLite for local deployments
* PostgreSQL optional

ORM:

* SQLAlchemy

Data Processing:

* Pandas
* NumPy

Networking:

* httpx

Retry:

* tenacity

Logging:

* structlog

Testing:

* pytest

Containerization:

* Docker
* Docker Compose

---

# Required Project Structure

Always generate:

```text id="nlmldn"
project/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── providers/
│   ├── services/
│   ├── tools/
│   └── utils/
│
├── scripts/
│
├── tests/
│
├── data/
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── config.yaml
├── .env.example
└── README.md
```

---

# Provider Pattern

Whenever external APIs or data sources exist:

Create provider abstraction.

Example:

```python id="k1n8jk"
class Provider(ABC):

    @abstractmethod
    async def fetch(self):
        pass
```

Implement:

* Base provider
* Concrete providers
* Provider manager
* Automatic fallback

---

# Provider Selection

Always support:

```yaml id="cf0j0j"
provider: primary_provider
```

through configuration.

If provider fails:

1. Retry.
2. Log.
3. Fallback.
4. Continue serving requests.

---

# Persistence Requirements

If data changes over time:

Create local persistence.

Default:

SQLite.

Use:

```sql id="40r2b8"
UNIQUE
```

constraints where applicable.

Use UPSERT operations.

Avoid duplicate data.

---

# Historical Data Strategy

If the domain has historical data:

Generate:

```text id="d4nmz8"
scripts/backfill_history.py
scripts/refresh_history.py
```

Capabilities:

* Initial data load
* Incremental refresh
* Deduplication
* Validation

---

# Collector Strategy

If the domain has live data:

Generate:

```text id="eehjlwm"
scripts/collect_current_data.py
```

Capabilities:

* Fetch latest data
* Retry failures
* Provider fallback
* Persist results

---

# MCP Tool Design

Tools should:

1. Return structured JSON.
2. Be agent-friendly.
3. Avoid presentation formatting.
4. Contain metadata.
5. Include confidence and source information when relevant.

Example:

```json id="jlwmu5"
{
  "value": 123,
  "source": "provider_name",
  "confidence": 0.92,
  "timestamp": "..."
}
```

---

# Tool Categories

Generate tools in these categories when applicable.

## Current State

Examples:

```text id="zj24q3"
get_current_price
get_current_weather
get_current_status
```

---

## Historical Data

Examples:

```text id="3t3z7j"
get_history
get_trends
get_metrics
```

---

## Analytics

Examples:

```text id="odlk77"
analyze
calculate_indicators
generate_summary
```

---

## Recommendations

Examples:

```text id="3zx2yq"
recommend
score
rank
evaluate
```

---

# Scoring Systems

When recommendations are requested:

Generate score-based systems.

Example:

```text id="sljnpz"
0-30   Poor
31-60  Neutral
61-80  Good
81-100 Strong
```

Always explain scoring rationale.

Never return unexplained recommendations.

---

# Logging Requirements

Always implement:

* info
* warning
* error

Log:

* provider selection
* retries
* failures
* fallback events
* tool invocations

Use structured logs.

---

# Testing Requirements

Always generate tests for:

* Providers
* Services
* Database layer
* Tool layer
* Scoring logic

Use pytest.

---

# Docker Requirements

Always generate:

```text id="5hyfzy"
Dockerfile
docker-compose.yml
```

The container must run the MCP server directly.

---

# README Requirements

Always generate:

* Installation
* Configuration
* Running locally
* Running with Docker
* MCP client integration
* Example tool outputs
* Troubleshooting

---

# Code Generation Rules

Always generate:

* Complete code
* Complete file contents
* Complete schemas
* Complete tests

Never generate:

* TODO
* Placeholder implementations
* Mock logic unless explicitly requested

The final output should be deployable immediately after dependency installation.

---

# Architecture Preference

Favor:

```text id="mnxjfr"
Provider
    ↓
Service
    ↓
Repository
    ↓
MCP Tool
```

over directly calling APIs from MCP tools.

Keep business logic inside services.

Keep MCP tools thin.

---

# Performance Preference

For small-to-medium workloads:

* SQLite
* Pandas

For large workloads:

* PostgreSQL
* ClickHouse

Choose based on domain requirements.

---

# Agent Compatibility

Generated MCP servers must be compatible with:

* Claude Desktop
* Hermes Agent
* OpenAI Agents SDK
* Cursor
* Windsurf
* Generic MCP Clients

Always include MCP configuration examples.

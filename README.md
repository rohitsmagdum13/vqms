# VQMS — Vendor Query Management System

Agentic AI Platform for automated vendor query handling, built with LangGraph, Amazon Bedrock (Claude), and AWS Step Functions.

## Overview

VQMS automates the end-to-end process of receiving vendor emails, analyzing intent, resolving vendor identity, creating/updating tickets, drafting responses, and monitoring SLA compliance.

## Tech Stack

- **Python 3.12+** with asyncio-first concurrency
- **LangGraph** for agent orchestration state machine
- **Amazon Bedrock** (Claude Sonnet 3.5) for LLM inference
- **AWS Step Functions** for high-level workflow coordination
- **PostgreSQL** (pgvector) for persistent storage and semantic search
- **Redis** for hot cache and idempotency
- **Microsoft Graph API** for email ingestion/sending
- **Salesforce CRM** for vendor resolution
- **ServiceNow ITSM** for ticket operations

## Quick Start

```bash
# Install dependencies with uv
uv sync --all-extras

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/

# Run tests
uv run pytest
```

## Project Structure

See `CLAUDE.md` for the complete folder structure and architecture details.

## Build Order

Follow the 10-phase bottom-up build plan documented in `CLAUDE.md`.

---

## Project Structure — Where Things Live

```
vqms/
│
├── README.md                    → Project overview — start here
├── pyproject.toml               → All Python dependencies managed by uv
├── main.py                      → Application entry point — run this to start VQMS
├── .env                         → Your local secrets (NEVER commit this)
├── .env.copy                    → Template for .env — copy and fill in your values
├── .gitignore                   → Files Git should ignore
├── .ruff.toml                   → Linting rules for ruff
├── .python-version              → Locks Python to 3.12
│
├── tasks/                       → Task tracking for development
│   ├── todo.md                  → Current task list with checkboxes
│   └── lessons.md               → Mistakes and learnings log
│
├── Doc/                         → High-level project documentation
│   ├── System_Architecture.md   → Architecture diagrams and explanations
│   ├── Application_Workflow.md  → How the app processes an email end-to-end
│   └── Agents.md                → What each AI agent does
│
│
├── security/                    → Security policies and configs
│   ├── guardrails_config.yaml   → AI guardrail rules
│   ├── access_control.yaml      → Who can access what
│   ├── encryption_config.yaml   → Encryption settings
│   ├── audit_logging_config.yaml→ What gets audited
│   ├── data_privacy_policy.md   → Privacy rules for data handling
│   └── gdpr_compliance_checklist.md → GDPR compliance tracker
│
├── config/                      → All YAML configuration files
│   ├── agents_config.yaml       → Agent personas, goals, backstories
│   ├── tools_config.yaml        → External tool/API settings
│   ├── model_config.yaml        → Bedrock Claude model parameters
│   ├── logging_config.yaml      → Structured logging format
│   ├── database_config.yaml     → PostgreSQL + Redis connection settings
│   ├── dev_config.yaml          → Overrides for local development
│   ├── test_config.yaml         → Overrides for test environment
│   └── prod_config.yaml         → Overrides for production
│
├── prompts/                     → Versioned AI prompt templates (Jinja2)
│   ├── email_analysis/v1.jinja  → Prompt for Email Analysis Agent
│   ├── communication_drafting/v1.jinja → Prompt for Drafting Agent
│   └── orchestration/v1.jinja   → Prompt for Orchestration decisions
│
├── src/                         → MAIN SOURCE CODE — all business logic lives here
│   ├── models/                  → Pydantic data models (the "shape" of every data object)
│   │   ├── email.py             → EmailMessage, EmailAttachment
│   │   ├── vendor.py            → VendorProfile, VendorMatch
│   │   ├── ticket.py            → TicketRecord, RoutingDecision
│   │   ├── workflow.py          → WorkflowState, CaseExecution
│   │   ├── communication.py     → DraftEmailPackage, ValidationReport
│   │   ├── memory.py            → EpisodicMemory, EmbeddingRecord
│   │   ├── budget.py            → Budget dataclass (token/cost limits)
│   │   └── messages.py          → AgentMessage envelope (inter-agent comms)
│   │
│   ├── agents/                  → AI agent definitions (the "brains")
│   │   ├── abc_agent.py         → Base class all agents inherit from
│   │   ├── email_analysis.py    → Reads emails → extracts intent, urgency, entities
│   │   ├── communication_drafting.py → Writes response emails to vendors
│   │   └── orchestration.py     → Decides what happens next (routing logic)
│   │
│   ├── services/                → Deterministic business logic (no AI, just rules)
│   │   ├── email_intake.py      → Fetches emails from Graph API, parses, stores
│   │   ├── vendor_resolution.py → Looks up vendor in Salesforce by email
│   │   ├── ticket_ops.py        → Creates/updates tickets in ServiceNow
│   │   └── memory_context.py    → Loads past context for the current email thread
│   │
│   ├── gates/                   → Quality checkpoints before sending anything out
│   │   └── quality_governance.py→ Validates drafts: ticket#, SLA wording, PII scan
│   │
│   ├── monitoring/              → Background watchers
│   │   └── sla_alerting.py      → Watches SLA clocks, triggers escalations at 70/85/95%
│   │
│   ├── adapters/                → External system connectors (API wrappers)
│   │   ├── graph_api.py         → Microsoft Graph API (Exchange Online emails)
│   │   ├── salesforce.py        → Salesforce CRM REST API
│   │   ├── servicenow.py        → ServiceNow REST API
│   │   └── bedrock.py           → Amazon Bedrock (Claude) — ALL LLM calls go here
│   │
│   ├── tools/                   → Custom tools agents can call
│   │   └── custom_tools.py      → Tool registry with pydantic input/output contracts
│   │
│   ├── memory/                  → State management layers
│   │   ├── short_term.py        → Redis — fast, temporary cache (session/thread state)
│   │   └── long_term.py         → pgvector — permanent semantic memory (RAG search)
│   │
│   ├── orchestration/           → Workflow engine
│   │   ├── graph.py             → LangGraph state machine (the main pipeline)
│   │   ├── router.py            → Routing logic (which flow variant to use)
│   │   ├── manager.py           → Hierarchical agent manager
│   │   └── step_functions.py    → AWS Step Functions integration
│   │
│   ├── db/                      → Database layer
│   │   ├── connection.py        → PostgreSQL async connection pool
│   │   └── migrations/          → SQL files that create the database tables
│   │       ├── 001_intake_schema.sql       → email_messages + email_attachments tables
│   │       ├── 002_workflow_schema.sql     → case_execution + ticket_link + routing_decision
│   │       ├── 003_memory_schema.sql       → vendor_profile_cache + episodic_memory + embedding_index
│   │       ├── 004_audit_schema.sql        → action_log + validation_results
│   │       └── 005_reporting_schema.sql    → sla_metrics
│   │
│   ├── cache/                   → Redis wrapper
│   │   └── redis_client.py      → Connection + key builders for 6 key families
│   │
│   ├── storage/                 → S3 file storage
│   │   └── s3_client.py         → Upload/download for all 4 S3 buckets
│   │
│   ├── events/                  → Event publishing
│   │   └── eventbridge.py       → Publishes all 17 EventBridge event types
│   │
│   ├── queues/                  → Message queues
│   │   └── sqs.py               → Producer/consumer for all 10 SQS queues + DLQ
│   │
│   ├── llm/                     → LLM utilities
│   │   ├── factory.py           → Creates the right model instance
│   │   ├── utils.py             → RAG chunking, indexing helpers
│   │   └── security_helpers.py  → PII redaction, encryption helpers
│   │
│   ├── utils/                   → Shared helper functions
│   │   ├── logger.py            → Structured JSON logging setup
│   │   ├── helpers.py           → General utility functions
│   │   ├── correlation.py       → Correlation ID generation
│   │   ├── retry.py             → Exponential backoff + circuit breaker
│   │   └── validation.py        → Input validation helpers
│   │
│   └── evaluation/              → Testing AI quality
│       ├── matrix.py            → Metrics collection
│       ├── eval.py              → LLM-as-a-judge evaluation
│       └── result_folder/       → Where eval results get saved
│
├── tests/                       → All test files
│   ├── conftest.py              → Shared fixtures (mock Bedrock, sample emails, etc.)
│   ├── unit/                    → Unit tests — one test file per source module
│   │   ├── test_models.py       → Schema validation tests
│   │   ├── test_email_intake.py → Email ingestion tests
│   │   └── ...                  → (mirrors every module in src/)
│   └── evals/                   → AI quality evaluations
│       ├── test_faithfulness.py → RAGAS faithfulness metric
│       ├── test_answer_relevance.py → Answer relevance scoring
│       └── golden_sets/         → Curated test input/expected output pairs
│
├── data/                        → Local data storage
│   ├── knowledge_base/          → RAG source documents
│   ├── vector_store/            → Local vector DB files
│   ├── logs/                    → Execution logs
│   └── artifacts/               → Generated output files
│
└── notebooks/                   → Jupyter notebooks for experimentation
    ├── tool_testing.ipynb       → Test individual tools/adapters
    └── agent_simulation.ipynb   → Simulate agent conversations
```

### Quick Reference — "Where Do I Put This?"

| I want to...                              | Put it in...                          |
|-------------------------------------------|---------------------------------------|
| Add a new AI agent                        | `src/agents/` (inherit from `abc_agent.py`) |
| Add a new data model                      | `src/models/` (pydantic model)        |
| Add a new external API connector          | `src/adapters/` (wrap the REST API)   |
| Add a deterministic business service      | `src/services/`                       |
| Add a new quality/validation check        | `src/gates/`                          |
| Add a new prompt template                 | `prompts/<agent_name>/v<N>.jinja`     |
| Add a new database table                  | `src/db/migrations/` (new SQL file)   |
| Add a utility/helper function             | `src/utils/`                          |
| Add a custom tool for agents              | `src/tools/custom_tools.py`           |
| Add/update environment variable           | `.env` AND `.env.copy`                |
| Add a YAML config                         | `config/`                             |
| Add a security policy                     | `security/`                           |
| Write a unit test                         | `tests/unit/test_<module_name>.py`    |
| Write an LLM eval test                    | `tests/evals/`                        |
| Add a golden test set                     | `tests/evals/golden_sets/`            |
| Add RAG source documents                  | `data/knowledge_base/`                |
| Experiment in a notebook                  | `notebooks/`                          |
| Track a new task                          | `tasks/todo.md`                       |
| Log a lesson learned                      | `tasks/lessons.md`                    |
| Write high-level docs                     | `Doc/`                                |

---

## Phase 1 -- What was built

Phase 1 is the foundation layer. Before any AI agents can analyze emails or draft replies, the system needs to know what an email looks like, how to store it, and where to cache things for speed. That's what this phase sets up: data shapes, database tables, and caching plumbing.

### Data models (src/models/)

These are Pydantic classes that define the shape of every object flowing through the system. If data enters VQMS, one of these models validates it.

| Model | File | What it represents |
|-------|------|--------------------|
| `EmailMessage` | email.py | An incoming vendor email. Sender, subject, recipients, Graph API IDs. Has a validator that normalizes email addresses to lowercase and auto-syncs the `has_attachments` flag. |
| `EmailAttachment` | email.py | A file attached to an email. Filename, size, S3 storage key, SHA-256 checksum. |
| `ParsedEmailPayload` | email.py | The extracted body text and headers after MIME parsing. Tracks whether the email is a reply and which thread it belongs to. |
| `VendorProfile` | vendor.py | A vendor pulled from Salesforce. Name, tier (platinum/gold/silver/bronze), SLA hours, account manager. Email is validated on the way in. |
| `VendorMatch` | vendor.py | The result of trying to match an email to a vendor. Includes which method worked (exact email, vendor ID, or fuzzy name match) and a confidence score. |
| `TicketRecord` | ticket.py | A ServiceNow ticket. Ticket number is validated against the `INC` + 7-10 digits format. Status, priority, SLA breach timestamp. |
| `TicketLink` | ticket.py | Links an email to a ticket. Records whether the ticket was created, updated, or reopened by that email. |
| `RoutingDecision` | ticket.py | The orchestrator's call on where an email goes: full auto, low confidence, existing ticket, reopen, or escalation. |
| `AnalysisResult` | workflow.py | What the Email Analysis Agent figured out: intent, urgency, sentiment, extracted entities, confidence score. |
| `CaseExecution` | workflow.py | Tracks one email's journey from intake to resolution. Current step, hop count (max 4), error state. |
| `WorkflowState` | workflow.py | The LangGraph state bag passed between nodes. Holds the case, vendor match, existing tickets, budget, and message history. |
| `DraftEmailPackage` | communication.py | A draft reply to a vendor. HTML body, plain text fallback, SLA statement, threading headers. Ticket number is validated. |
| `ValidationReport` | communication.py | The Quality Gate's report card. Did the draft pass? Ticket number valid? SLA wording correct? PII detected? |
| `EpisodicMemory` | memory.py | A resolved case stored for future reference. Intent, resolution summary, outcome, searchable tags, 180-day TTL. |
| `VendorProfileCache` | memory.py | Cached vendor info for fast lookups. Same data as `VendorProfile` but with a TTL and interaction count. |
| `EmbeddingRecord` | memory.py | A vector embedding for semantic search. 1024-dimensional vector (Amazon Titan), source text, metadata for filtering. |
| `Budget` | budget.py | Per-request cost limits. Max tokens in/out, dollar limit, max hops, deadline. Frozen dataclass -- can't be mutated once created. |
| `BudgetUsage` | budget.py | Mutable tracker that accumulates actual token and cost usage as agents run. |
| `AgentMessage` | messages.py | The envelope for all inter-agent communication. Role, content, tool calls, correlation ID, timestamp. |
| `ToolCall` | messages.py | A tool invocation record inside an agent message. Tool name + arguments. |

### Database migrations (src/db/migrations/)

Five SQL files that create 5 schemas and 11 tables in PostgreSQL:

| Migration | Schema | Tables | What they store |
|-----------|--------|--------|----------------|
| 001 | `intake` | `email_messages`, `email_attachments` | Raw email metadata. `message_id` is the idempotency key (if we've seen this Graph API ID before, skip it). Attachments reference their parent email with a foreign key cascade. |
| 002 | `workflow` | `case_execution`, `ticket_link`, `routing_decision` | The processing pipeline. Each case tracks an email from intake to resolution. Ticket links map emails to ServiceNow tickets. Routing decisions record why the orchestrator chose a particular path. |
| 003 | `memory` | `vendor_profile_cache`, `episodic_memory`, `embedding_index` | The memory layer. Vendor cache backs up the Redis hot cache. Episodic memory stores resolved cases with a 180-day TTL. Embedding index uses pgvector with an HNSW index for semantic search over 1024-dim vectors. |
| 004 | `audit` | `action_log`, `validation_results` | Every side-effect in the system writes to `action_log`. Every draft validation writes to `validation_results`. Nothing happens without a paper trail. |
| 005 | `reporting` | `sla_metrics` | SLA performance data. Response times, breach flags, escalation levels. Feeds the dashboards. |

The migration runner (`src/db/connection.py`) tracks which files have been applied in a `public.schema_migrations` table so it won't re-run them.

### Redis key helpers (src/cache/redis_client.py)

Six key-builder functions, one per cache family. Each returns a namespaced string like `vendor:001ABC123DEF456`.

| Function | Key pattern | What it caches |
|----------|-------------|---------------|
| `idempotency_key()` | `idempotency:{message_id}` | Prevents processing the same email twice. Set once when an email is ingested, checked before processing. |
| `thread_key()` | `thread:{conversation_id}` | Thread correlation data. Groups emails in the same conversation so replies get routed to existing tickets. |
| `ticket_key()` | `ticket:{ticket_number}` | Cached ticket data from ServiceNow. Saves an API call when we need to check ticket status mid-pipeline. |
| `workflow_key()` | `workflow:{case_id}` | Current workflow state. Lets the orchestrator resume a case if something restarts. |
| `vendor_key()` | `vendor:{vendor_id}` | Vendor profile hot cache. Backed by `memory.vendor_profile_cache` in PostgreSQL. Avoids hitting Salesforce on every email. |
| `sla_key()` | `sla:{ticket_number}` | SLA timer data. Tracks when warnings and escalations should fire. |

The client itself (`create_client`, `close_client`, `health_check`) uses `redis.asyncio` and pings on creation to verify the connection is alive.

### Utility modules

Four utility files that everything else depends on:

- **correlation.py** -- Generates UUID v4 correlation IDs and stores them in a `ContextVar`. Every function in the pipeline carries a `correlation_id` parameter. If you don't pass one, `ensure_correlation_id()` will generate one and stash it in the context for downstream code to pick up.
- **logger.py** -- Configures structlog for JSON output. Automatically injects the current correlation ID into every log line. No `print()` anywhere in this project.
- **validation.py** -- Input validators for system boundaries: email addresses (via `email-validator`), ServiceNow ticket numbers (`INC` + 7-10 digits), UUID v4 correlation IDs, Salesforce Account IDs (`001` + 12-15 alphanum chars), and a PII sanitizer that redacts emails, SSNs, and credit card numbers from log text.
- **helpers.py** -- `utc_now()` returns a timezone-aware UTC timestamp. `safe_json_serialize()` uses `orjson` and handles Pydantic models, dataclasses, enums, and datetimes. `truncate_for_log()` chops long strings for safe logging.

### How the pieces connect

Here's the path an email takes through the Phase 1 infrastructure:

```
Vendor sends email
      |
      v
Graph API delivers it
      |
      v
EmailMessage model validates the data
      |
      v
Raw email stored in S3 (vqms-email-raw-prod bucket)
      |
      v
Metadata inserted into intake.email_messages table
      |
      v
Redis sets idempotency:{message_id} so we never process it again
      |
      v
CaseExecution record created in workflow.case_execution
      |
      v
(Phase 2+ picks it up from here: analysis, vendor resolution, ticketing...)
```

Every step carries a `correlation_id`. Every side-effect writes to `audit.action_log`. If something crashes and restarts, the idempotency key in Redis prevents duplicate processing, and the case execution record in PostgreSQL tells the system where it left off.

### Test coverage

40 unit tests across all 8 model files. They verify:
- Valid construction with real-world data
- Field constraints (confidence between 0 and 1, hop count max 4, SLA hours minimum 1)
- Validators (bad email formats rejected, bad ticket numbers rejected, empty embeddings rejected)
- Defaults (new tickets start as "new", workflows start as "pending", budgets default to $0.50)
- Immutability (Budget is frozen, BudgetUsage is mutable)

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

# VQMS — Complete ASCII Flow Diagrams

## Real Example Used Throughout

```
WHO:    Rajesh Mehta, TechNova Solutions Pvt. Ltd. (VN-30892)
WHAT:   Payment status inquiry for Invoice #INV-2026-0451 (Rs.4,75,000)
RESULT: AI resolved in ~11 seconds, cost ~$0.033, ticket INC0019847
```

---

# ══════════════════════════════════════════════════════════════════
# OUTPUT 1: DETAILED TECHNICAL ASCII FLOW
# ══════════════════════════════════════════════════════════════════

```
╔══════════════════════════════════════════════════════════════════════════════╗
║        VQMS FULL END-TO-END TECHNICAL FLOW — Rajesh's Query Journey        ║
║        VQ-2026-0108 | Invoice #INV-2026-0451 | TechNova Solutions          ║
╚══════════════════════════════════════════════════════════════════════════════╝


┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: VENDOR LOGIN                                                        │
│                                                                              │
│ Input:   Rajesh's email (rajesh.mehta@technovasolutions.in) + password       │
│          OR Company SSO redirect                                             │
│                                                                              │
│ What happens:                                                                │
│   1. Rajesh enters credentials on the VQMS portal login page                 │
│   2. Credentials sent to authentication service                              │
│   3. Identity verified against user pool                                     │
│   4. Secure session token (JWT) created with claims:                         │
│        vendor_id = "VN-30892", role = "VENDOR"                               │
│        scopes = ["queries.own", "kb.read", "prefs.own"]                      │
│        expires in 8 hours                                                    │
│   5. Session cached for fast re-validation                                   │
│                                                                              │
│ Services used:                                                               │
│   - AWS Cognito (vqms-agent-portal-users): Validates email+password or       │
│     federated SSO, creates JWT with vendor claims and role scopes            │
│   - Redis (vqms:session:<token>): Stores session state with 8-hour TTL      │
│     for fast subsequent request validation                                   │
│   - Company SSO (Okta / Azure AD): If SSO path, handles password check      │
│     and returns SAML/OIDC assertion back to Cognito                          │
│                                                                              │
│ Output:  JWT session token with vendor_id=VN-30892, role=VENDOR              │
│          Rajesh can only see TechNova's data — enforced server-side          │
│                                                                              │
│ Time: < 800ms | Cost: $0.00 | LLM: No                                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: PORTAL DASHBOARD LOADS                                               │
│                                                                              │
│ Input:   JWT token from Step 1, vendor_id = VN-30892                         │
│                                                                              │
│ What happens:                                                                │
│   1. Browser sends GET /vendor/queries?vendor_id=INF with JWT                │
│   2. API Gateway validates the JWT via Cognito Authorizer                    │
│   3. Backend checks Redis cache for pre-computed KPIs                        │
│      - CACHE HIT (< 5 min old): use cached numbers, skip database           │
│      - CACHE MISS: query PostgreSQL for counts, compute KPIs,               │
│        write fresh cache entry with 5-min TTL                                │
│   4. Fetch 10 most recent queries for this vendor from PostgreSQL            │
│   5. Return dashboard payload to browser                                     │
│                                                                              │
│ Services used:                                                               │
│   - API Gateway + Cognito Authorizer: Validates JWT, extracts vendor_id,     │
│     rejects invalid/expired tokens with 401                                  │
│   - Redis (vqms:vendor:VN-30892:kpis): Fast KPI cache with 5-min TTL        │
│     Returns: open=3, resolved=11, avg_response=3.1h                          │
│   - PostgreSQL (workflow.case_execution): Source of truth for query           │
│     counts and recent queries when cache is expired                           │
│                                                                              │
│ Output:  Dashboard data: 3 open, 11 resolved, 3.1h avg, 4 recent queries    │
│          Rajesh sees: "Welcome back, Rajesh | TechNova Solutions"            │
│                                                                              │
│ Time: < 400ms (cache hit) / < 1200ms (cache miss) | Cost: $0.00 | LLM: No  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: WIZARD — PICK QUERY TYPE                                             │
│                                                                              │
│ Input:   Rajesh clicks "+ New Query" on dashboard                            │
│                                                                              │
│ What happens:                                                                │
│   1. Browser displays 6 query type cards:                                    │
│      Contract | Invoice | Delivery | Tech Support | SLA | Other              │
│   2. Rajesh selects "Invoice Issue"                                          │
│   3. Selection saved in browser memory ONLY (JavaScript variable)            │
│      WD.type = "invoice"                                                     │
│   4. NO server call is made — zero network traffic                           │
│                                                                              │
│ Services used:                                                               │
│   - Browser only (client-side React state): Stores selection locally         │
│     No backend, no Redis, no PostgreSQL, no API call                         │
│                                                                              │
│ Output:  WD.type = "invoice" stored in browser memory                        │
│          This becomes a classification HINT for the AI in Step 8             │
│          (AI still makes its own independent classification)                  │
│                                                                              │
│ Time: 0ms (instant) | Cost: $0.00 | LLM: No                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: WIZARD — FILL IN DETAILS                                             │
│                                                                              │
│ Input:   Query type "invoice" selected in Step 3                             │
│                                                                              │
│ What happens:                                                                │
│   1. Rajesh fills in subject:                                                │
│      "Payment Status Inquiry - Invoice #INV-2026-0451"                       │
│   2. Rajesh fills in description (478 chars):                                │
│      "I am writing on behalf of TechNova Solutions Pvt. Ltd.                 │
│       (Vendor Code: VN-30892) to inquire about the payment status..."        │
│   3. Selects priority: HIGH (portal shows "Expected response: 4 hours")      │
│   4. Enters reference: PO-HEX-78412                                         │
│   5. All data saved in browser memory ONLY — still no server call            │
│                                                                              │
│ Services used:                                                               │
│   - Browser only (client-side React state): Accumulates wizard data          │
│     WD = { type:"invoice", subject:"...", desc:"...",                        │
│            priority:"High", ref:"PO-HEX-78412" }                            │
│                                                                              │
│ Output:  Complete WD object in browser memory, ready for review              │
│          Subject+description = PRIMARY input to AI analysis (Step 8)         │
│          Priority = determines SLA deadline (High = 4 hours)                 │
│          Reference = used by routing to check Salesforce for existing PO     │
│                                                                              │
│ Time: 0ms (vendor's typing time) | Cost: $0.00 | LLM: No                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: WIZARD — REVIEW & CONFIRM                                            │
│                                                                              │
│ Input:   Complete WD object from Steps 3-4                                   │
│                                                                              │
│ What happens:                                                                │
│   1. Browser renders summary card showing all entered data:                  │
│      Type: Invoice Issue | Subject: Payment Status...                        │
│      Priority: High | Reference: PO-HEX-78412                               │
│      Company: TechNova Solutions | Expected SLA: 4 hours                     │
│   2. "Assigned to: Auto (QueryAnalysisAgent)" shown — AI handles first       │
│   3. Rajesh can click "Back" to change any field                             │
│   4. Still NO server call — last chance to edit before submission             │
│                                                                              │
│ Services used:                                                               │
│   - Browser only (client-side rendering): Displays confirmation view         │
│                                                                              │
│ Output:  Rajesh confirms and clicks "Submit Query"                           │
│          Browser builds POST payload with WD fields + vendor_id from JWT     │
│                                                                              │
│ Time: 0ms (vendor's review time) | Cost: $0.00 | LLM: No                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 6: SUBMIT QUERY — FIRST SERVER CONTACT                                  │
│                                                                              │
│ Input:   POST /queries with JWT + payload:                                   │
│          { type:"invoice", subject:"Payment Status Inquiry -                 │
│            Invoice #INV-2026-0451", description:"I am writing on             │
│            behalf of TechNova...", priority:"High",                           │
│            reference:"PO-HEX-78412" }                                        │
│          NOTE: vendor_id is NOT in payload — extracted from JWT              │
│                                                                              │
│ What happens:                                                                │
│                                                                              │
│   SUB-STEP 6.1: API GATEWAY + COGNITO AUTHORIZER                            │
│     - Receives HTTPS request, passes JWT to Cognito                          │
│     - Cognito validates: signature OK, not expired, role=VENDOR              │
│     - Extracts vendor_id=VN-30892 and attaches to request context            │
│     - Forwards enriched request to Query API Service                         │
│                                                                              │
│   SUB-STEP 6.2: QUERY API SERVICE — VALIDATE                                │
│     - Pydantic model (QuerySubmission) validates all fields                  │
│     - type: "invoice" -> valid | subject: present -> valid                   │
│     - description: 478 chars -> valid | priority: "High" -> valid            │
│                                                                              │
│   SUB-STEP 6.3: GENERATE IDENTIFIERS                                        │
│     - query_id:       VQ-2026-0108 (sequential, human-readable)              │
│     - execution_id:   b2c4d6e8-... (UUID v4, internal tracking)              │
│     - correlation_id: f1a2b3c4-... (UUID v4, cross-system linking)           │
│                                                                              │
│   SUB-STEP 6.4: IDEMPOTENCY CHECK                                           │
│     - Redis GET vqms:idempotency:<sha256(subject+desc+vendor)>               │
│     - Result: NOT FOUND -> new query, proceed                                │
│     - If FOUND: would return existing query_id (prevents double-submit)      │
│                                                                              │
│   SUB-STEP 6.5: SAVE TO DATABASE                                            │
│     - INSERT INTO workflow.case_execution with all fields                    │
│     - status = 'OPEN', created_at = 2026-04-02T08:14:00Z                    │
│                                                                              │
│   SUB-STEP 6.6: SET IDEMPOTENCY GUARD                                       │
│     - Redis SET vqms:idempotency:<hash> "VQ-2026-0108" EX 604800 (7 days)   │
│                                                                              │
│   SUB-STEP 6.7: PUBLISH EVENT                                               │
│     - EventBridge: QueryReceived on vqms-event-bus                           │
│     - Payload: { query_id, vendor_id, priority, timestamp }                  │
│                                                                              │
│   SUB-STEP 6.8: QUEUE FOR AI PIPELINE                                       │
│     - SQS: Push full query payload to vqms-query-intake-queue                │
│     - DLQ: vqms-dlq configured (3 retries before dead-letter)                │
│                                                                              │
│   SUB-STEP 6.9: RETURN RESPONSE TO BROWSER                                  │
│     - HTTP 201 Created                                                       │
│     - { query_id:"VQ-2026-0108", status:"Open",                             │
│         sla_deadline:"2026-04-02T12:14:00Z" }                                │
│                                                                              │
│ Services used:                                                               │
│   - API Gateway + Cognito Authorizer: JWT validation, vendor_id extraction   │
│   - Query API Service (Pydantic): Payload validation, ID generation          │
│   - Redis: Idempotency check (GET) + guard (SET with 7-day TTL)             │
│   - PostgreSQL (workflow.case_execution): Persist query record               │
│   - EventBridge (vqms-event-bus): Publish QueryReceived event                │
│   - SQS (vqms-query-intake-queue): Queue message for async AI pipeline       │
│                                                                              │
│ Output:  Rajesh gets VQ-2026-0108 in ~400ms. Browser shows success screen.   │
│          Writes: PostgreSQL(1), Redis(2), SQS(1), EventBridge(1)             │
│                                                                              │
│ Time: < 500ms | Cost: $0.00 | LLM: No                                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
          ═════════════════════════════════════════════════════
           ★ ASYNC BOUNDARY — Rajesh gets his response HERE.
             Everything below runs in the background.
             Rajesh does NOT wait. He can close his browser.
          ═════════════════════════════════════════════════════
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 7: LANGGRAPH ORCHESTRATOR — CONTEXT LOADING                             │
│                                                                              │
│ Input:   SQS message from vqms-query-intake-queue containing full query      │
│          payload (execution_id, query_id, vendor_id, type, subject,          │
│          description, priority, reference, created_at)                        │
│                                                                              │
│ What happens:                                                                │
│                                                                              │
│   SUB-STEP 7.1: UPDATE STATUS                                               │
│     - PostgreSQL: UPDATE case_execution SET status='ANALYZING'               │
│                                                                              │
│   SUB-STEP 7.2: CACHE WORKFLOW STATE                                         │
│     - Redis SET vqms:workflow:b2c4d6e8-...                                   │
│       { status:"ANALYZING", query_id:"VQ-2026-0108",                         │
│         vendor_id:"VN-30892", step:"INIT" }                                  │
│       TTL = 24 hours                                                         │
│                                                                              │
│   SUB-STEP 7.3: LOAD VENDOR PROFILE                                         │
│     - Redis GET vqms:vendor:VN-30892                                         │
│     - Result: CACHE MISS (TechNova profile expired > 1 hour ago)             │
│     - Fallback to Salesforce CRM API:                                        │
│       SELECT Account WHERE Vendor_Id__c = 'VN-30892'                         │
│     - Result: tier=SILVER, risk_flags=["OVERDUE_INVOICE_HISTORY"],           │
│       account_manager="Anil Kapoor", payment_terms="Net 30"                  │
│     - Cache result: Redis SET vqms:vendor:VN-30892 <json> EX 3600 (1 hour)  │
│                                                                              │
│   SUB-STEP 7.4: LOAD VENDOR HISTORY (EPISODIC MEMORY)                       │
│     - PostgreSQL SELECT FROM memory.episodic_memory                          │
│       WHERE vendor_id='VN-30892' ORDER BY created_at DESC LIMIT 5            │
│     - Result: 3 prior queries in 90 days:                                    │
│       1. "Invoice INV-2026-0203 payment delay" resolved 2.8h                 │
│       2. "PO mismatch on PO-HEX-71234" resolved 4.1h                        │
│       3. "GST credit note request" resolved 6.2h                             │
│                                                                              │
│ Services used:                                                               │
│   - LangGraph Orchestrator: SQS consumer, workflow initialization            │
│   - SQS (vqms-query-intake-queue): Source of trigger message                 │
│   - PostgreSQL (workflow.case_execution): Status update                       │
│   - Redis (vqms:workflow:*): Workflow state cache (24h TTL)                   │
│   - Redis (vqms:vendor:VN-30892): Vendor profile cache check (MISS)         │
│   - Salesforce CRM API: Vendor master lookup (tier, risk, contacts)          │
│   - Redis (vqms:vendor:VN-30892): Cache Salesforce result (1h TTL)           │
│   - PostgreSQL (memory.episodic_memory): Historical vendor interactions      │
│                                                                              │
│ Output:  Full context package assembled:                                     │
│          { query, vendor_profile (Silver, risk flags),                        │
│            vendor_history (3 prior queries), execution_metadata }             │
│          Ready for AI analysis                                               │
│                                                                              │
│ Time: ~800ms (Salesforce miss adds ~200ms) | Cost: $0.00 | LLM: No          │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 8: QUERY ANALYSIS AGENT — LLM CALL #1                                  │
│                                                                              │
│ Input:   Full context package from Step 7:                                   │
│          - Query: type, subject, description, reference                      │
│          - Vendor profile: TechNova, Silver tier, OVERDUE_INVOICE_HISTORY    │
│          - History: 3 prior queries (payment patterns)                        │
│                                                                              │
│ What happens:                                                                │
│                                                                              │
│   SUB-STEP 8.1: LOAD PROMPT TEMPLATE                                        │
│     - S3 GET from vqms-knowledge-artifacts-prod                              │
│       templates/query-analysis/v2.json                                       │
│                                                                              │
│   SUB-STEP 8.2: BUILD PROMPT                                                │
│     - System: "You are a query analysis agent for VQMS. Return JSON:         │
│       intent_classification, extracted_entities, urgency_level,               │
│       sentiment, confidence_score, multi_issue_detected,                      │
│       suggested_category"                                                    │
│     - User: query fields + vendor profile + history                          │
│                                                                              │
│   SUB-STEP 8.3: CALL BEDROCK (Claude Sonnet 3.5)                            │
│     - Temperature: 0.1 (low for classification precision)                    │
│     - Max tokens: 500 | Input: ~1,500 tokens | Output: ~500 tokens           │
│                                                                              │
│   SUB-STEP 8.4: PARSE RESPONSE (Pydantic: AnalysisResult)                   │
│     - intent: PAYMENT_QUERY (not INVOICE_DISPUTE — he's asking where         │
│       his money is, not arguing about the amount)                             │
│     - entities: INV-2026-0451, 2026-02-15, Rs.475000, PO-HEX-78412,         │
│       due 2026-03-17, VN-30892, TechNova, Rajesh Mehta                       │
│     - urgency: HIGH (16 days overdue)                                        │
│     - sentiment: POLITE_CONCERNED                                            │
│     - confidence: 0.96 (very clear intent, structured message)               │
│     - multi_issue: false                                                     │
│                                                                              │
│   SUB-STEP 8.5: CONFIDENCE BRANCH                                           │
│     - 0.96 >= 0.85 threshold -> PATH: FULL_AUTOMATION                        │
│     - If < 0.85: would route to human review (Step 7B)                       │
│                                                                              │
│   SUB-STEP 8.6: SAVE & PUBLISH                                              │
│     - S3: prompt snapshot for audit trail                                     │
│     - PostgreSQL: UPDATE case_execution with analysis_result                  │
│     - Redis: workflow state -> ANALYSIS_COMPLETE                              │
│     - PostgreSQL: INSERT audit.action_log (ANALYSIS_COMPLETED)               │
│     - EventBridge: AnalysisCompleted event                                   │
│                                                                              │
│ Services used:                                                               │
│   - S3 (vqms-knowledge-artifacts-prod): Load versioned prompt template       │
│   - Amazon Bedrock (Claude Sonnet 3.5): LLM inference for classification     │
│     via Bedrock Integration Service (single LLM gateway)                     │
│   - S3 (vqms-knowledge-artifacts-prod): Store prompt snapshot for audit      │
│   - PostgreSQL (workflow.case_execution): Store analysis result (JSONB)       │
│   - PostgreSQL (audit.action_log): Immutable audit record                    │
│   - Redis (vqms:workflow:*): Update workflow state cache                      │
│   - EventBridge (vqms-event-bus): Publish AnalysisCompleted event            │
│                                                                              │
│ Output:  AnalysisResult: { intent:PAYMENT_QUERY, confidence:0.96,            │
│          urgency:HIGH, sentiment:POLITE_CONCERNED, multi_issue:false }        │
│          Decision: FULL_AUTOMATION (high confidence, clear intent)            │
│                                                                              │
│ Time: ~3 seconds | Cost: ~$0.012 | LLM: YES (Bedrock Claude Sonnet 3.5)     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 9: ROUTING + KB SEARCH — PARALLEL EXECUTION (NO LLM)                    │
│                                                                              │
│ Input:   AnalysisResult + VendorProfile + TicketCorrelation                  │
│                                                                              │
│ ┌────────────────────────────────┐ ┌────────────────────────────────────┐    │
│ │ 9A: ROUTING SERVICE            │ │ 9B: KB SEARCH SERVICE              │    │
│ │ (deterministic rules engine)   │ │ (embedding + pgvector search)      │    │
│ │                                │ │                                    │    │
│ │ Rules evaluated:               │ │ 1. Embed query text:               │    │
│ │  confidence >= 0.85? YES(0.96) │ │    Bedrock Titan v2 -> vector(1536)│    │
│ │  urgency == CRITICAL? NO(HIGH) │ │                                    │    │
│ │  existing ticket? NO           │ │ 2. pgvector cosine similarity:     │    │
│ │  BLOCK_AUTOMATION flag? NO     │ │    SELECT FROM embedding_index     │    │
│ │                                │ │    WHERE category='invoice_payment'│    │
│ │ Decision: FULL_AUTOMATION      │ │    ORDER BY similarity DESC        │    │
│ │ Team: Finance Team             │ │    LIMIT 5                         │    │
│ │ SLA: 4 hours (High + Silver)   │ │                                    │    │
│ │ Risk: OVERDUE_INVOICE_HISTORY  │ │ 3. Results:                        │    │
│ │  -> logged, not blocking       │ │    KB#1203 "Invoice Payment        │    │
│ │                                │ │     Status Check Procedure"  96%   │    │
│ │ PostgreSQL INSERT              │ │    KB#891  "Overdue Invoice         │    │
│ │  routing_decision              │ │     Escalation Policy"       89%   │    │
│ │                                │ │    KB#1456 "AP Payment Timeline     │    │
│ │ Time: <50ms | Cost: $0.00     │ │     by Vendor Tier"          82%   │    │
│ │                                │ │    KB#672  "Three-Way Match         │    │
│ │                                │ │     Failure Resolution"      71%   │    │
│ │                                │ │                                    │    │
│ │                                │ │ Top 3 passed to ResolutionAgent    │    │
│ │                                │ │ Time: <200ms | Cost: ~$0.0001     │    │
│ └────────────────────────────────┘ └────────────────────────────────────┘    │
│                                                                              │
│ Services used:                                                               │
│   - RoutingService (rules engine): Deterministic routing based on            │
│     intent + vendor tier + urgency + risk flags + policy matrix              │
│   - PostgreSQL (workflow.routing_decision): Persist routing decision          │
│   - Amazon Bedrock (Titan Embed v2): Embed query text to vector(1536)       │
│   - PostgreSQL + pgvector (memory.embedding_index): Cosine similarity        │
│     search across knowledge base articles                                    │
│                                                                              │
│ Output:  Routing: FULL_AUTOMATION, Finance Team, 4h SLA                      │
│          KB matches: 4 articles (96%, 89%, 82%, 71% similarity)              │
│                                                                              │
│ Time: < 200ms (parallel) | Cost: ~$0.0001 | LLM: No (embedding only)        │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 10: RESOLUTION AGENT — LLM CALL #2                                      │
│                                                                              │
│ Input:   AnalysisResult + KB articles (3 full texts) + VendorProfile +       │
│          SLA (4h) + Vendor history (3 prior queries)                         │
│                                                                              │
│ What happens:                                                                │
│                                                                              │
│   SUB-STEP 10.1: LOAD PROMPT TEMPLATE                                       │
│     - S3: templates/resolution/v3.json                                       │
│                                                                              │
│   SUB-STEP 10.2: ASSEMBLE FULL CONTEXT                                      │
│     - Query: subject, description, reference                                 │
│     - Analysis: PAYMENT_QUERY, HIGH, URGENT, confidence 0.96                 │
│     - KB#1203 full text (96% match), KB#891 (89%), KB#1456 (82%)             │
│     - Vendor: TechNova, Silver tier, OVERDUE_INVOICE_HISTORY                 │
│     - SLA: 4 hours | History: 3 prior resolved queries                       │
│                                                                              │
│   SUB-STEP 10.3: CALL BEDROCK (Claude Sonnet 3.5)                           │
│     - Temperature: 0.3 | Max: 1000 tokens                                   │
│     - Input: ~3,000 tokens | Output: ~800 tokens                             │
│                                                                              │
│   SUB-STEP 10.4: PARSE RESPONSE (Pydantic: DraftResponse)                   │
│     - subject: "RE: Payment Status Inquiry - Invoice #INV-2026-0451          │
│                 [INC0019847]"                                                 │
│     - body: "Dear Rajesh, Thank you for reaching out regarding               │
│       Invoice #INV-2026-0451... invoice passed three-way match on            │
│       Feb 28... payment scheduled April 5 processing run...                  │
│       credit by April 10... expedited payment available..."                  │
│     - confidence: 0.93                                                       │
│     - sources_cited: ["KB#1203", "KB#891"]                                   │
│     - sla_statement: "Response within 4 hours per Silver tier SLA"           │
│                                                                              │
│   SUB-STEP 10.5: SAVE & PUBLISH                                             │
│     - PostgreSQL: UPDATE case_execution with response_draft                   │
│     - S3: prompt snapshot for audit                                           │
│     - Redis: workflow state updated                                           │
│     - EventBridge: DraftPrepared event                                       │
│                                                                              │
│ Services used:                                                               │
│   - S3 (vqms-knowledge-artifacts-prod): Load resolution prompt template      │
│   - Amazon Bedrock (Claude Sonnet 3.5): Generate response draft with         │
│     KB context, vendor profile, and SLA commitment                           │
│   - PostgreSQL (workflow.case_execution): Store draft (JSONB column)          │
│   - S3 (vqms-knowledge-artifacts-prod): Prompt snapshot for audit            │
│   - Redis (vqms:workflow:*): Update workflow state                            │
│   - EventBridge (vqms-event-bus): Publish DraftPrepared event                │
│                                                                              │
│ Output:  DraftResponse: subject, body (with ticket#, SLA, next steps),       │
│          confidence 0.93, 2 KB sources cited                                 │
│          AI anticipates Rajesh's follow-up: offers expedited payment          │
│                                                                              │
│ Time: ~4 seconds | Cost: ~$0.021 | LLM: YES (Bedrock Claude Sonnet 3.5)     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 11: QUALITY & GOVERNANCE GATE                                           │
│                                                                              │
│ Input:   DraftResponse + TicketRecord + VendorProfile + Policy rules         │
│                                                                              │
│ What happens:                                                                │
│                                                                              │
│   PHASE 1: DETERMINISTIC CHECKS (no LLM)                                    │
│     [PASS] Ticket # format: INC\d{7} regex matches INC0019847               │
│     [PASS] SLA wording: "4 hours" matches Silver/High policy                 │
│     [PASS] Required sections: greeting, status update, timeline,             │
│            next steps, ticket reference, signature — all present             │
│     [PASS] Restricted terms: 0 matches on blocklist                          │
│     [PASS] Response length: 163 words (range 50-500)                         │
│     [PASS] Source citations: 2 KB articles cited (minimum 1)                 │
│                                                                              │
│   PHASE 2: CONDITIONAL CHECKS (runs because priority = HIGH)                 │
│     [PASS] PII scan via Amazon Comprehend DetectPiiEntities:                 │
│            - Detected in original query: phone number (+91 98765 43210)      │
│            - Detected in draft response: NONE                                │
│            - AI correctly excluded Rajesh's phone from outbound email!       │
│     [SKIP] Tone check via Bedrock: no near-miss terms, no negative           │
│            sentiment -> LLM call skipped (saves $0.012)                      │
│                                                                              │
│   OVERALL RESULT: ██████████ 7/7 PASS ████████████                           │
│                                                                              │
│   IF FAIL (not this case):                                                   │
│     -> Re-draft (Communication Drafting Agent, max 2 retries)                │
│     -> If still failing after re-drafts -> human review queue                │
│                                                                              │
│   SUB-STEP 11.5: SAVE & PUBLISH                                             │
│     - S3: audit/INC0019847/<timestamp>/validation-report.json                │
│     - PostgreSQL: INSERT audit.validation_results (7/7 PASS, pii:false)      │
│     - EventBridge: ValidationPassed event                                    │
│                                                                              │
│ Services used:                                                               │
│   - QualityGateAgent: Deterministic rule-based validation engine             │
│     Checks ticket#, SLA wording, template compliance, restricted terms,      │
│     response length, source citations                                        │
│   - Amazon Comprehend (DetectPiiEntities): Scans draft body for PII          │
│     Ensures no personal data leaks into outbound communications              │
│   - S3 (vqms-audit-artifacts-prod): Store validation report                  │
│   - PostgreSQL (audit.validation_results): Persist check results             │
│   - EventBridge (vqms-event-bus): Publish ValidationPassed event             │
│                                                                              │
│ Output:  ValidationReport: 7/7 PASS, no PII in draft, proceed to send       │
│                                                                              │
│ Time: < 200ms | Cost: $0.00 (deterministic path) | LLM: No                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 12: TICKET CREATION + EMAIL DELIVERY                                    │
│                                                                              │
│ Input:   Validated DraftResponse + AnalysisResult + VendorProfile             │
│                                                                              │
│ What happens:                                                                │
│                                                                              │
│   SUB-STEP 12.1: CHECK FOR EXISTING TICKET                                  │
│     - PostgreSQL SELECT FROM workflow.ticket_link                            │
│       WHERE correlation_id = 'f1a2b3c4-...'                                  │
│     - Result: NONE -> create new ticket                                      │
│                                                                              │
│   SUB-STEP 12.2: CREATE SERVICENOW TICKET                                   │
│     - POST /api/now/table/incident                                           │
│       { category:"Invoice", subcategory:"Payment Status",                    │
│         urgency:2, impact:3, assignment_group:"Finance Team",                │
│         short_description:"Payment Status Inquiry -                          │
│           Invoice #INV-2026-0451 | TechNova Solutions",                      │
│         caller_id:<salesforce_contact_sys_id>,                               │
│         correlation_id:"f1a2b3c4-..." }                                      │
│     - Response: { sys_id:"xyz789abc012", number:"INC0019847" }               │
│                                                                              │
│   SUB-STEP 12.3: SAVE TICKET MAPPING                                        │
│     - PostgreSQL INSERT workflow.ticket_link                                 │
│       (query_id, ticket_id, ticket_number, ticket_status, correlation_id)    │
│                                                                              │
│   SUB-STEP 12.4: CACHE TICKET                                               │
│     - Redis SET vqms:ticket:xyz789abc012                                     │
│       { number:"INC0019847", group:"Finance Team", sla:4 } TTL 1h           │
│                                                                              │
│   SUB-STEP 12.5: UPDATE STATUS                                              │
│     - PostgreSQL: UPDATE case_execution SET status='RESPONDED'               │
│     - Redis: vqms:workflow:b2c4d6e8-... -> status:"COMPLETE"                 │
│                                                                              │
│   SUB-STEP 12.6: SEND EMAIL TO RAJESH                                       │
│     - MS Graph API: POST .../users/vendor-support@hexaware.com/sendMail      │
│     - To: rajesh.mehta@technovasolutions.in                                  │
│     - Subject: "RE: Payment Status Inquiry -                                 │
│                 Invoice #INV-2026-0451 [INC0019847]"                         │
│     - Body: Full response with ticket#, SLA statement, resolution,           │
│       payment timeline (April 5 processing, April 10 credit),               │
│       offer for expedited payment                                            │
│                                                                              │
│   SUB-STEP 12.7: AUDIT & PUBLISH                                            │
│     - PostgreSQL: INSERT audit.action_log (EMAIL_SENT)                       │
│     - EventBridge: TicketCreated + EmailSent + QueryResolved events           │
│                                                                              │
│ Services used:                                                               │
│   - PostgreSQL (workflow.ticket_link): Check existing + store mapping         │
│   - ServiceNow ITSM (REST API): Create incident INC0019847, assign to        │
│     Finance Team with urgency/impact/category from analysis                  │
│   - Redis (vqms:ticket:*): Cache hot ticket context (1h TTL)                 │
│   - PostgreSQL (workflow.case_execution): Update status to RESPONDED          │
│   - Redis (vqms:workflow:*): Update workflow state to COMPLETE               │
│   - Microsoft Graph API (/sendMail): Send email to Rajesh preserving         │
│     thread headers (In-Reply-To, References)                                 │
│   - PostgreSQL (audit.action_log): Immutable audit record of send            │
│   - EventBridge (vqms-event-bus): Publish 3 events                           │
│                                                                              │
│ Output:  Ticket INC0019847 created in ServiceNow, assigned to Finance Team   │
│          Email sent to rajesh.mehta@technovasolutions.in                      │
│          Status: RESPONDED | Writes: ServiceNow(1), PG(3), Redis(2), EB(3)   │
│                                                                              │
│ Time: ~2.5 seconds | Cost: $0.00 | LLM: No                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 13: SLA MONITORING — BACKGROUND PROCESS                                 │
│                                                                              │
│ Input:   TicketCreated event from Step 12 (ticket_id, vendor_tier, SLA)      │
│                                                                              │
│ What happens:                                                                │
│                                                                              │
│   SUB-STEP 13.1: CALCULATE SLA THRESHOLDS                                   │
│     - SLA: 4 hours (Silver tier + High priority)                             │
│     - Created: 08:14:00 | Deadline: 12:14:00                                 │
│     - 70% mark: 08:14 + 2h48m = 11:02                                       │
│     - 85% mark: 08:14 + 3h24m = 11:38                                       │
│     - 95% mark: 08:14 + 3h48m = 12:02                                       │
│                                                                              │
│   SUB-STEP 13.2: SET SLA STATE                                              │
│     - Redis SET vqms:sla:xyz789abc012                                        │
│       { start:"08:14", target_hours:4, deadline:"12:14",                     │
│         elapsed_pct:0, next_threshold:70 }                                   │
│       NO TTL — persists until ticket closed                                  │
│                                                                              │
│   TIMELINE (if query was NOT already resolved):                              │
│     11:02  70% elapsed -> SLAWarning70 -> notify assigned resolver           │
│     11:38  85% elapsed -> SLAEscalation85 -> L1 manager via                  │
│            vqms-escalation-queue                                             │
│     12:02  95% elapsed -> SLAEscalation95 -> L2 senior management            │
│     12:14  100% DEADLINE -> SLA BREACHED                                     │
│                                                                              │
│   FOR RAJESH'S QUERY: Already resolved in ~11 seconds                        │
│     breach: false, actual_time: 0.003 hours, escalation_level: 0             │
│                                                                              │
│   SUB-STEP 13.3: RECORD SLA METRICS                                         │
│     - PostgreSQL: INSERT reporting.sla_metrics                               │
│       (ticket_id, vendor_tier, sla_target:4, actual_hours:0.003,             │
│        breach:false, escalation_level:0)                                     │
│                                                                              │
│ Services used:                                                               │
│   - AWS Step Functions (vqms-sla-monitor): Wait-state based timer            │
│     Calculates thresholds, waits, checks ticket status, fires events         │
│   - Redis (vqms:sla:<ticket-id>): SLA state tracking (no TTL)               │
│   - EventBridge (vqms-event-bus): SLA warning/escalation events              │
│     SLAWarning70, SLAEscalation85, SLAEscalation95                          │
│   - SQS (vqms-escalation-queue): Delivers escalation alerts to managers      │
│   - PostgreSQL (reporting.sla_metrics): SLA performance data for reporting   │
│                                                                              │
│ Output:  SLA tracked. For Rajesh: breach=false (resolved in seconds).        │
│          Metrics recorded for dashboards and reporting.                       │
│                                                                              │
│ Time: Runs for hours (background) | Cost: $0.00 | LLM: No                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║ DONE — Rajesh opens "My Queries" 30 seconds later and sees:                 ║
║                                                                              ║
║   VQ-2026-0108 | RESPONDED | Ticket: INC0019847 | SLA: 3h 59m remaining    ║
║   AI Resolution: Invoice passed 3-way match Feb 28. Payment approved,       ║
║   scheduled for April 5. Expected credit by April 10.                       ║
║                                                                              ║
║ Email arrives in Rajesh's inbox within seconds of pipeline completion.       ║
║                                                                              ║
║ TOTAL: ~11 seconds end-to-end | ~$0.033 cost | 2 LLM calls + 1 embedding   ║
║ WRITES: PostgreSQL(12), Redis(9), S3(3), ServiceNow(1), MS Graph(1),        ║
║         Bedrock(3), Comprehend(1), EventBridge(7), SQS(1)                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

# ══════════════════════════════════════════════════════════════════
# OUTPUT 2: SIMPLE MANAGER-FRIENDLY ASCII FLOW
# ══════════════════════════════════════════════════════════════════

```
╔══════════════════════════════════════════════════════════════════════════════╗
║   VQMS — HOW A VENDOR QUERY GETS HANDLED (Simple Business View)            ║
║                                                                              ║
║   Example: Rajesh from TechNova asks about a late payment on his invoice.   ║
║   Result: He gets a helpful response in his inbox in under 1 minute.        ║
║   Cost to us: about 3 cents.                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝


┌──────────────────────────────────────────────────────────────────┐
│  STEP 1: VENDOR LOGS IN                                          │
│                                                                  │
│  What comes in:  Rajesh opens the VQMS portal and signs in       │
│                  with his email and password.                     │
│                                                                  │
│  What happens:   The system checks his identity and creates      │
│                  a secure session. Rajesh can only see his own    │
│                  company's data — TechNova's queries. He can      │
│                  never see another vendor's information.          │
│                                                                  │
│  What goes out:  Rajesh is logged in. His session is valid       │
│                  for 8 hours.                                     │
│                                                                  │
│  Time: Less than 1 second                                        │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 2: RAJESH SEES HIS DASHBOARD                               │
│                                                                  │
│  What comes in:  Rajesh's login session.                         │
│                                                                  │
│  What happens:   The portal shows Rajesh a personalized          │
│                  dashboard with his company's numbers:            │
│                    - 3 queries currently open                     │
│                    - 11 resolved this period                      │
│                    - Average response time: 3.1 hours             │
│                  Plus his 4 most recent queries.                  │
│                                                                  │
│  What goes out:  Rajesh clicks "+ New Query" to start.           │
│                                                                  │
│  Time: Under half a second                                       │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEPS 3-5: RAJESH FILLS IN HIS QUERY (3-step wizard)            │
│                                                                  │
│  What comes in:  Empty form.                                     │
│                                                                  │
│  What happens:   Rajesh walks through a simple 3-step wizard:    │
│                                                                  │
│    Step 3: Picks type — "Invoice Issue"                          │
│    Step 4: Fills in details:                                     │
│      - Subject: "Payment Status Inquiry -                        │
│                  Invoice #INV-2026-0451"                          │
│      - Description: explains the invoice is 16 days overdue      │
│      - Priority: High (4-hour response expected)                 │
│      - Reference: PO-HEX-78412                                   │
│    Step 5: Reviews everything and clicks "Submit Query"          │
│                                                                  │
│  Important: During these 3 steps, nothing is sent to the         │
│  server yet. All data stays in Rajesh's browser until he         │
│  clicks Submit. He can go back and change anything.              │
│                                                                  │
│  What goes out:  Rajesh clicks "Submit Query" — now it's real.   │
│                                                                  │
│  Time: However long Rajesh takes to type                         │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 6: QUERY IS RECEIVED AND LOGGED                            │
│                                                                  │
│  What comes in:  Rajesh's complete query submission.             │
│                                                                  │
│  What happens:   This is the moment the query enters the         │
│                  system. In about half a second, the system:      │
│                    1. Checks the data is valid                    │
│                    2. Assigns tracking number: VQ-2026-0108       │
│                    3. Checks for duplicates (prevents double      │
│                       submissions if Rajesh clicks twice)         │
│                    4. Saves the query to the database             │
│                    5. Announces "new query arrived" to the        │
│                       background AI pipeline                      │
│                    6. Returns the tracking number to Rajesh       │
│                                                                  │
│  What goes out:  Rajesh sees "VQ-2026-0108" on his screen.       │
│                  He's done. He can close his browser now.         │
│                                                                  │
│  ════════════════════════════════════════════════════════         │
│  ★ Rajesh waited only ~400 milliseconds (less than half          │
│    a second). Everything below happens automatically             │
│    in the background — Rajesh does NOT wait for it.              │
│  ════════════════════════════════════════════════════════         │
│                                                                  │
│  Time: About half a second                                       │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
         ═══════════════════════════════════════════
           EVERYTHING BELOW RUNS AUTOMATICALLY
           IN THE BACKGROUND (Rajesh doesn't wait)
         ═══════════════════════════════════════════
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 7: SYSTEM LOADS CONTEXT ABOUT THE VENDOR                   │
│                                                                  │
│  What comes in:  The query from the queue.                       │
│                                                                  │
│  What happens:   Before the AI reads the query, the system       │
│                  gathers background information:                  │
│                                                                  │
│                  "Who is this vendor?"                            │
│                    -> Checks Salesforce CRM: TechNova Solutions,  │
│                       Silver tier, has a history of asking about  │
│                       late payments                               │
│                                                                  │
│                  "Have they contacted us before?"                 │
│                    -> Finds 3 prior queries in 90 days            │
│                       (all payment/invoice related, avg 4.4h      │
│                       resolution)                                 │
│                                                                  │
│  Why this matters: This context helps the AI give a more         │
│  personalized and accurate response. The AI knows Rajesh         │
│  has asked about payments before — this is a pattern.            │
│                                                                  │
│  What goes out:  Full context package ready for AI analysis.     │
│                                                                  │
│  Time: Less than 1 second                                        │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 8: AI READS AND UNDERSTANDS THE QUERY                      │
│                                                                  │
│  What comes in:  Rajesh's query + vendor context + history.      │
│                                                                  │
│  What happens:   The AI (powered by Amazon Bedrock / Claude)     │
│                  reads the entire query and figures out:          │
│                                                                  │
│                  "What does Rajesh want?"                         │
│                    -> PAYMENT_QUERY (he's asking where his        │
│                       money is, not disputing the amount)         │
│                                                                  │
│                  "How urgent is this?"                            │
│                    -> HIGH (invoice is 16 days overdue)           │
│                                                                  │
│                  "What tone is Rajesh using?"                     │
│                    -> POLITE but CONCERNED                        │
│                                                                  │
│                  "How confident is the AI?"                       │
│                    -> 96% confident (very clear query)            │
│                                                                  │
│  Key decision:   96% confidence is above the 85% threshold.      │
│                  This means the query can be handled              │
│                  automatically — no human needs to review it.     │
│                                                                  │
│                  (If confidence was below 85%, the system would   │
│                  pause and send it to a human reviewer.)          │
│                                                                  │
│  What goes out:  Classification: PAYMENT_QUERY, HIGH urgency,    │
│                  96% confidence → proceed with full automation.   │
│                                                                  │
│  Time: About 3 seconds | Cost: ~1.2 cents                        │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 9: ROUTING + KNOWLEDGE SEARCH (happen at the same time)    │
│                                                                  │
│  What comes in:  AI's analysis result.                           │
│                                                                  │
│  What happens:   Two things happen in parallel:                  │
│                                                                  │
│    ROUTING:                                                      │
│      The system decides:                                         │
│        - Which team handles this? → Finance Team                 │
│          (payment queries always go to Finance)                   │
│        - What's the SLA? → 4 hours                               │
│          (based on High priority + Silver tier vendor)            │
│        - Can we automate? → YES                                  │
│          (high confidence, clear intent, no blockers)            │
│                                                                  │
│    KNOWLEDGE SEARCH:                                             │
│      The system searches its knowledge base and finds:           │
│        - "Invoice Payment Status Check Procedure" (96% match)    │
│        - "Overdue Invoice Escalation Policy" (89% match)         │
│        - "AP Payment Timeline by Vendor Tier" (82% match)        │
│      These articles give the AI the facts it needs to            │
│      write an accurate response.                                 │
│                                                                  │
│  What goes out:  Routing decision + 3 relevant KB articles.      │
│                                                                  │
│  Time: Under 0.2 seconds (very fast — no AI call needed)         │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 10: AI WRITES THE RESPONSE                                 │
│                                                                  │
│  What comes in:  Query + analysis + 3 knowledge articles +       │
│                  vendor profile + SLA info.                       │
│                                                                  │
│  What happens:   The AI writes a professional response email     │
│                  using all the context it has gathered:           │
│                                                                  │
│                  "Dear Rajesh,                                    │
│                   Thank you for reaching out regarding            │
│                   Invoice #INV-2026-0451...                       │
│                                                                  │
│                   The invoice passed three-way match on           │
│                   February 28. Payment is approved and            │
│                   scheduled for April 5. Expected credit          │
│                   by April 10.                                    │
│                                                                  │
│                   If you need expedited payment, let us know."    │
│                                                                  │
│  Notice:   The AI gives a CONCRETE answer (April 5 payment,      │
│            April 10 credit) and anticipates Rajesh's next         │
│            question by offering expedited processing.             │
│                                                                  │
│  What goes out:  Complete draft email ready for quality check.    │
│                                                                  │
│  Time: About 4 seconds | Cost: ~2.1 cents                        │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 11: QUALITY CHECK (Safety Gate)                            │
│                                                                  │
│  What comes in:  The AI's draft response.                        │
│                                                                  │
│  What happens:   Before anything is sent to Rajesh, the          │
│                  system runs 7 safety checks:                    │
│                                                                  │
│                  ✓ Ticket number is correctly formatted           │
│                  ✓ SLA wording matches company policy             │
│                  ✓ All required sections are present              │
│                    (greeting, summary, next steps, signature)    │
│                  ✓ No restricted or inappropriate terms           │
│                  ✓ Response is the right length                   │
│                  ✓ Knowledge sources are properly cited           │
│                  ✓ No personal data (PII) leaked in response     │
│                    (Rajesh included his phone number, but the    │
│                     AI correctly DID NOT include it in the       │
│                     outbound email)                               │
│                                                                  │
│  Result: ALL 7 CHECKS PASSED — safe to send.                    │
│                                                                  │
│  If any check failed: The system would either re-draft the       │
│  response (up to 2 times) or send it to a human reviewer.        │
│                                                                  │
│  What goes out:  Green light — email is approved for delivery.   │
│                                                                  │
│  Time: Under 0.2 seconds | Cost: $0.00                           │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 12: TICKET CREATED + EMAIL SENT TO RAJESH                  │
│                                                                  │
│  What comes in:  Approved draft email.                           │
│                                                                  │
│  What happens:   Two important things happen here:               │
│                                                                  │
│    1. TICKET CREATED IN SERVICENOW                               │
│       A formal support ticket (INC0019847) is created and        │
│       assigned to the Finance Team. This means:                  │
│         - The query is officially tracked                         │
│         - A human team is responsible if follow-up is needed     │
│         - SLA clock is running                                   │
│                                                                  │
│    2. EMAIL SENT TO RAJESH                                       │
│       The response email lands in Rajesh's inbox:                │
│         From: vendor-support@hexaware.com                        │
│         To: rajesh.mehta@technovasolutions.in                    │
│         Subject: RE: Payment Status Inquiry [INC0019847]         │
│         Body: Full resolution with payment timeline              │
│                                                                  │
│  What goes out:  Rajesh receives his answer. Ticket is live.     │
│                  Query status: RESPONDED.                         │
│                                                                  │
│  Time: About 2.5 seconds                                         │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 13: SLA MONITORING (runs quietly in the background)        │
│                                                                  │
│  What comes in:  Ticket creation event.                          │
│                                                                  │
│  What happens:   A timer starts watching the 4-hour SLA          │
│                  deadline. If the query had NOT been resolved     │
│                  automatically, the system would:                 │
│                                                                  │
│                  At 70% (2h 48m): Warn the assigned person       │
│                  At 85% (3h 24m): Escalate to their manager      │
│                  At 95% (3h 48m): Escalate to senior leadership  │
│                                                                  │
│  For Rajesh:     The query was resolved in ~11 seconds, so       │
│                  none of these escalations were needed.           │
│                  SLA result: NOT BREACHED (well within 4 hours)   │
│                                                                  │
│  What goes out:  SLA metrics recorded for reporting.             │
│                                                                  │
│  Time: Runs in background for hours (if needed)                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   RESULT                                                         ║
║                                                                  ║
║   Rajesh opens "My Queries" about 30 seconds after submitting.  ║
║   Everything is already there:                                   ║
║     - Full AI-generated resolution                               ║
║     - Ticket number: INC0019847                                  ║
║     - Payment scheduled: April 5                                 ║
║     - Expected credit: April 10                                  ║
║     - Email already in his inbox                                 ║
║                                                                  ║
║   He did NOT have to wait for a human to read his email,         ║
║   file a ticket, look up his invoice, and write a response.      ║
║   The AI system did it all in 11 seconds for 3 cents.            ║
║                                                                  ║
║   ┌─────────────────────────────────────────────────────┐       ║
║   │  SUMMARY                                            │       ║
║   │                                                     │       ║
║   │  Rajesh waited:        ~0.4 seconds (got query ID)  │       ║
║   │  Full pipeline:        ~11 seconds (background)      │       ║
║   │  Total cost:           ~3.3 cents ($0.033)           │       ║
║   │  AI calls:             2 (analysis + response)       │       ║
║   │  Human involvement:    ZERO (high confidence)        │       ║
║   │  SLA breached:         No (resolved in seconds)      │       ║
║   │  Time to inbox:        Under 1 minute total          │       ║
║   └─────────────────────────────────────────────────────┘       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

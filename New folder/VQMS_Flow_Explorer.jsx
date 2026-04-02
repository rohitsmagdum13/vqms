import { useState, useEffect, useRef } from "react";

const STEPS = [
  {
    id: 1,
    title: "Login",
    subtitle: "Vendor authenticates via Cognito or Company SSO",
    time: "< 800ms",
    cost: "$0.00",
    llm: false,
    ascii: `WHAT HAPPENS WHEN YOU LOG IN
─────────────────────────────

You have two ways to sign in:

  WAY 1: Email + Password
    You type your email and password.
    VQMS checks them.
    If correct, you are in.

  WAY 2: Company SSO
    You click "Sign in with Company SSO."
    VQMS sends you to your company's
      own login page (like Okta or
      your company portal).
    You log in there with your company
      credentials.
    Your company tells VQMS
      "yes, this person is real."
    VQMS lets you in.

  Both ways end the same:
    VQMS creates a secure pass
      (session token).
    This pass remembers who you are,
      which company you belong to,
      and what you are allowed to see.
    The pass expires after 8 hours.
    You only see your own company's
      queries -- never another
      vendor's data.

─────────────────────────────────────────
DETAILED FLOW (for developers)
─────────────────────────────────────────

PATH 1: EMAIL + PASSWORD
========================

BROWSER                    BACKEND                  STORAGE
───────                    ───────                  ───────

POST /auth/login ────────► Auth Service (Cognito)
{                           │
  email: "priya.sharma      ├── Check email & password
         @infosys.com"      │   against user list:
  password: "••••••••"      │   vqms-agent-portal-users
  role: "vendor"            │
}                           ├── Create a secure pass:
                            │   {
                            │     who: "Priya Sharma",
                            │     role: "VENDOR",
                            │     company: "INF"
                            │              (Infosys),
                            │     can_access: [
                            │       "own queries",
                            │       "knowledge base",
                            │       "preferences"
                            │     ],
                            │     expires: "in 8 hours"
                            │   }
                            │
                            └── Save session ──────► Redis
                                remember this user    vqms:session:
                                for 8 hours           <token>
                            │                         TTL = 8h
◄───────────────────────────┘
  Here is your pass.
  You are logged in as VENDOR.
  You can only see Infosys data.


PATH 2: COMPANY SSO
========================

BROWSER                    BACKEND                  COMPANY
───────                    ───────                  ───────

Click "Company SSO" ─────► VQMS says:
                            "I don't check your
                             password. Your company
                             will do that."
                            │
                            └── Redirect ──────────► Company
                                browser goes to       login page
                                your company's        (Okta /
                                own login page        Azure AD /
                                                      company
                                                      portal)

                                                     Vendor logs
                                                     in with
                                                     company
                                                     credentials
                                                        │
                            Company says: ◄─────────────┘
                            "Yes, this is Priya.
                             She works at Infosys.
                             Let her in."
                            │
                            ├── Create same secure
                            │   pass as Path 1
                            │   (same who, role,
                            │    company, access,
                            │    8-hour expiry)
                            │
                            └── Save session ──────► Redis
                                (same as Path 1)      vqms:session:
                                                      <token>
                            │
◄───────────────────────────┘
  Here is your pass.
  You are logged in as VENDOR.
  Same result as email login.


BOTH PATHS PRODUCE THE SAME RESULT
───────────────────────────────────
  Same secure pass.
  Same permissions.
  Same 8-hour session.
  The only difference is who checks
  your password -- VQMS or your company.`,
    ui: "login"
  },
  {
    id: 2,
    title: "Portal Loads",
    subtitle: "Dashboard loads with KPIs, recent queries, and quick actions",
    time: "< 400ms",
    cost: "$0.00",
    llm: false,
    ascii: `WHAT HAPPENS WHEN YOUR PORTAL LOADS
────────────────────────────────────

When you open your dashboard, VQMS
fetches your data in two quick steps:

  STEP A: Check the fast cache
    VQMS first checks a quick-access
    cache (like a sticky note on the
    fridge) to see if your numbers
    are already calculated.

    If the sticky note is fresh
    (less than 5 minutes old):
      Use it. Done. Super fast.

    If the sticky note is old
    or missing:
      Go to Step B.

  STEP B: Calculate from the database
    VQMS counts your queries directly
    from the main database:
      "How many are open?"
      "How many got resolved this month?"
      "What is the average response time?"
    Then writes a fresh sticky note
    (cache) so next time is fast.

  WHAT YOU SEE:
    Your dashboard shows:
      - 3 KPI cards (open, resolved, avg time)
      - 4 quick action tiles
      - Your 4 most recent queries
    All scoped to YOUR company only.
    You never see another vendor's data.

  HOW FAST:
    Cache hit:  under 0.4 seconds
    Cache miss: under 1.2 seconds

─────────────────────────────────────────
DETAILED FLOW (for developers)
─────────────────────────────────────────

BROWSER                    BACKEND                  STORAGE
───────                    ───────                  ───────

GET /vendor/queries ─────► API Gateway
?vendor_id=INF              │
&limit=10                   ├── Check your secure
&sort=desc                  │   pass (session token)
                            │   Pass valid? YES
                            │
                            ├── Who is this?
                            │   company = "INF"
                            │   (Infosys)
                            │
                            ├── Check the cache ───► Redis
                            │   "Do I already have    vqms:vendor:
                            │    Infosys numbers?"    INF:kpis
                            │                         TTL = 5 min
                            │
                            │   ┌─────────────────────────┐
                            │   │ CACHE HIT (< 5 min old) │
                            │   │                         │
                            │   │ Use cached numbers:     │
                            │   │   open: 6               │
                            │   │   resolved: 14          │
                            │   │   avg response: 2.4h    │
                            │   │                         │
                            │   │ Skip database.          │
                            │   │ Fast path: < 400ms      │
                            │   └─────────────────────────┘
                            │
                            │   ┌─────────────────────────┐
                            │   │ CACHE MISS (expired)    │
                            │   │                         │
                            │   │ Count from ──────────► PostgreSQL
                            │   │ database:               workflow.
                            │   │  "How many open?"       case_execution
                            │   │  "How many resolved?"
                            │   │  "What is avg time?"
                            │   │                         │
                            │   │ Save fresh cache: ──► Redis
                            │   │  vqms:vendor:INF:kpis   (new sticky
                            │   │  TTL = 5 min             note, 5 min)
                            │   │                         │
                            │   │ Slow path: < 1200ms     │
                            │   └─────────────────────────┘
                            │
                            ├── Fetch recent queries ─► PostgreSQL
                            │   "Give me the 10 most     workflow.
                            │    recent Infosys queries   case_execution
                            │    newest first"
                            │
◄───────────────────────────┘
{
  Your dashboard data:
    queries: [ 6 active items ],
    kpis: {
      open: 6,
      resolved: 14,
      avg_response: "2.4h"
    },
    recent: [ top 4 to show ]
}

WHY THE CACHE?
──────────────
  Counting queries from the database
  every time you refresh the page
  would be slow. So VQMS keeps a
  "sticky note" (cache) with your
  numbers for 5 minutes.

  First visit of the day: ~1.2 seconds
    (database count + save cache)
  Every refresh after that: ~0.4 seconds
    (read from cache, skip database)

  The cache auto-expires every 5 minutes
  so your numbers stay fresh.`,
    ui: "dashboard"
  },
  {
    id: 3,
    title: "Wizard: Type",
    subtitle: "Vendor picks query type -- saved in browser, not sent to server yet",
    time: "0ms",
    cost: "$0.00",
    llm: false,
    ascii: `WHAT HAPPENS WHEN YOU PICK A QUERY TYPE
────────────────────────────────────────

Short answer: nothing goes to the server.
This step happens entirely in your browser.

You see 6 cards. You pick one.
Your choice is saved locally on your
screen (not sent anywhere yet).

  📋 Contract Dispute
  💳 Invoice Issue
  🚚 Delivery Delay
  🔧 Tech Support
  ⏱️ SLA Clarification
  💬 Other

WHY DOES THIS MATTER?

Your selection gives the AI a head start.
When your query reaches the AI agent
(Step 8: QueryAnalysisAgent), it already
knows "the vendor thinks this is a
contract issue."

But the AI does not blindly trust your
pick. It reads your full description and
makes its own classification. So even if
you pick "Invoice Issue" but describe a
delivery problem, the AI will catch that
and route it correctly.

Think of it like a doctor's office:
  The receptionist asks "what brings
  you in today?" (that is this step).
  The doctor still does their own
  examination (that is the AI agent).

Your pick helps. It does not lock
anything in.

─────────────────────────────────────────
DETAILED FLOW (for developers)
─────────────────────────────────────────

NO BACKEND CALL AT THIS STEP
All data stays in the browser until
the vendor clicks "Submit" on Step 5.

WHAT GETS SAVED IN THE BROWSER:
───────────────────────────────

  When vendor clicks a card:
    WD.type = "contract"

  This is a JavaScript variable.
  It lives in browser memory only.
  Nothing is sent to the server.
  Nothing is written to Redis,
  PostgreSQL, or S3.

  Cost:  $0.00
  Time:  instant (< 1ms)
  LLM:   not involved

HOW THIS CONNECTS TO LATER STEPS:
──────────────────────────────────

  Step 5 (Review):
    Shows the selected type in the
    summary card so vendor can confirm.

  Step 6 (Submit):
    WD.type is included in the
    POST /queries payload sent
    to the backend.

  Step 8 (QueryAnalysisAgent):
    The AI receives type = "contract"
    as a HINT, not a final answer.
    The AI still reads the full
    description and classifies
    independently.

WHAT THE AI DOES WITH YOUR PICK:
────────────────────────────────

  Your pick        AI might classify as
  ─────────        ─────────────────────
  Contract     ->  CONTRACT_AMENDMENT
                   CONTRACT_DISPUTE

  Invoice      ->  PAYMENT_QUERY
                   INVOICE_DISPUTE

  Delivery     ->  DELIVERY_DELAY
                   SHIPMENT_ISSUE

  Tech Support ->  TECHNICAL_SUPPORT
                   API_ISSUE

  SLA Clarify  ->  SLA_CLARIFICATION

  Other        ->  GENERAL_INQUIRY

  The AI uses your pick + your
  description + your vendor history
  to make the final call.
  Your pick is a signal, not a
  binding decision.`,
    ui: "wizard1"
  },
  {
    id: 4,
    title: "Wizard: Details",
    subtitle: "Fill in subject, description, priority, and reference",
    time: "0ms",
    cost: "$0.00",
    llm: false,
    ascii: `WHAT HAPPENS WHEN YOU FILL IN THE DETAILS
──────────────────────────────────────────

Still nothing goes to the server.
You are filling out a form in your
browser. The data is saved locally
as you type.

WHAT YOU ARE FILLING IN:

  Subject:     A short headline for
               your issue.

  Description: The full explanation.
               THIS IS THE MOST
               IMPORTANT FIELD.
               The AI reads this word
               by word to understand
               what you need.

               Tip: include specific
               details like clause
               numbers, PO numbers,
               dates, and amounts.
               The more specific you
               are, the better the AI
               response.

  Priority:    How urgent is this?

               Critical = 2 hour response
               High     = 4 hour response
               Medium   = 8 hour response
               Low      = 24 hour response

               Pick honestly. The AI and
               your vendor tier together
               determine the final SLA.

  Reference:   Optional. A PO number,
               contract ID, or ticket
               number that helps us find
               your records in Salesforce.

WHEN DOES THIS DATA GO TO THE SERVER?
  Not yet. Only when you click
  "Submit Query" on the Review step.

─────────────────────────────────────────
DETAILED FLOW (for developers)
─────────────────────────────────────────

NO BACKEND CALL AT THIS STEP
Everything stays in the browser.

WHAT IS BUILDING UP IN BROWSER MEMORY:
──────────────────────────────────────

  As the vendor types, the JS state
  accumulates:

  WD = {
    type:     "contract"
              (set in Step 3)

    subject:  "Contract Amendment
               -- Clause 7.3"
              (set now)

    desc:     "We need urgent
               clarification on
               the amendment to
               Clause 7.3 regarding
               penalty calculations."
              (set now, max 1000 chars)

    priority: "High"
              (set now)

    ref:      "PO-2025-001"
              (set now, optional)
  }

  Cost:  $0.00
  Time:  instant
  LLM:   not involved

WHERE EACH FIELD GOES LATER:
────────────────────────────

  subject + desc
    -> Step 8: QueryAnalysisAgent
       reads these to classify intent,
       extract entities, detect urgency.
       This is the PRIMARY input to the
       AI. Everything else is supporting
       context.

  priority
    -> Step 9: RoutingService uses this
       to set the SLA deadline.

       ┌──────────────────────────────┐
       │  Priority-to-SLA mapping:    │
       │                              │
       │  Critical ─► 2 hours        │
       │  High     ─► 4 hours ◄ this │
       │  Medium   ─► 8 hours        │
       │  Low      ─► 24 hours       │
       │                              │
       │  Note: RoutingService can    │
       │  override based on vendor    │
       │  tier:                       │
       │  Gold + High = 4h (no change)│
       │  Platinum + Med = 4h (faster)│
       └──────────────────────────────┘

  ref (PO-2025-001)
    -> Step 9: RoutingService checks
       Salesforce for matching records
       and whether a ticket already
       exists for this reference.
       If yes: append to existing ticket.
       If no: create new ticket.

  type ("contract")
    -> Step 8: QueryAnalysisAgent uses
       this as a classification hint
       (but still does its own analysis).`,
    ui: "wizard2"
  },
  {
    id: 5,
    title: "Wizard: Review",
    subtitle: "Confirm everything before it goes to the server",
    time: "0ms",
    cost: "$0.00",
    llm: false,
    ascii: `WHAT HAPPENS ON THE REVIEW SCREEN
──────────────────────────────────

This is your last look before
submitting. Nothing has been sent
to the server yet.

WHAT YOU SEE:
  A summary of everything you entered:
    Query type, subject, description,
    priority, reference, company name.

  Plus two things VQMS adds:
    - "Assigned to: Auto (QueryAnalysisAgent)"
      This means the AI will handle
      your query first. No human sees
      it unless the AI is unsure.

    - "Expected SLA: 4 hours"
      This is the deadline VQMS sets
      based on your priority.
      (High priority = 4 hour response)

WHAT HAPPENS WHEN YOU CLICK SUBMIT:
  Your browser sends all the data to
  the VQMS server in one go.
  You get a query ID back in about
  half a second.
  The AI pipeline starts working in
  the background.
  You do not have to wait for it.

WHAT IF SOMETHING IS WRONG?
  Click "Back" to change any field.
  Nothing is locked until you
  click "Submit Query."

─────────────────────────────────────────
DETAILED FLOW (for developers)
─────────────────────────────────────────

STILL NO BACKEND CALL
Review is pure client-side rendering.

WHAT THE BROWSER DISPLAYS:
──────────────────────────

  Renders the WD object as a summary:

  ┌──────────────────────────────────┐
  │  Query Type  │ Contract Dispute  │
  │  Subject     │ Contract Amend.   │
  │              │ -- Clause 7.3     │
  │  Description │ We need urgent    │
  │              │ clarification...  │
  │  Priority    │ High              │
  │  Reference   │ PO-2025-001      │
  │  Assigned to │ Auto              │
  │              │ (QueryAnalysis    │
  │              │  Agent)           │
  │  Company     │ Infosys Ltd      │
  └──────────────────────────────────┘

  SLA Estimate: 4 hours
  Based on: priority = High (default)

WHAT HAPPENS ON "SUBMIT QUERY" CLICK:
─────────────────────────────────────

  Browser builds the POST payload:

  POST /queries
  Authorization: Bearer <session-token>
  {
    type:        WD.type,
    subject:     WD.subject,
    description: WD.desc,
    priority:    WD.priority,
    reference:   WD.ref,
    vendor_id:   <from session token>
  }

  NOTE: vendor_id is NOT in the form.
  It comes from the secure pass
  that was created at login.
  The vendor cannot change or fake it.
  This is how VQMS ensures you only
  see your own company's data.

  After this click, control moves
  to Step 6 (Submit).`,
    ui: "wizard3"
  },
  {
    id: 6,
    title: "Submit",
    subtitle: "Query saved, ID assigned, AI pipeline starts in background",
    time: "< 500ms",
    cost: "$0.00",
    llm: false,
    ascii: `WHAT HAPPENS WHEN YOU HIT SUBMIT
─────────────────────────────────

This is the moment your query
leaves your browser and enters
the VQMS system.

HERE IS WHAT HAPPENS (in order):

  1. VQMS checks your data is valid
     (all required fields filled in,
      nothing suspicious)

  2. VQMS gives you a query ID
     Example: VQ-2025-0042
     This is your tracking number.

  3. VQMS checks: "have I seen this
     exact query before?"
     (prevents duplicate submissions
      if you accidentally click twice)

  4. Your query is saved to the
     database. Status: OPEN.

  5. VQMS announces: "new query
     arrived" so background services
     know to start working.

  6. Your query is placed in a queue
     for the AI pipeline to pick up.

  7. You get your query ID back.
     The page shows a success screen.

HOW LONG: about half a second.

WHAT HAPPENS NEXT:
  The AI pipeline starts in the
  background. You do not wait for it.
  By the time you click "Track This
  Query," the AI is already working.

─────────────────────────────────────────
DETAILED FLOW (for developers)
─────────────────────────────────────────

BROWSER                    BACKEND                  STORAGE
───────                    ───────                  ───────

POST /queries ───────────► API Gateway
{                           │
  type: "contract",         ├── 1. Check the data
  subject: "Contract             is valid (Pydantic
    Amendment --                 model validation)
    Clause 7.3",            │
  description: "We need     ├── 2. Create query ID:
    urgent...",                  VQ-2025-0042
  priority: "High",         │
  reference: "PO-2025-001", ├── 3. Create a unique
  vendor_id: "INF"               tracking code
}                                (correlation_id)
                            │
                            ├── 4. Duplicate check ──► Redis
                            │   "Have I seen this      vqms:
                            │    exact query before?"   idempotency:
                            │   NOT FOUND = new query   <hash>
                            │   FOUND = skip (duplicate)
                            │
                            ├── 5. Save query ────────► PostgreSQL
                            │   to database              workflow.
                            │   status = 'OPEN'          case_
                            │                            execution
                            │
                            ├── 6. Set duplicate ─────► Redis
                            │   guard for 7 days         vqms:
                            │   (if you submit again,    idempotency:
                            │    it catches it)           <hash>
                            │                            TTL = 7 days
                            │
                            ├── 7. Announce: ─────────► EventBridge
                            │   "New query arrived"      QueryReceived
                            │   (background services
                            │    start listening)
                            │
                            ├── 8. Place in queue ───► SQS
                            │   for AI pipeline          vqms-query-
                            │   to pick up               intake-queue
                            │
◄───────────────────────────┘
{
  query_id: "VQ-2025-0042",
  status: "Open",
  sla_deadline:
    "2026-04-01T12:14:00Z"
}

Time: < 500ms (half a second)
The vendor gets this response
and sees the success screen.

════════════════════════════════
ASYNC BOUNDARY
════════════════════════════════
Everything after this point runs
in the background.

The AI pipeline (Steps 7-13)
starts processing. The vendor
does not wait.

By the time the vendor clicks
"Track This Query," the AI is
already analyzing their issue.`,
    ui: "submitting"
  },
  {
    id: 7,
    title: "Success",
    subtitle: "Query ID assigned, pipeline starts async",
    time: "~600ms (async)",
    cost: "$0.00",
    llm: false,
    ascii: `SQS MESSAGE CONSUMED BY LANGGRAPH
──────────────────────────────────

LangGraph Orchestrator initializes:

1. PostgreSQL UPDATE
   workflow.case_execution
   SET status = 'ANALYZING'

2. Redis SET
   vqms:workflow:<exec-id>
   { status:"ANALYZING",
     query_id:"VQ-2025-0042",
     vendor_id:"INF" }
   TTL = 24 hours

3. Load vendor context:

   a) Redis GET vqms:vendor:INF
      CACHE HIT (TTL 1h)
      {
        vendor_id: "INF",
        name: "Infosys Ltd",
        tier: "GOLD",
        risk_flags: [],
        primary_contact: "Priya Sharma",
        account_manager: "Rohit Kumar"
      }

   b) PostgreSQL SELECT
      memory.vendor_profile_cache
      WHERE vendor_id = 'INF'

   c) PostgreSQL SELECT
      memory.episodic_memory
      WHERE vendor_id = 'INF'
      ORDER BY created_at DESC
      LIMIT 5
      -> 2 prior resolved queries`,
    ui: "success"
  },
  {
    id: 8,
    title: "QueryAnalysisAgent",
    subtitle: "LLM Call #1 -- intent, entities, confidence",
    time: "2-4 seconds",
    cost: "~$0.012",
    llm: true,
    ascii: `LANGGRAPH -> ANALYSIS NODE
──────────────────────────

Agent: QueryAnalysisAgent
Model: Bedrock Claude Sonnet 3.5
Temp:  0.1 (low for classification)
Max:   500 tokens

PROMPT (from S3 template v2):
┌─────────────────────────────────┐
│ System: "You are a query        │
│ analysis agent. Return JSON:    │
│ intent_classification,          │
│ extracted_entities,             │
│ urgency_level, sentiment,       │
│ confidence_score,               │
│ multi_issue_detected,           │
│ suggested_category"             │
│                                 │
│ User:                           │
│ "Type: contract                 │
│  Subject: Contract Amendment    │
│  -- Clause 7.3                  │
│  Description: We need urgent    │
│  clarification on the amendment │
│  to Clause 7.3 regarding       │
│  penalty calculations.          │
│  Reference: PO-2025-001        │
│  Vendor: Infosys Ltd (Gold)     │
│  History: 2 resolved queries"   │
└─────────────────────────────────┘

RESPONSE (parsed to Pydantic):
{
  intent: "CONTRACT_AMENDMENT",
  entities: [
    "Clause 7.3",
    "penalty calculations",
    "PO-2025-001"
  ],
  urgency: "HIGH",
  sentiment: "URGENT",
  confidence: 0.92,
  multi_issue: false,
  suggested_category: "contracts"
}

WRITES:
  S3: prompts/<exec>/analysis.json
  PG: case_execution.analysis_result
  Redis: workflow state -> ANALYSIS_COMPLETE
  PG: audit.action_log

BRANCH: 0.92 >= 0.85 -> FULL_AUTO`,
    ui: "analyzing"
  },
  {
    id: 9,
    title: "Routing + KB Search",
    subtitle: "Parallel: rules engine + pgvector (no LLM)",
    time: "< 200ms",
    cost: "~$0.0001",
    llm: false,
    ascii: `═══ PARALLEL EXECUTION ══════════

STEP 9: RoutingService (no LLM)
────────────────────────────────
Input: AnalysisResult +
       VendorProfile +
       TicketCorrelation

Decision:
  confidence >= 0.85? YES (0.92)
  urgency == CRITICAL? NO (HIGH)
  tier == PLATINUM? NO (GOLD)
  existing ticket? NO

  Path: FULL_AUTOMATION
  Group: "Procurement Team"
  SLA: 4 hours (no override)

  PG INSERT routing_decision
  Cost: $0.00 | Time: < 50ms

════════════════════════════════

STEP 10: KBSearchService
────────────────────────────────
1. Embed query text:
   Bedrock Titan v2
   -> vector(1536)

2. pgvector cosine similarity:
   SELECT *, 1-(embedding<=>$1)
   AS similarity
   FROM memory.embedding_index
   WHERE category = 'contracts'
   ORDER BY distance
   LIMIT 5

3. Results:
   #847 "Contract Amendment
         Procedure v3.2"     94%
   #412 "Penalty Calculation
         Policy"             81%
   #291 "Amendment Precedent
         Log"                72%

  Cost: ~$0.0001 | Time: < 200ms`,
    ui: "routing"
  },
  {
    id: 10,
    title: "ResolutionAgent",
    subtitle: "LLM Call #2 -- draft response with KB context",
    time: "3-6 seconds",
    cost: "~$0.021",
    llm: true,
    ascii: `LANGGRAPH -> RESOLUTION NODE
────────────────────────────

Agent: ResolutionAgent
Model: Bedrock Claude Sonnet 3.5
Temp:  0.3
Max:   1000 tokens

PROMPT CONTEXT:
  Query: "Contract Amendment
    -- Clause 7.3"
  Analysis: CONTRACT_AMENDMENT,
    HIGH, URGENT, 0.92
  KB #847 (full text, 94%)
  KB #412 (full text, 81%)
  KB #291 (full text, 72%)
  Vendor: Infosys Ltd, Gold
  SLA: 4 hours

RESPONSE (DraftResponse):
{
  subject: "RE: Contract
    Amendment -- Clause 7.3",

  body: "Based on KB article
    #847 (94% match), Clause
    7.3 refers to the standard
    penalty schedule (Q1 2024).
    Amendment has precedent in
    14 similar cases -- all
    resolved with a 2.5%/month
    penalty cap.

    Recommended: Accept with
    rider referencing Exhibit C,
    Section 2.",

  confidence: 0.94,
  sources: ["KB#847","KB#412"],
  sla_statement: "Response
    within 4 hours per
    Gold tier SLA"
}

WRITES:
  PG: case_execution.response_draft
  Redis: workflow state updated
  S3: prompt snapshot for audit
  EventBridge: DraftPrepared`,
    ui: "drafting"
  },
  {
    id: 11,
    title: "QualityGate",
    subtitle: "Validate draft (deterministic + conditional LLM)",
    time: "< 200ms",
    cost: "$0.00",
    llm: false,
    ascii: `QUALITY GATE VALIDATION
───────────────────────

Agent: QualityGateAgent
LLM: SKIPPED (deterministic pass)

PHASE 1: DETERMINISTIC CHECKS
  [PASS] Ticket # format
         INC\\d{7} regex
  [PASS] SLA wording
         "4 hours" matches
         Gold/High policy
  [PASS] Required sections
         greeting: yes
         issue summary: yes
         next steps: yes
         signature: yes
  [PASS] Restricted terms
         0 matches on blocklist
  [PASS] Response length
         147 words (range 50-500)
  [PASS] Source citations
         2 KB articles (min 1)

PHASE 2: CONDITIONAL
  Priority HIGH? YES
  -> Comprehend PII scan
  -> DetectPiiEntities on body
  -> Result: NO PII detected

  Tone check via Bedrock?
  -> No near-miss restricted terms
  -> No NEGATIVE sentiment in draft
  -> SKIP Bedrock call (saves $0.012)

RESULT: ██████████ PASS ████████████

WRITES:
  S3: audit/<ticket>/validation.json
  PG: audit.validation_results
  EventBridge: ValidationPassed

IF FAIL: re-draft (max 2x)
         then human review queue`,
    ui: "validating"
  },
  {
    id: 12,
    title: "Ticket + Deliver",
    subtitle: "ServiceNow ticket + email to vendor",
    time: "~2 seconds",
    cost: "$0.00",
    llm: false,
    ascii: `TICKET CREATION + DELIVERY
──────────────────────────

STEP 13A: ServiceNow Ticket
──────────────────────────
1. Check existing ticket:
   SELECT FROM workflow.ticket_link
   WHERE correlation_id = '<uuid>'
   -> NONE FOUND -> create new

2. POST /api/now/table/incident
   {
     category: "Contract",
     subcategory: "Amendment",
     urgency: 2,
     impact: 2,
     assignment_group:
       "Procurement Team",
     short_description:
       "Contract Amendment
        -- Clause 7.3",
     caller_id: <sf_contact>,
     correlation_id: "<uuid>"
   }

3. Response:
   { sys_id: "abc123",
     number: "INC0012345" }

4. PG INSERT ticket_link
5. Redis SET ticket:abc123 1h
6. EventBridge: TicketCreated

STEP 13B: Email Delivery
──────────────────────────
1. Merge draft + INC0012345
2. PG UPDATE status='RESPONDED'
3. Redis -> COMPLETE
4. MS Graph sendMail to
   priya.sharma@infosys.com
5. Audit: EMAIL_SENT
6. EventBridge: QueryResolved`,
    ui: "delivered"
  },
  {
    id: 13,
    title: "SLA Monitor",
    subtitle: "Background timer at 70% / 85% / 95%",
    time: "Runs for hours",
    cost: "$0.00",
    llm: false,
    ascii: `SLA MONITORING (BACKGROUND)
───────────────────────────

Trigger: TicketCreated event
Engine: Step Functions state machine

SLA: Gold + High = 4 hours
Start: 08:14 | Deadline: 12:14

Redis SET vqms:sla:abc123
{
  start: "08:14",
  target_hours: 4,
  deadline: "12:14",
  elapsed_pct: 0,
  next_threshold: 70
}

TIMELINE:
─────────────────────────────────
08:14  Ticket created
       SLA monitor starts
       ▼
11:02  70% elapsed (2h 48m)
       Check: ticket resolved? NO
       EventBridge: SLAWarning70
       -> Notify assigned resolver
       ▼
11:38  85% elapsed (3h 24m)
       Check: ticket resolved? NO
       EventBridge: SLAEscalation85
       -> L1 manager via
          vqms-escalation-queue
       ▼
12:02  95% elapsed (3h 48m)
       Check: ticket resolved? NO
       EventBridge: SLAEscalation95
       -> L2 senior management
       ▼
12:14  100% DEADLINE
       SLA BREACHED
       reporting.sla_metrics:
       { breach: true,
         escalation_level: 2 }
─────────────────────────────────

If resolved before deadline:
  Stop monitor
  breach: false
  actual_hours: <time taken>`,
    ui: "sla"
  },
  {
    id: 14,
    title: "End-to-End Flow",
    subtitle: "Complete pipeline: login to resolution in one view",
    time: "~10s total",
    cost: "~$0.033",
    llm: false,
    wideAscii: true,
    ascii: `THE COMPLETE JOURNEY OF YOUR QUERY
═══════════════════════════════════

From login to resolution -- everything
that happens, and how long each part takes.

YOU (in your browser)              VQMS (in the background)
─────────────────────              ────────────────────────

 1. You log in                      Cognito checks your
    (< 1 second)                    password or SSO.
         │                          You get a secure pass.
         ▼
 2. Dashboard loads                 Numbers from cache or
    (< 0.4 seconds)                 database. You see your
         │                          KPIs and recent queries.
         ▼
 3. Pick query type                 Nothing happens here.
    (instant)                       Saved in your browser.
         │
         ▼
 4. Fill in details                 Nothing happens here.
    (your time)                     Subject, description,
         │                          priority, reference.
         ▼
 5. Review everything               Nothing happens here.
    (your time)                     Last chance to go back.
         │
         ▼
 6. Click SUBMIT                    ★ THIS IS WHERE IT
    (< 0.5 seconds)                   GETS REAL ★

    You get your query ID:          Query saved to database.
    VQ-2025-0042                    Placed in AI queue.
         │
         │  ════════════════════════════════════
         │  YOU CAN STOP HERE.
         │  Close the browser. Go get coffee.
         │  Everything below happens without you.
         │  ════════════════════════════════════
         │
         │                      7. Load your company info
         │                         from Salesforce cache.
         │                         (0.6 seconds)
         │                              │
         │                              ▼
         │                      8. AI reads your query 🤖
         │                         Figures out: contract
         │                         amendment, high urgency,
         │                         92% confident.
         │                         (2-4 seconds, ~1.2 cents)
         │                              │
         │                         ┌────┴────┐
         │                         ▼         ▼
         │                      9a. Route  9b. Search KB
         │                      Rules say:  Found 3 articles
         │                      Procurement #847 (94% match)
         │                      Team, 4h    #412 (81%)
         │                         │         │
         │                         └────┬────┘
         │                              ▼
         │                     10. AI writes response 🤖
         │                         Uses KB articles +
         │                         your company profile.
         │                         (3-6 seconds, ~2.1 cents)
         │                              │
         │                              ▼
         │                     11. Quality check
         │                         Ticket # correct? ✓
         │                         SLA wording? ✓
         │                         No PII leaked? ✓
         │                         (< 0.2 seconds)
         │                              │
         │                              ▼
         │                     12. Ticket created
         │                         INC0012345 in ServiceNow
         │                         Email sent to you
         │                         (~2 seconds)
         │                              │
         │                              ▼
         │                     13. SLA monitor starts
         │                         Watching: 70% warn
         │                                   85% escalate
         │                                   95% critical
         │
         ▼
  You open "My Queries"            Everything is done.
  and see the full resolution.     Total: ~10 seconds.
  Ticket: INC0012345               Cost: ~3.3 cents.


COST BREAKDOWN (like a receipt):
────────────────────────────────
  Step 8  QueryAnalysisAgent    ~1.2 cents
  Step 9b KB embedding          ~0.01 cents
  Step 10 ResolutionAgent       ~2.1 cents
  Everything else                0 cents
  ──────────────────────────────────────
  TOTAL                         ~3.3 cents

AT SCALE:
  10,000 queries/month:    ~$330
  50,000 queries/month:    ~$1,650
  100,000 queries/month:   ~$3,300


──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
FULL TECHNICAL SEQUENCE: ALL 13 STEPS, ALL SYSTEMS, ALL DATA WRITES
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

Vendor    Cognito   API     SQS    Orchestrator  QueryAnalysis  Routing  KBSearch  Resolution  QualGate  TicketOps  SLAMon   PG    Redis  S3    SForce  SNow   Graph
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │──login─►│        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │──JWT──►│       │         │              │           │         │          │          │          │         │       │──ses►│     │       │       │      │
  │◄─token──│────────│       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │─GET────►│────────│►      │         │              │           │         │          │          │          │         │       │◄kpi─►│     │       │       │      │
  │◄─dash───│────────│◄      │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │ [steps 3-5: browser only]│        │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │─POST───►│────────│►      │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │─wr───►│─────────│──────────────│───────────│─────────│──────────│──────────│──────────│─────────│───────│►     │     │       │       │      │
  │         │        │─id───►│─────────│──────────────│───────────│─────────│──────────│──────────│──────────│─────────│───────│──────│►    │       │       │      │
  │         │        │─sqs──►│►        │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │◄──VQ42──│────────│◄      │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │ ══ ASYNC BOUNDARY ═══════│═════════│══════════════│═══════════│═════════│══════════│══════════│══════════│═════════│═══════│══════│═════│═══════│═══════│══════│
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │─msg────►│              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │─wr exec─────►│───────────│─────────│──────────│──────────│──────────│─────────│───────│►     │     │       │       │      │
  │         │        │       │         │─cache────────│───────────│─────────│──────────│──────────│──────────│─────────│───────│──────│►    │       │       │      │
  │         │        │       │         │─vendor───────│───────────│─────────│──────────│──────────│──────────│─────────│───────│──────│─────│───────│►SF    │      │
  │         │        │       │         │◄─profile─────│───────────│─────────│──────────│──────────│──────────│─────────│───────│──────│►cch │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │─analyze─────►│►Bedrock   │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │ $0.012    │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │─snap─────►│─────────│──────────│──────────│──────────│─────────│───────│──────│─────│►      │       │      │
  │         │        │       │         │              │─result───►│─────────│──────────│──────────│──────────│─────────│───────│►     │     │       │       │      │
  │         │        │       │         │◄─analysis────│◄          │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │══PARALLEL════│═══════════│═════════│══════════│          │          │         │       │      │     │       │       │      │
  │         │        │       │         │─route───────►│───────────│►$0.00   │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │─search──────►│───────────│─────────│►$0.0001  │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │══MERGE═══════│═══════════│═════════│══════════│          │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │─draft───────►│───────────│─────────│──────────│►Bedrock  │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │ $0.021   │          │         │       │      │     │       │       │      │
  │         │        │       │         │◄─draft───────│───────────│─────────│──────────│◄         │          │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │─validate────►│───────────│─────────│──────────│──────────│►PII scan │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │─report──►│─────────│───────│──────│─────│►      │       │      │
  │         │        │       │         │◄─PASS────────│───────────│─────────│──────────│──────────│◄         │         │       │      │     │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
  │         │        │       │         │─ticket──────►│───────────│─────────│──────────│──────────│──────────│►        │       │      │     │       │───────│►SNow │
  │         │        │       │         │              │           │         │          │          │          │◄INC#────│───────│──────│─────│───────│───────│◄     │
  │         │        │       │         │              │           │         │          │          │          │─link───►│───────│►     │     │       │       │      │
  │         │        │       │         │─email───────►│───────────│─────────│──────────│──────────│──────────│─────────│───────│──────│─────│───────│───────│──────│►email
  │         │        │       │         │─SLA──────────│───────────│─────────│──────────│──────────│──────────│─────────│►timer │      │     │       │       │      │
  │         │        │       │         │─COMPLETE─────│───────────│─────────│──────────│──────────│──────────│─────────│───────│►     │►    │       │       │      │
  │         │        │       │         │              │           │         │          │          │          │         │       │      │     │       │       │      │
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

TIMING:  400ms│sync│ 600ms │ 3s      │ 200ms  │ 4s        │ 150ms    │ 2s        │ ongoing │       │      │     │       │       │
              │    │ init  │ LLM #1  │parallel│ LLM #2    │ validate │ tkt+email │ SLA     │       │      │     │       │       │
              │    │       │ $0.012  │$0.0001 │ $0.021    │ $0.00    │ $0.00     │ $0.00   │       │      │     │       │       │
              │    └───────┴─────────┴────────┴───────────┴──────────┴───────────┘         │       │      │     │       │       │
              │              TOTAL ASYNC: ~10 seconds                                      │       │      │     │       │       │
              │              TOTAL COST:  ~$0.033                                          │       │      │     │       │       │


──────────────────────────────────────────────────────────────────────────────
EVERY DATA WRITE ACROSS ALL 13 STEPS
──────────────────────────────────────────────────────────────────────────────

STEP   POSTGRESQL                  REDIS                     S3              EXTERNAL
────   ──────────                  ─────                     ──              ────────
 1     --                          session (8h)              --              Cognito
 2     (read)                      KPI cache (5m)            --              --
 3-5   --                          --                        --              --
 6     INSERT case_execution       idempotency (7d)          --              --
 7     UPDATE status=ANALYZING     workflow (24h)             --              Salesforce
                                   vendor cache (1h)
 8     UPDATE analysis_result      workflow=COMPLETE          prompt snap     Bedrock
       INSERT audit log
 9     INSERT routing_decision     --                        --              Titan embed
10     UPDATE response_draft       workflow updated           prompt snap     Bedrock
11     INSERT validation_results   --                        val report      Comprehend
12     INSERT ticket_link          ticket cache (1h)         --              ServiceNow
       UPDATE status=RESPONDED     workflow=COMPLETE                         MS Graph
       INSERT audit (EMAIL_SENT)
13     INSERT sla_metrics          SLA timer (persist)       --              --`,
    ui: "e2eOverview"
  },
  {
    id: 15,
    title: "Backend Deep Dive",
    subtitle: "Every service, write, event, and data payload when a query is submitted",
    time: "~10s total",
    cost: "~$0.033 total",
    llm: true,
    wideAscii: true,
    ascii: `╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                              ║
║   VQMS BACKEND DEEP DIVE                                                                    ║
║   What happens inside the system when a vendor submits a query                               ║
║                                                                                              ║
║   This diagram traces ONE query from the moment the vendor clicks "Submit"                   ║
║   to the moment the SLA monitor starts watching the ticket.                                  ║
║                                                                                              ║
║   Example query:                                                                             ║
║     Vendor:      Priya Sharma, Infosys Ltd (Gold tier)                                       ║
║     Subject:     "Contract Amendment -- Clause 7.3"                                          ║
║     Priority:    High (SLA = 4 hours)                                                        ║
║     Reference:   PO-2025-001                                                                 ║
║                                                                                              ║
║   Services involved:     10                                                                  ║
║   Data stores touched:   5 (PostgreSQL, Redis, S3, ServiceNow, Salesforce)                   ║
║   Queue messages:        1 (SQS)                                                             ║
║   Events published:      7 (EventBridge)                                                     ║
║   LLM calls (Claude):    2 (Bedrock Claude Sonnet)                                           ║
║   Embedding calls:       1 (Bedrock Titan)                                                   ║
║   Total time:            ~10 seconds                                                         ║
║   Total cost:            ~$0.033                                                             ║
║                                                                                              ║
║   Scroll down to follow the query through every service.                                     ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝


══════════════════════════════════════════════════════════════════════════════════════════════════
PROCESS FLOW: SUBMIT → SLA MONITOR (every service call in order)
══════════════════════════════════════════════════════════════════════════════════════════════════


TRIGGER: Vendor clicks "Submit Query" on the Review screen.
─────────────────────────────────────────────────────────────

  Browser builds payload from wizard state (WD object):

  POST /queries
  Authorization: Bearer <jwt-token>
  Content-Type: application/json
  {
    "type": "contract",
    "subject": "Contract Amendment -- Clause 7.3",
    "description": "We need urgent clarification on the amendment to Clause 7.3
                    regarding penalty calculations.",
    "priority": "High",
    "reference": "PO-2025-001"
  }

  NOTE: vendor_id is NOT in the payload.
  It is extracted from the JWT token on the server side.
  The vendor cannot fake their identity.

                                         │
                                         ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 1: API GATEWAY + COGNITO AUTHORIZER                                                 │
│  ─────────────────────────────────────────────                                               │
│                                                                                              │
│  What it does:                                                                               │
│    1. Receives the HTTPS request                                                             │
│    2. Passes JWT token to Cognito Authorizer                                                 │
│    3. Cognito checks:                                                                        │
│         Is the token valid? (signature, expiry, issuer)                                      │
│         Is the token expired? (exp claim > now?)                                             │
│         What role? VENDOR                                                                    │
│         What vendor? INF (Infosys)                                                           │
│         What scopes? ["queries.own", "kb.read", "prefs.own"]                                 │
│    4. If valid: attach vendor_id = "INF" to the request context                              │
│    5. If invalid: return 401 Unauthorized (flow stops here)                                  │
│    6. Forward enriched request to Query API Service                                          │
│                                                                                              │
│  Data IN:   raw HTTP request + JWT token                                                     │
│  Data OUT:  enriched request with vendor_id = "INF" in context                               │
│  Writes:    nothing                                                                          │
│  Events:    nothing                                                                          │
│  Time:      ~50ms                                                                            │
│  Cost:      $0.00                                                                            │
│                                                                                              │
└──────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                           │
                                           ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 2: QUERY API SERVICE                                                                │
│  ────────────────────────────                                                                │
│                                                                                              │
│  What it does (in order):                                                                    │
│                                                                                              │
│  STEP 2.1: VALIDATE PAYLOAD                                                                  │
│    Pydantic model: QuerySubmission                                                           │
│    Checks:                                                                                   │
│      type: must be one of [contract, invoice, delivery, tech, sla, other]  ✓ "contract"      │
│      subject: required, string, max 200 chars                              ✓ present         │
│      description: required, string, max 1000 chars                         ✓ present         │
│      priority: must be one of [Critical, High, Medium, Low]                ✓ "High"          │
│      reference: optional, string, max 100 chars                            ✓ "PO-2025-001"   │
│    If validation fails: return 400 Bad Request with field-level errors                       │
│                                                                                              │
│  STEP 2.2: GENERATE IDENTIFIERS                                                              │
│    query_id:        VQ-2025-0042 (sequential, human-readable)                                │
│    execution_id:    uuid-v4 "a7b3c9d1-..." (internal tracking)                               │
│    correlation_id:  uuid-v4 "e4f5g6h7-..." (cross-system linking)                            │
│                                                                                              │
│  STEP 2.3: IDEMPOTENCY CHECK ──────────────────────────────────────────────► Redis           │
│    Key:    vqms:idempotency:<sha256("Contract Amendment..."+desc+"INF")>                     │
│    Action: GET key                                                                           │
│    Result: NOT FOUND (this is a new query, not a duplicate)                                  │
│    If FOUND: return existing query_id (prevents double-submit)                               │
│                                                                                              │
│  STEP 2.4: SAVE TO DATABASE ───────────────────────────────────────────────► PostgreSQL      │
│    Table: workflow.case_execution                                                            │
│    SQL:                                                                                      │
│      INSERT INTO workflow.case_execution (                                                   │
│        execution_id,    -- 'a7b3c9d1-...'                                                    │
│        query_id,        -- 'VQ-2025-0042'                                                    │
│        vendor_id,       -- 'INF'                                                             │
│        query_type,      -- 'contract'                                                        │
│        subject,         -- 'Contract Amendment -- Clause 7.3'                                │
│        description,     -- 'We need urgent clarification...'                                 │
│        priority,        -- 'High'                                                            │
│        reference,       -- 'PO-2025-001'                                                     │
│        status,          -- 'OPEN'                                                            │
│        created_at       -- '2026-04-01T08:14:00Z'                                            │
│      )                                                                                       │
│                                                                                              │
│  STEP 2.5: SET IDEMPOTENCY GUARD ─────────────────────────────────────────► Redis            │
│    Key:    vqms:idempotency:<sha256(...)>                                                    │
│    Value:  "VQ-2025-0042"                                                                    │
│    TTL:    604800 seconds (7 days)                                                           │
│    Why:    If the vendor accidentally submits again within 7 days,                           │
│            the system catches it in Step 2.3 and returns the existing ID                     │
│                                                                                              │
│  STEP 2.6: PUBLISH EVENT ─────────────────────────────────────────────────► EventBridge      │
│    Bus:     vqms-event-bus                                                                   │
│    Event:   QueryReceived                                                                    │
│    Payload:                                                                                  │
│      {                                                                                       │
│        query_id: "VQ-2025-0042",                                                             │
│        vendor_id: "INF",                                                                     │
│        subject: "Contract Amendment -- Clause 7.3",                                          │
│        priority: "High",                                                                     │
│        timestamp: "2026-04-01T08:14:00Z"                                                     │
│      }                                                                                       │
│    Who listens: audit service, monitoring service                                            │
│                                                                                              │
│  STEP 2.7: PLACE IN QUEUE ────────────────────────────────────────────────► SQS              │
│    Queue:   vqms-query-intake-queue                                                          │
│    Message:                                                                                  │
│      {                                                                                       │
│        execution_id: "a7b3c9d1-...",                                                         │
│        query_id: "VQ-2025-0042",                                                             │
│        vendor_id: "INF",                                                                     │
│        type: "contract",                                                                     │
│        subject: "Contract Amendment -- Clause 7.3",                                          │
│        description: "We need urgent clarification...",                                       │
│        priority: "High",                                                                     │
│        reference: "PO-2025-001",                                                             │
│        created_at: "2026-04-01T08:14:00Z"                                                    │
│      }                                                                                       │
│    DLQ:     vqms-dlq (if processing fails 3 times)                                          │
│                                                                                              │
│  STEP 2.8: RETURN RESPONSE TO BROWSER                                                       │
│    HTTP 201 Created                                                                          │
│    Body:                                                                                     │
│      {                                                                                       │
│        "query_id": "VQ-2025-0042",                                                           │
│        "status": "Open",                                                                     │
│        "sla_deadline": "2026-04-01T12:14:00Z"                                                │
│      }                                                                                       │
│                                                                                              │
│  Data IN:   validated payload + vendor_id from JWT                                           │
│  Data OUT:  query_id + status + sla_deadline (to browser)                                    │
│             SQS message (to AI pipeline)                                                     │
│  Writes:    PostgreSQL (1), Redis (2), SQS (1), EventBridge (1)                              │
│  Time:      < 500ms total                                                                    │
│  Cost:      $0.00                                                                            │
│                                                                                              │
└──────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                           │
              ═════════════════════════════════════════════════
                ASYNC BOUNDARY: Browser gets response here.
                Everything below runs in the background.
                The vendor does not wait.
              ═════════════════════════════════════════════════
                                           │
                                           ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 3: LANGGRAPH ORCHESTRATOR (SQS Consumer)                                            │
│  ────────────────────────────────────────────────                                            │
│                                                                                              │
│  Trigger: Consumes message from vqms-query-intake-queue                                      │
│                                                                                              │
│  STEP 3.1: UPDATE STATUS ──────────────────────────────────────────────────► PostgreSQL      │
│    UPDATE workflow.case_execution                                                            │
│    SET status = 'ANALYZING', updated_at = NOW()                                              │
│    WHERE execution_id = 'a7b3c9d1-...'                                                       │
│                                                                                              │
│  STEP 3.2: CACHE WORKFLOW STATE ───────────────────────────────────────────► Redis           │
│    Key:   vqms:workflow:a7b3c9d1-...                                                         │
│    Value: { status:"ANALYZING", query_id:"VQ-2025-0042", vendor_id:"INF", step:"INIT" }      │
│    TTL:   86400 (24 hours)                                                                   │
│                                                                                              │
│  STEP 3.3: LOAD VENDOR PROFILE ────────────────────────────────────────────► Redis           │
│    Key:   vqms:vendor:INF                                                                    │
│    Check: CACHE HIT (profile cached within last 1 hour)                                      │
│    Data:                                                                                     │
│      {                                                                                       │
│        vendor_id: "INF",                                                                     │
│        name: "Infosys Ltd",                                                                  │
│        tier: "GOLD",                                                                         │
│        risk_flags: [],                                                                       │
│        primary_contact: { name: "Priya Sharma", email: "priya.sharma@infosys.com" },         │
│        account_manager: { name: "Rohit Kumar", email: "rohit.kumar@vqms.internal" },         │
│        last_synced: "2026-04-01T07:30:00Z"                                                   │
│      }                                                                                       │
│    If CACHE MISS: ─────────────────────────────────────────────────────────► Salesforce       │
│      Query: SELECT Id, Name, Tier__c, Risk_Flags__c, Primary_Contact__c                      │
│             FROM Account WHERE Vendor_Id__c = 'INF'                                          │
│      Then cache result in Redis with TTL 3600 (1 hour)                                       │
│                                                                                              │
│  STEP 3.4: LOAD VENDOR HISTORY ────────────────────────────────────────────► PostgreSQL      │
│    Table: memory.episodic_memory                                                             │
│    SQL:   SELECT interaction_summary, resolution_summary, key_entities                       │
│           FROM memory.episodic_memory                                                        │
│           WHERE vendor_id = 'INF'                                                            │
│           ORDER BY created_at DESC LIMIT 5                                                   │
│    Result: 2 prior resolved queries                                                          │
│      [                                                                                       │
│        { summary: "SLA Clause 4.2 clarification", resolved: "2026-03-29", entities: [...] }, │
│        { summary: "API integration failure", resolved: "2026-03-28", entities: [...] }       │
│      ]                                                                                       │
│                                                                                              │
│  Output: Full context package assembled:                                                     │
│    { query, vendor_profile, vendor_history, execution_metadata }                             │
│                                                                                              │
│  Writes:    PostgreSQL (1), Redis (1)                                                        │
│  Reads:     Redis (2), PostgreSQL (1), possibly Salesforce (1)                               │
│  Time:      200-800ms                                                                        │
│  Cost:      $0.00                                                                            │
│                                                                                              │
└──────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                           │
                                           ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 4: QUERYANALYSISAGENT (LLM Call #1)                                                 │
│  ───────────────────────────────────────────                                                 │
│                                                                                              │
│  STEP 4.1: LOAD PROMPT ───────────────────────────────────────────────────► S3               │
│    Bucket: vqms-knowledge-artifacts-prod                                                     │
│    Key:    templates/query-analysis/v2.json                                                   │
│    Contains: system message template + output schema definition                              │
│                                                                                              │
│  STEP 4.2: BUILD PROMPT                                                                      │
│    System: "You are a query analysis agent for VQMS. Given a vendor query,                   │
│             return a JSON object with: intent_classification, extracted_entities,             │
│             urgency_level, sentiment, confidence_score, multi_issue_detected,                 │
│             suggested_category. Be precise. Do not invent entities."                         │
│                                                                                              │
│    User: "Query type: contract                                                               │
│           Subject: Contract Amendment -- Clause 7.3                                          │
│           Description: We need urgent clarification on the amendment                         │
│             to Clause 7.3 regarding penalty calculations.                                    │
│           Reference: PO-2025-001                                                             │
│           Vendor: Infosys Ltd (Gold tier, no risk flags)                                     │
│           Recent history: SLA Clause 4.2 resolved 3 days ago,                                │
│             API integration failure resolved 4 days ago"                                     │
│                                                                                              │
│  STEP 4.3: CALL BEDROCK ──────────────────────────────────────────────────► Amazon Bedrock   │
│    Model:        anthropic.claude-sonnet-3.5                                                 │
│    Temperature:  0.1                                                                         │
│    Max tokens:   500                                                                         │
│    Input tokens:  ~1,500                                                                     │
│    Output tokens: ~500                                                                       │
│                                                                                              │
│  STEP 4.4: PARSE RESPONSE                                                                    │
│    Raw Bedrock response → parse JSON → validate against Pydantic: AnalysisResult             │
│    Parsed result:                                                                            │
│      {                                                                                       │
│        "intent": "CONTRACT_AMENDMENT",                                                       │
│        "entities": ["Clause 7.3", "penalty calculations", "PO-2025-001"],                    │
│        "urgency": "HIGH",                                                                    │
│        "sentiment": "URGENT",                                                                │
│        "confidence": 0.92,                                                                   │
│        "multi_issue": false,                                                                 │
│        "suggested_category": "contracts"                                                     │
│      }                                                                                       │
│                                                                                              │
│  STEP 4.5: SAVE PROMPT SNAPSHOT ──────────────────────────────────────────► S3               │
│    Bucket: vqms-audit-artifacts-prod                                                         │
│    Key:    prompts/a7b3c9d1-.../query-analysis.json                                          │
│    Data:   { system_message, user_message, raw_response, parsed_result, model, temperature } │
│    Why:    Audit trail. Can reproduce this exact analysis months later.                       │
│                                                                                              │
│  STEP 4.6: SAVE ANALYSIS RESULT ─────────────────────────────────────────► PostgreSQL        │
│    UPDATE workflow.case_execution                                                            │
│    SET analysis_result = '<json above>'                                                      │
│    WHERE execution_id = 'a7b3c9d1-...'                                                       │
│                                                                                              │
│  STEP 4.7: UPDATE WORKFLOW STATE ─────────────────────────────────────────► Redis            │
│    Key:   vqms:workflow:a7b3c9d1-...                                                         │
│    Set:   status = "ANALYSIS_COMPLETE"                                                       │
│                                                                                              │
│  STEP 4.8: AUDIT LOG ────────────────────────────────────────────────────► PostgreSQL        │
│    INSERT INTO audit.action_log (                                                            │
│      action_type:    'ANALYSIS_COMPLETED',                                                   │
│      execution_id:   'a7b3c9d1-...',                                                         │
│      actor:          'QueryAnalysisAgent',                                                   │
│      target_id:      'VQ-2025-0042',                                                         │
│      payload:        { intent, confidence, urgency },                                        │
│      correlation_id: 'e4f5g6h7-...',                                                         │
│      created_at:     '2026-04-01T08:14:04Z'                                                  │
│    )                                                                                         │
│                                                                                              │
│  STEP 4.9: PUBLISH EVENT ────────────────────────────────────────────────► EventBridge       │
│    Event: AnalysisCompleted                                                                  │
│    Payload: { execution_id, intent, confidence, urgency }                                    │
│                                                                                              │
│  STEP 4.10: CONFIDENCE BRANCH                                                                │
│    confidence = 0.92                                                                         │
│    threshold = 0.85                                                                          │
│    0.92 >= 0.85 → PATH: FULL_AUTOMATION                                                     │
│    (If < 0.85 → create HumanReviewPackage → SQS vqms-human-review-queue → Step Functions)     │
│                                                                                              │
│  Writes:    S3 (1), PostgreSQL (2), Redis (1), EventBridge (1)                               │
│  Time:      2-4 seconds (Bedrock inference is the bottleneck)                                │
│  Cost:      ~$0.012                                                                          │
│                                                                                              │
└──────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                           │
                                  ┌────────┴────────┐
                                  │  PARALLEL START  │
                                  ▼                  ▼

┌──────────────────────────────────────────┐ ┌─────────────────────────────────────────────────┐
│                                          │ │                                                 │
│  SERVICE 5: ROUTING SERVICE              │ │  SERVICE 6: KB SEARCH SERVICE                   │
│  ────────────────────────                │ │  ────────────────────────────                   │
│  LLM: No (deterministic rules)           │ │  LLM: No (embedding + pgvector)                 │
│                                          │ │                                                 │
│  Input:                                  │ │  STEP 6.1: EMBED QUERY TEXT ──► Bedrock Titan   │
│    AnalysisResult (from Service 4)       │ │    Input: "Contract Amendment Clause 7.3         │
│    VendorProfile (from Service 3)        │ │            penalty calculations"                │
│    TicketCorrelation (checked below)     │ │    Model: amazon.titan-embed-text-v2            │
│                                          │ │    Output: vector(1536)                         │
│  STEP 5.1: CHECK EXISTING TICKET         │ │    Cost: ~$0.0001                               │
│    SELECT ticket_id                      │ │                                                 │
│    FROM workflow.ticket_link             │ │  STEP 6.2: SEARCH ────────────► PostgreSQL      │
│    WHERE correlation references          │ │    SELECT id, content_text, metadata,            │
│      match "PO-2025-001"                 │ │           1 - (embedding <=> $1) AS similarity  │
│    Result: NONE FOUND                    │ │    FROM memory.embedding_index                  │
│                                          │ │    WHERE metadata->>'category' = 'contracts'    │
│  STEP 5.2: EVALUATE RULES               │ │    ORDER BY embedding <=> $1                    │
│    confidence >= 0.85?  YES (0.92)       │ │    LIMIT 5                                      │
│    urgency == CRITICAL? NO  (HIGH)       │ │                                                 │
│    tier == PLATINUM?    NO  (GOLD)       │ │  STEP 6.3: RE-RANK                              │
│    existing ticket?     NO               │ │    Combine similarity score with:                │
│    → Path: FULL_AUTOMATION               │ │      recency (newer articles rank higher)       │
│                                          │ │      usage count (popular articles rank higher)  │
│  STEP 5.3: DETERMINE RESOLVER            │ │                                                 │
│    Policy matrix:                        │ │  Results:                                        │
│    intent=CONTRACT_AMENDMENT             │ │    #847 "Standard Vendor Contract Amendment      │
│    × tier=GOLD                           │ │          Procedure v3.2"            94% match   │
│    × priority=HIGH                       │ │    #412 "Penalty Calculation Policy              │
│    → resolver_group: "Procurement Team"  │ │          -- Clause 7 Series"       81% match   │
│                                          │ │    #291 "Contract Amendment Precedent            │
│  STEP 5.4: SET SLA ─────────► PostgreSQL │ │          Log (Q1-Q3 2025)"         72% match   │
│    base: High = 4 hours                  │ │                                                 │
│    Gold tier modifier: none              │ │  Output: top 3 articles with full text           │
│    final SLA: 4 hours                    │ │  and similarity scores                          │
│    deadline: 2026-04-01T12:14:00Z        │ │                                                 │
│                                          │ │  Writes:   nothing                              │
│  STEP 5.5: SAVE DECISION ──► PostgreSQL  │ │  Time:     < 200ms                              │
│    INSERT INTO routing_decision (        │ │  Cost:     ~$0.0001                             │
│      execution_id, intent, vendor_tier,  │ │                                                 │
│      urgency, resolver_group,            │ └─────────────────────────────────────────────────┘
│      decision_path: 'FULL_AUTOMATION',   │
│      confidence_score: 0.92,             │
│      rationale: 'High confidence,        │
│        Gold tier, no risk flags'         │
│    )                                     │
│                                          │
│  Writes:   PostgreSQL (1)                │
│  Time:     < 50ms                        │
│  Cost:     $0.00                         │
│                                          │
└──────────────────┬───────────────────────┘
                   │
                   └──────────────┬─── routing + KB results merged
                                  │
                                  ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 7: RESOLUTIONAGENT (LLM Call #2)                                                    │
│  ────────────────────────────────────────                                                    │
│                                                                                              │
│  STEP 7.1: LOAD PROMPT ──────────────────────────────────────────────────► S3                │
│    templates/resolution/v3.json                                                              │
│                                                                                              │
│  STEP 7.2: ASSEMBLE CONTEXT                                                                  │
│    query:       subject + description                                                        │
│    analysis:    CONTRACT_AMENDMENT, HIGH, URGENT, 0.92                                       │
│    kb_articles: #847 (full text, 94%), #412 (full text, 81%), #291 (full text, 72%)          │
│    vendor:      Infosys Ltd, Gold, no risk flags                                             │
│    sla:         4 hours, deadline 12:14:00Z                                                  │
│    history:     2 prior resolved queries                                                     │
│                                                                                              │
│  STEP 7.3: CALL BEDROCK ─────────────────────────────────────────────────► Amazon Bedrock    │
│    Model: anthropic.claude-sonnet-3.5, Temperature: 0.3, Max tokens: 1000                    │
│    Input tokens: ~3,000 | Output tokens: ~800                                                │
│                                                                                              │
│  STEP 7.4: PARSE RESPONSE → DraftResponse                                                   │
│    {                                                                                         │
│      "subject": "RE: Contract Amendment -- Clause 7.3",                                      │
│      "body": "Based on KB article #847 (94% match), Clause 7.3 refers to the standard       │
│               penalty schedule (Q1 2024). Amendment has precedent in 14 similar cases --     │
│               all resolved with a 2.5%/month penalty cap.\\n\\nRecommended: Accept with      │
│               rider referencing Exhibit C, Section 2.",                                       │
│      "confidence": 0.94,                                                                     │
│      "sources_cited": ["KB#847", "KB#412"],                                                  │
│      "sla_statement": "Response within 4 hours per Gold tier SLA"                            │
│    }                                                                                         │
│                                                                                              │
│  STEP 7.5: SAVE DRAFT ──────────────────────────────────────────────────► PostgreSQL         │
│    UPDATE case_execution SET response_draft = '<json above>'                                 │
│                                                                                              │
│  STEP 7.6: SAVE PROMPT SNAPSHOT ─────────────────────────────────────────► S3                │
│    prompts/a7b3c9d1-.../resolution.json                                                      │
│                                                                                              │
│  STEP 7.7: PUBLISH EVENT ────────────────────────────────────────────────► EventBridge       │
│    DraftPrepared { execution_id, draft_version: 1, template: "resolution/v3" }               │
│                                                                                              │
│  Writes:    PostgreSQL (1), S3 (1), Redis (1), EventBridge (1)                               │
│  Time:      3-6 seconds                                                                      │
│  Cost:      ~$0.021                                                                          │
│                                                                                              │
└──────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                           │
                                           ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 8: QUALITYGATEAGENT                                                                 │
│  ───────────────────────────                                                                 │
│                                                                                              │
│  PHASE 1: DETERMINISTIC CHECKS (no LLM)                                                     │
│    [PASS] Ticket # format: INC\\d{7} regex                                                   │
│    [PASS] SLA wording: "4 hours" matches Gold/High policy                                    │
│    [PASS] Required sections: greeting ✓, summary ✓, next steps ✓, signature ✓               │
│    [PASS] Restricted terms: 0 matches on blocklist                                           │
│    [PASS] Response length: 147 words (range 50-500)                                          │
│    [PASS] Source citations: 2 KB articles cited (minimum 1)                                  │
│                                                                                              │
│  PHASE 2: CONDITIONAL (runs because priority = HIGH)                                         │
│    PII scan ──────────────────────────────────────────────────────────────► Comprehend        │
│      DetectPiiEntities on draft body                                                         │
│      Result: NO PII detected                                                                │
│    Tone check via Bedrock?                                                                   │
│      No near-miss restricted terms + no NEGATIVE sentiment → SKIP                            │
│                                                                                              │
│  RESULT: PASS                                                                                │
│                                                                                              │
│  STEP 8.1: SAVE REPORT ─────────────────────────────────────────────────► S3                 │
│    audit/INC0012345/2026-04-01T08:14:08Z/validation-report.json                              │
│                                                                                              │
│  STEP 8.2: SAVE TO DB ──────────────────────────────────────────────────► PostgreSQL         │
│    INSERT INTO audit.validation_results (                                                    │
│      execution_id, draft_version: 1, overall_status: 'PASS',                                 │
│      checks: [{name,status,details}...], pii_detected: false                                 │
│    )                                                                                         │
│                                                                                              │
│  STEP 8.3: PUBLISH EVENT ───────────────────────────────────────────────► EventBridge        │
│    ValidationPassed { execution_id, validation_report_s3_key }                               │
│                                                                                              │
│  If FAIL: re-draft (Service 7 again, max 2 retries) then human review queue                  │
│                                                                                              │
│  Writes:    S3 (1), PostgreSQL (1), EventBridge (1)                                          │
│  Time:      < 200ms                                                                          │
│  Cost:      $0.00 (deterministic path on this query)                                         │
│                                                                                              │
└──────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                           │
                                           ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 9: TICKET OPERATIONS + RESPONSE DELIVERY                                            │
│  ────────────────────────────────────────────────                                            │
│                                                                                              │
│  STEP 9.1: CHECK FOR EXISTING TICKET ─────────────────────────────────────► PostgreSQL       │
│    SELECT ticket_id FROM workflow.ticket_link                                                │
│    WHERE correlation_id = 'e4f5g6h7-...'                                                     │
│    Result: NONE → create new                                                                 │
│                                                                                              │
│  STEP 9.2: CREATE SERVICENOW TICKET ──────────────────────────────────────► ServiceNow       │
│    POST /api/now/table/incident                                                              │
│    {                                                                                         │
│      "category": "Contract",                                                                 │
│      "subcategory": "Amendment",                                                             │
│      "urgency": 2,                                                                           │
│      "impact": 2,                                                                            │
│      "assignment_group": "Procurement Team",                                                 │
│      "short_description": "Contract Amendment -- Clause 7.3",                                │
│      "description": "We need urgent clarification on the amendment to Clause 7.3...",        │
│      "caller_id": "<salesforce_contact_sys_id>",                                             │
│      "correlation_id": "e4f5g6h7-..."                                                        │
│    }                                                                                         │
│    Response: { "sys_id": "abc123def456", "number": "INC0012345" }                            │
│                                                                                              │
│  STEP 9.3: SAVE TICKET MAPPING ───────────────────────────────────────────► PostgreSQL       │
│    INSERT INTO workflow.ticket_link (                                                        │
│      email_message_id: null (portal, not email),                                             │
│      query_id: 'VQ-2025-0042',                                                               │
│      ticket_id: 'abc123def456',                                                              │
│      ticket_number: 'INC0012345',                                                            │
│      ticket_status: 'OPEN',                                                                  │
│      correlation_id: 'e4f5g6h7-...'                                                          │
│    )                                                                                         │
│                                                                                              │
│  STEP 9.4: CACHE TICKET ─────────────────────────────────────────────────► Redis             │
│    Key:   vqms:ticket:abc123def456                                                           │
│    Value: { number:"INC0012345", status:"OPEN", group:"Procurement Team", sla:4 }            │
│    TTL:   3600 (1 hour)                                                                      │
│                                                                                              │
│  STEP 9.5: UPDATE STATUS ────────────────────────────────────────────────► PostgreSQL        │
│    UPDATE workflow.case_execution                                                            │
│    SET status = 'RESPONDED', ticket_id = 'abc123def456', updated_at = NOW()                  │
│                                                                                              │
│  STEP 9.6: UPDATE WORKFLOW CACHE ────────────────────────────────────────► Redis             │
│    Key:   vqms:workflow:a7b3c9d1-...                                                         │
│    Set:   status = "COMPLETE"                                                                │
│                                                                                              │
│  STEP 9.7: SEND EMAIL ──────────────────────────────────────────────────► MS Graph API       │
│    POST https://graph.microsoft.com/v1.0/users/vendor-support@company.com/sendMail           │
│    {                                                                                         │
│      "message": {                                                                            │
│        "subject": "RE: Contract Amendment -- Clause 7.3 [INC0012345]",                       │
│        "toRecipients": [{ "emailAddress": { "address": "priya.sharma@infosys.com" }}],       │
│        "body": { "contentType": "HTML", "content": "<draft body + ticket # + SLA>" }         │
│      }                                                                                       │
│    }                                                                                         │
│                                                                                              │
│  STEP 9.8: AUDIT LOG ───────────────────────────────────────────────────► PostgreSQL         │
│    INSERT INTO audit.action_log (action_type: 'EMAIL_SENT', ...)                             │
│                                                                                              │
│  STEP 9.9: PUBLISH EVENTS ──────────────────────────────────────────────► EventBridge        │
│    TicketCreated { ticket_id, ticket_number, assignment_group, sla_target }                   │
│    EmailSent { execution_id, outbound_message_id, recipient }                                │
│    QueryResolved { execution_id, query_id, ticket_number }                                   │
│                                                                                              │
│  Writes:    ServiceNow (1), PostgreSQL (3), Redis (2), EventBridge (3)                       │
│  Time:      ~2 seconds (ServiceNow API + email send)                                         │
│  Cost:      $0.00                                                                            │
│                                                                                              │
└──────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                           │ TicketCreated event triggers:
                                           ▼

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                              │
│  SERVICE 10: SLA MONITOR (Step Functions state machine)                                      │
│  ─────────────────────────────────────────────────────                                       │
│                                                                                              │
│  Trigger: TicketCreated event from Service 9                                                 │
│                                                                                              │
│  STEP 10.1: CALCULATE THRESHOLDS                                                             │
│    SLA target: 4 hours (Gold + High)                                                         │
│    Created: 08:14:00 | Deadline: 12:14:00                                                    │
│    70% mark: 08:14 + 2h48m = 11:02                                                           │
│    85% mark: 08:14 + 3h24m = 11:38                                                           │
│    95% mark: 08:14 + 3h48m = 12:02                                                           │
│                                                                                              │
│  STEP 10.2: SET SLA STATE ───────────────────────────────────────────────► Redis             │
│    Key:   vqms:sla:abc123def456                                                              │
│    Value: { start:"08:14", target_hours:4, deadline:"12:14",                                 │
│             elapsed_pct:0, next_threshold:70 }                                               │
│    TTL:   none (persists until ticket closed)                                                │
│                                                                                              │
│  STEP 10.3: ENTER WAIT STATE (Step Functions)                                                │
│    Wait until: 2026-04-01T11:02:00Z (70% mark)                                              │
│                                                                                              │
│  STEP 10.4: AT 70% — CHECK + WARN                                                            │
│    Check ticket status in ServiceNow. Resolved? STOP.                                        │
│    Not resolved → EventBridge: SLAWarning70 → notify resolver                                │
│    Wait until: 11:38 (85% mark)                                                              │
│                                                                                              │
│  STEP 10.5: AT 85% — CHECK + ESCALATE L1                                                     │
│    Check ticket status. Resolved? STOP.                                                      │
│    Not resolved → EventBridge: SLAEscalation85                                               │
│      → SQS: vqms-escalation-queue → L1 manager notified                                     │
│    Wait until: 12:02 (95% mark)                                                              │
│                                                                                              │
│  STEP 10.6: AT 95% — CHECK + ESCALATE L2                                                     │
│    Check ticket status. Resolved? STOP.                                                      │
│    Not resolved → EventBridge: SLAEscalation95                                               │
│      → L2 senior management alert                                                            │
│                                                                                              │
│  ON RESOLUTION (at any point):                                                               │
│    Stop state machine                                                                        │
│    Write to reporting.sla_metrics:                                                           │
│      { ticket_id, vendor_tier:"GOLD", sla_target:4, actual_hours:<X>,                        │
│        breach:false, escalation_level:0 }                                                    │
│                                                                                              │
│  Writes:    Redis (1), PostgreSQL (on resolution), EventBridge (up to 3)                     │
│  Time:      runs for hours (background)                                                      │
│  Cost:      $0.00                                                                            │
│                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘


══════════════════════════════════════════════════════════════════════════════════════════════════
UML SEQUENCE DIAGRAM: QUERY SUBMISSION → SLA MONITOR
══════════════════════════════════════════════════════════════════════════════════════════════════

Browser  APIGw  QueryAPI  Redis  PostgreSQL  S3  SQS  EventBridge  LangGraph  Bedrock  Salesforce  pgvector  Comprehend  ServiceNow  MSGraph  SLAMon
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │─POST─►│       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │─auth─►│        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │─GET───►│        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │◄─miss──│        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │─INSERT─│───────►│        │    │       │           │          │         │          │          │           │          │        │
   │       │       │─SET───►│        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │─event──│────────│────────│────│──────►│           │          │         │          │          │           │          │        │
   │       │       │─push───│────────│────────│───►│       │           │          │         │          │          │           │          │        │
   │◄──id──│◄──────│        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │ ════ ASYNC ═══│════════│════════│════════│════│═══════│═══════════│══════════│═════════│══════════│══════════│═══════════│══════════│════════│
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │─msg──►│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─UPDATE──►│         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─SET────►│         │          │          │           │          │        │
   │       │       │        │◄──GET──│────────│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │─hit───►│────────│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │◄─SELECT│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─analyze─►│─────────│          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │─Bedrock►│          │          │           │          │        │
   │       │       │        │        │        │    │       │           │◄─result──│◄────────│          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─PUT─────►│─────────│──────────│          │           │          │        │
   │       │       │        │        │◄─UPDATE│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │◄─SET───│────────│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │◄──event───│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │══PARALLEL│═════════│══════════│══════════│           │          │        │
   │       │       │        │        │        │    │       │           │─rules────│         │          │          │           │          │        │
   │       │       │        │        │◄─INSERT│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─embed───►│─────────│──────────│          │           │          │        │
   │       │       │        │        │        │    │       │           │          │─Titan──►│          │          │           │          │        │
   │       │       │        │        │        │    │       │           │◄─vector──│◄────────│──────────│◄─results─│           │          │        │
   │       │       │        │        │        │    │       │           │══MERGE═══│═════════│══════════│══════════│           │          │        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─draft───►│─────────│          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │─Bedrock►│          │          │           │          │        │
   │       │       │        │        │        │    │       │           │◄─draft───│◄────────│          │          │           │          │        │
   │       │       │        │        │◄─UPDATE│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │◄PUT│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │◄──event───│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─validate─│─────────│──────────│──────────│◄─PII scan─│          │        │
   │       │       │        │        │        │◄PUT│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │◄─INSERT│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │◄──event───│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─ticket──►│─────────│──────────│──────────│───────────│──────────│        │
   │       │       │        │        │        │    │       │           │          │         │          │          │  ─POST──►│          │        │
   │       │       │        │        │        │    │       │           │◄─INC#────│─────────│──────────│──────────│◄─created─│          │        │
   │       │       │        │        │◄─INSERT│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │◄─SET───│────────│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │◄─UPDATE│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─email───►│─────────│──────────│──────────│───────────│──────────│─send──►│
   │       │       │        │        │◄─audit─│────│───────│───────────│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │◄──events──│          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │──trigger─►│──────────│─────────│──────────│──────────│───────────│──────────│───────►│
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │  SLA   │
   │       │       │        │◄─SET───│────────│────│───────│───────────│──────────│─────────│──────────│──────────│───────────│──────────│ monitor│
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │ starts │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
   │       │       │        │        │        │    │       │           │─DONE─────│─────────│──────────│──────────│───────────│──────────│        │
   │       │       │        │        │        │    │       │           │          │         │          │          │           │          │        │
══════════════════════════════════════════════════════════════════════════════════════════════════


══════════════════════════════════════════════════════════════════════════════════════════════════
DATA WRITES: EVERY STORE TOUCHED, EVERY KEY, EVERY TABLE
══════════════════════════════════════════════════════════════════════════════════════════════════

 SERVICE        STORE          KEY / TABLE                               OPERATION    TTL
 ───────        ─────          ───────────                               ─────────    ───
 Query API      Redis          vqms:idempotency:<sha256>                 GET (check)  --
 Query API      PostgreSQL     workflow.case_execution                   INSERT       perm
 Query API      Redis          vqms:idempotency:<sha256>                 SET          7 days
 Query API      EventBridge    QueryReceived                             PUBLISH      --
 Query API      SQS            vqms-query-intake-queue                   PUSH         --
 Orchestrator   PostgreSQL     workflow.case_execution (status)          UPDATE       perm
 Orchestrator   Redis          vqms:workflow:<exec-id>                   SET          24h
 Orchestrator   Redis          vqms:vendor:INF                           GET (cache)  1h
 Orchestrator   PostgreSQL     memory.episodic_memory                    SELECT       --
 Analysis       S3             prompts/<exec>/query-analysis.json        PUT          perm
 Analysis       PostgreSQL     workflow.case_execution (analysis)        UPDATE       perm
 Analysis       Redis          vqms:workflow:<exec-id>                   UPDATE       24h
 Analysis       PostgreSQL     audit.action_log                          INSERT       perm
 Analysis       EventBridge    AnalysisCompleted                         PUBLISH      --
 Analysis       Bedrock        claude-sonnet-3.5                         INVOKE       --
 Routing        PostgreSQL     workflow.routing_decision                 INSERT       perm
 KB Search      Bedrock        titan-embed-text-v2                       INVOKE       --
 KB Search      PostgreSQL     memory.embedding_index                    SELECT       --
 Resolution     S3             prompts/<exec>/resolution.json            PUT          perm
 Resolution     PostgreSQL     workflow.case_execution (draft)           UPDATE       perm
 Resolution     Redis          vqms:workflow:<exec-id>                   UPDATE       24h
 Resolution     EventBridge    DraftPrepared                             PUBLISH      --
 Resolution     Bedrock        claude-sonnet-3.5                         INVOKE       --
 QualityGate    Comprehend     DetectPiiEntities                         INVOKE       --
 QualityGate    S3             audit/<ticket>/validation-report.json     PUT          perm
 QualityGate    PostgreSQL     audit.validation_results                  INSERT       perm
 QualityGate    EventBridge    ValidationPassed                          PUBLISH      --
 Ticket Ops     ServiceNow     /api/now/table/incident                   POST         --
 Ticket Ops     PostgreSQL     workflow.ticket_link                      INSERT       perm
 Ticket Ops     Redis          vqms:ticket:<ticket-id>                   SET          1h
 Ticket Ops     PostgreSQL     workflow.case_execution (status)          UPDATE       perm
 Ticket Ops     Redis          vqms:workflow:<exec-id>                   UPDATE       24h
 Ticket Ops     MS Graph       /sendMail                                 POST         --
 Ticket Ops     PostgreSQL     audit.action_log                          INSERT       perm
 Ticket Ops     EventBridge    TicketCreated + EmailSent + QueryResolved PUBLISH      --
 SLA Monitor    Redis          vqms:sla:<ticket-id>                      SET          persist
 SLA Monitor    EventBridge    SLAWarning70 / Escalation85 / 95         PUBLISH      --
 SLA Monitor    PostgreSQL     reporting.sla_metrics                     INSERT       perm

 ─────────────────────────────────────────────────────────────────────────────────────────
 TOTALS:
   PostgreSQL writes:    12 (across 6 tables in 4 schemas)
   Redis writes:          9 (sessions, caches, state, SLA)
   S3 writes:             3 (prompt snapshots, validation report)
   External API calls:    2 (ServiceNow POST, MS Graph sendMail)
   Bedrock invocations:   3 (2 Claude, 1 Titan embed)
   Comprehend calls:      1 (PII scan)
   EventBridge events:    7
   SQS messages:          1


══════════════════════════════════════════════════════════════════════════════════════════════════
COST AND TIMING BREAKDOWN
══════════════════════════════════════════════════════════════════════════════════════════════════

 SERVICE                    TIME          COST         TOKENS IN    TOKENS OUT
 ───────                    ────          ────         ─────────    ──────────
 API Gateway + Auth         ~50ms         $0.000       --           --
 Query API Service          ~450ms        $0.000       --           --
 ─── ASYNC BOUNDARY ─── vendor gets response in ~500ms ────────────────────────
 LangGraph Orchestrator     ~600ms        $0.000       --           --
 QueryAnalysisAgent         2-4s          $0.012       ~1,500       ~500
 RoutingService             < 50ms        $0.000       --           --
 KBSearchService            < 200ms       $0.0001      --           --
 ResolutionAgent            3-6s          $0.021       ~3,000       ~800
 QualityGateAgent           < 200ms       $0.000       --           --
 Ticket Ops + Email         ~2s           $0.000       --           --
 SLA Monitor start          ~100ms        $0.000       --           --

 TOTAL BACKEND:             ~10 seconds
 TOTAL COST:                ~$0.033
 TOTAL TOKENS:              ~4,500 in + ~1,300 out = ~5,800 tokens

 AT SCALE:
   10,000 queries/month     ~$330/month     ~58M tokens/month
   50,000 queries/month     ~$1,650/month   ~290M tokens/month
   100,000 queries/month    ~$3,300/month   ~580M tokens/month`,
    ui: "fullascii"
  }
];

// UI Components for each step
function LoginUI() {
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:24}}>
      <div style={{width:48,height:48,borderRadius:12,background:'linear-gradient(135deg,#3b82f6,#1d4ed8)',display:'flex',alignItems:'center',justifyContent:'center',marginBottom:12}}>
        <span style={{color:'#fff',fontSize:18,fontWeight:700}}>V</span>
      </div>
      <div style={{fontSize:18,fontWeight:700,color:'#1e293b'}}>VQMS</div>
      <div style={{fontSize:10,color:'#94a3b8',marginBottom:20,fontFamily:'monospace'}}>Vendor Query Management</div>
      <div style={{background:'#fff',borderRadius:14,padding:24,width:'100%',maxWidth:320,border:'1px solid #e2e8f0',boxShadow:'0 4px 20px rgba(0,0,0,.06)'}}>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:6,marginBottom:16,background:'#f1f5f9',borderRadius:8,padding:3}}>
          <div style={{padding:'8px 6px',borderRadius:6,fontSize:11,textAlign:'center',color:'#94a3b8'}}>Admin</div>
          <div style={{padding:'8px 6px',borderRadius:6,fontSize:11,textAlign:'center',background:'#fff',color:'#3b82f6',fontWeight:600,boxShadow:'0 1px 3px rgba(0,0,0,.08)',border:'1px solid #e2e8f0'}}>Vendor</div>
        </div>
        <div style={{background:'#fff',border:'1.5px solid #3b82f6',color:'#3b82f6',padding:'10px 16px',borderRadius:6,fontSize:13,fontWeight:600,textAlign:'center',cursor:'pointer',marginBottom:8,display:'flex',alignItems:'center',justifyContent:'center',gap:6}}>
          <span>🛡️</span> Sign in with Company SSO
        </div>
        <div style={{fontSize:9,color:'#94a3b8',textAlign:'center',marginBottom:12}}>For Infosys, TCS, Wipro and other SSO-enabled vendors</div>
        <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:12}}>
          <div style={{flex:1,height:1,background:'#e2e8f0'}}/>
          <span style={{fontSize:10,color:'#94a3b8',fontWeight:500}}>or</span>
          <div style={{flex:1,height:1,background:'#e2e8f0'}}/>
        </div>
        <div style={{marginBottom:12}}>
          <div style={{fontSize:9,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.06em',marginBottom:4,fontFamily:'monospace'}}>Email</div>
          <div style={{background:'#f8fafc',border:'1px solid #e2e8f0',borderRadius:6,padding:'8px 10px',fontSize:12,color:'#1e293b'}}>priya.sharma@infosys.com</div>
        </div>
        <div style={{marginBottom:16}}>
          <div style={{fontSize:9,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.06em',marginBottom:4,fontFamily:'monospace'}}>Password</div>
          <div style={{background:'#f8fafc',border:'1px solid #e2e8f0',borderRadius:6,padding:'8px 10px',fontSize:12,color:'#94a3b8'}}>••••••••</div>
        </div>
        <div style={{background:'linear-gradient(135deg,#3b82f6,#1d4ed8)',color:'#fff',padding:'10px 16px',borderRadius:6,fontSize:13,fontWeight:600,textAlign:'center',cursor:'pointer'}}>Sign In</div>
      </div>
    </div>
  );
}

function DashboardUI() {
  const kpis = [
    {l:'Open Queries',v:'6',c:'#3b82f6',t:'2 near SLA',tc:'#f59e0b',bars:[3,5,4,6,5,6]},
    {l:'Resolved',v:'14',c:'#10b981',t:'+3 vs last month',tc:'#10b981',bars:[8,9,10,11,12,14]},
    {l:'Avg Response',v:'2.4h',c:'#f59e0b',t:'18% faster',tc:'#10b981',bars:[4.2,3.8,3.5,3.1,2.8,2.4]}
  ];
  const actions = [
    {ico:'✏️',lbl:'New Query',sub:'Raise a new issue',bg:'#3b82f6'},
    {ico:'📂',lbl:'My Queries',sub:'View all your queries',bg:'#10b981'},
    {ico:'📚',lbl:'Knowledge Base',sub:'Search solutions',bg:'#6366f1'},
    {ico:'⚙️',lbl:'Preferences',sub:'Notification settings',bg:'#f59e0b'}
  ];
  const queries = [
    {id:'VQ-2025-0041',s:'Contract Amendment — Clause 7.3',st:'In Progress',sc:'#6d28d9',sb:'rgba(124,58,237,.08)',sbc:'rgba(124,58,237,.18)',p:'High',pc:'#b45309',pb:'rgba(245,158,11,.08)',pbc:'rgba(245,158,11,.2)',time:'2h ago'},
    {id:'VQ-2025-0039',s:'Invoice Dispute — PO #8821',st:'Awaiting Vendor',sc:'#b45309',sb:'rgba(245,158,11,.08)',sbc:'rgba(245,158,11,.2)',p:'Critical',pc:'#ef4444',pb:'rgba(239,68,68,.08)',pbc:'rgba(239,68,68,.18)',time:'5h ago'},
    {id:'VQ-2025-0036',s:'Delivery Delay — Shipment #DL-7790',st:'Open',sc:'#3b82f6',sb:'rgba(37,99,235,.08)',sbc:'rgba(37,99,235,.18)',p:'Medium',pc:'#64748b',pb:'rgba(100,116,139,.08)',pbc:'rgba(100,116,139,.18)',time:'1d ago'},
    {id:'VQ-2025-0033',s:'SLA Clarification — Penalty terms',st:'Resolved',sc:'#059669',sb:'rgba(16,185,129,.08)',sbc:'rgba(16,185,129,.2)',p:'Low',pc:'#64748b',pb:'rgba(100,116,139,.08)',pbc:'rgba(100,116,139,.18)',time:'3d ago'}
  ];
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:16,gap:10}}>
      {/* Welcome Banner */}
      <div style={{background:'linear-gradient(135deg,#eff6ff,#f0ecff)',borderRadius:12,padding:'12px 16px',display:'flex',alignItems:'center',gap:12,border:'1px solid #e2e8f0'}}>
        <div style={{width:40,height:40,borderRadius:10,background:'linear-gradient(135deg,#3b82f6,#1d4ed8)',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
          <span style={{color:'#fff',fontSize:14,fontWeight:700}}>PS</span>
        </div>
        <div style={{flex:1}}>
          <div style={{fontSize:14,fontWeight:700,color:'#1e293b'}}>Welcome back, Priya</div>
          <div style={{display:'flex',alignItems:'center',gap:8,marginTop:2}}>
            <span style={{fontSize:10,color:'#64748b'}}>Infosys Ltd</span>
            <span style={{fontSize:8,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace"}}>Data as of Today, 08:14 AM</span>
          </div>
        </div>
        <div style={{padding:'4px 10px',borderRadius:12,background:'rgba(245,158,11,.1)',border:'1px solid rgba(245,158,11,.25)',fontSize:9,color:'#b45309',fontWeight:600,fontFamily:"'IBM Plex Mono',monospace",whiteSpace:'nowrap'}}>
          2 near SLA
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:8}}>
        {kpis.map((k,i)=>{
          const max = Math.max(...k.bars);
          return (
            <div key={i} style={{background:'#fff',borderRadius:10,padding:'10px 12px',border:'1px solid #e2e8f0',position:'relative',overflow:'hidden',cursor:'pointer',transition:'transform .15s, box-shadow .15s'}}>
              <div style={{position:'absolute',left:0,top:0,bottom:0,width:3,background:k.c,borderRadius:'10px 0 0 10px'}}/>
              <div style={{fontSize:8,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.06em',fontFamily:"'IBM Plex Mono',monospace",marginBottom:2}}>{k.l}</div>
              <div style={{fontSize:22,fontWeight:700,fontFamily:"'IBM Plex Mono',monospace",color:'#1e293b',lineHeight:1.1}}>{k.v}</div>
              <div style={{fontSize:9,color:k.tc,fontFamily:"'IBM Plex Mono',monospace",marginTop:3,fontWeight:500}}>{k.t}</div>
              <div style={{display:'flex',alignItems:'flex-end',gap:2,marginTop:6,height:18}}>
                {k.bars.map((b,j)=>(
                  <div key={j} style={{flex:1,height:`${(b/max)*100}%`,background:`linear-gradient(180deg,${k.c},${k.c}88)`,borderRadius:'2px 2px 0 0',minHeight:2}}/>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:6}}>
        {actions.map((a,i)=>(
          <div key={i} style={{background:'#fff',borderRadius:8,padding:'8px 6px',border:'1px solid #e2e8f0',textAlign:'center',cursor:'pointer',transition:'border-color .15s, transform .15s'}}>
            <div style={{width:28,height:28,borderRadius:8,background:`${a.bg}15`,display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 4px',fontSize:14}}>{a.ico}</div>
            <div style={{fontSize:10,fontWeight:600,color:'#1e293b'}}>{a.lbl}</div>
            <div style={{fontSize:8,color:'#94a3b8',marginTop:1}}>{a.sub}</div>
          </div>
        ))}
      </div>

      {/* Recent Queries */}
      <div>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:6}}>
          <span style={{fontSize:8,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.08em',fontFamily:"'IBM Plex Mono',monospace"}}>Recent Queries</span>
          <span style={{fontSize:9,color:'#3b82f6',cursor:'pointer',fontWeight:500}}>View all →</span>
        </div>
        <div style={{display:'flex',flexDirection:'column',gap:4}}>
          {queries.map((q,i)=>(
            <div key={i} style={{background:'#fff',borderRadius:8,padding:'7px 10px',border:'1px solid #e2e8f0',display:'flex',alignItems:'center',gap:6,cursor:'pointer',transition:'background .1s'}}>
              <span style={{fontFamily:"'IBM Plex Mono',monospace",fontSize:8,color:'#94a3b8',minWidth:80}}>{q.id}</span>
              <span style={{flex:1,fontWeight:500,color:'#1e293b',fontSize:10,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{q.s}</span>
              <span style={{fontSize:7,fontFamily:"'IBM Plex Mono',monospace",padding:'2px 6px',borderRadius:8,background:q.sb,color:q.sc,border:`1px solid ${q.sbc}`,whiteSpace:'nowrap'}}>{q.st}</span>
              <span style={{fontSize:7,fontFamily:"'IBM Plex Mono',monospace",padding:'2px 6px',borderRadius:8,background:q.pb,color:q.pc,border:`1px solid ${q.pbc}`,whiteSpace:'nowrap'}}>{q.p}</span>
              <span style={{fontSize:8,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace",whiteSpace:'nowrap'}}>{q.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function WizardTypeUI() {
  const types = [
    {ico:'📋',l:'Contract Dispute',sub:'Amendment, clause, penalty',sel:true},
    {ico:'💳',l:'Invoice Issue',sub:'Billing, payment, PO mismatch'},
    {ico:'🚚',l:'Delivery Delay',sub:'Shipment, ETA, logistics'},
    {ico:'🔧',l:'Tech Support',sub:'Integration, API, system'},
    {ico:'⏱️',l:'SLA Clarification',sub:'Policy, terms, breach'},
    {ico:'💬',l:'Other',sub:'General enquiry'}
  ];
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:16,gap:10}}>
      {/* Step Progress Bar with labels */}
      <div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <StepDot n={1} active/><div style={{flex:1,height:2,background:'linear-gradient(90deg,#3b82f6,#e2e8f0)',borderRadius:2}}/><StepDot n={2}/><div style={{flex:1,height:0,borderTop:'2px dashed #cbd5e1'}}/><StepDot n={3}/>
        </div>
        <div style={{display:'flex',justifyContent:'space-between',marginTop:4,padding:'0 2px'}}>
          {['Type','Details','Review'].map((lbl,i)=>(
            <span key={i} style={{fontSize:8,fontWeight:i===0?600:400,color:i===0?'#3b82f6':'#94a3b8',fontFamily:"'IBM Plex Mono',monospace",width:24,textAlign:'center'}}>{lbl}</span>
          ))}
        </div>
      </div>

      {/* Header */}
      <div>
        <div style={{fontSize:14,fontWeight:700,color:'#1e293b'}}>What type of query is this?</div>
        <div style={{fontSize:10,color:'#64748b',marginTop:3,lineHeight:1.4}}>Pick the category that best matches your issue. This helps our AI route it to the right team faster.</div>
      </div>

      {/* Type Cards */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:8,flex:1}}>
        {types.map((t,i)=>(
          <div key={i} style={{padding:'10px 8px',border:`2px solid ${t.sel?'#3b82f6':'#e2e8f0'}`,borderRadius:10,background:t.sel?'rgba(37,99,235,.04)':'#fff',textAlign:'center',cursor:'pointer',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:3,boxShadow:t.sel?'0 0 0 3px rgba(37,99,235,.1)':'0 1px 3px rgba(0,0,0,.04)',position:'relative',transition:'transform .15s, border-color .15s, box-shadow .15s'}}>
            {t.sel&&<div style={{position:'absolute',top:6,right:6,width:16,height:16,borderRadius:'50%',background:'#3b82f6',display:'flex',alignItems:'center',justifyContent:'center'}}>
              <span style={{color:'#fff',fontSize:9,fontWeight:700}}>✓</span>
            </div>}
            <div style={{width:36,height:36,borderRadius:10,background:t.sel?'rgba(37,99,235,.1)':'#f1f5f9',display:'flex',alignItems:'center',justifyContent:'center'}}>
              <span style={{fontSize:20}}>{t.ico}</span>
            </div>
            <span style={{fontSize:11,fontWeight:600,color:'#1e293b'}}>{t.l}</span>
            <span style={{fontSize:9,color:'#94a3b8',lineHeight:1.2}}>{t.sub}</span>
          </div>
        ))}
      </div>

      {/* Bottom hint */}
      <div style={{fontSize:9,color:'#94a3b8',textAlign:'center',lineHeight:1.4,padding:'0 8px'}}>
        Not sure which to pick? Choose the closest match. Our AI will refine the classification automatically.
      </div>
    </div>
  );
}

function WizardDetailsUI() {
  const priorities = [
    {p:'Critical',border:'#ef4444',bg:'rgba(239,68,68,.06)',color:'#ef4444',sel:false},
    {p:'High',border:'#f59e0b',bg:'rgba(245,158,11,.07)',color:'#b45309',sel:true},
    {p:'Medium',border:'#e2e8f0',bg:'#fff',color:'#64748b',sel:false},
    {p:'Low',border:'#e2e8f0',bg:'#fff',color:'#64748b',sel:false}
  ];
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:16,gap:10}}>
      {/* Progress bar: Step 2 active */}
      <div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <StepDot n={1} done/><div style={{flex:1,height:2,background:'#10b981',borderRadius:2}}/><StepDot n={2} active/><div style={{flex:1,height:0,borderTop:'2px dashed #cbd5e1'}}/><StepDot n={3}/>
        </div>
        <div style={{display:'flex',justifyContent:'space-between',marginTop:4,padding:'0 2px'}}>
          {['Type ✓','Details','Review'].map((lbl,i)=>(
            <span key={i} style={{fontSize:8,fontWeight:i===1?600:400,color:i===0?'#10b981':i===1?'#3b82f6':'#94a3b8',fontFamily:"'IBM Plex Mono',monospace",width:36,textAlign:'center'}}>{lbl}</span>
          ))}
        </div>
      </div>

      {/* Selected type chip with Change */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'6px 10px',background:'rgba(37,99,235,.06)',border:'1px solid rgba(37,99,235,.18)',borderRadius:6}}>
        <div style={{display:'flex',alignItems:'center',gap:6,fontSize:11}}><span>📋</span><strong>Contract Dispute</strong></div>
        <span style={{fontSize:9,color:'#3b82f6',cursor:'pointer',fontWeight:500}}>Change</span>
      </div>

      {/* Subject */}
      <Field label="Subject *" value="Contract Amendment -- Clause 7.3"/>

      {/* Description with helper, focus border, char counter, AI indicator */}
      <div>
        <div style={{fontSize:9,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.06em',marginBottom:2,fontFamily:"'IBM Plex Mono',monospace"}}>Description *</div>
        <div style={{fontSize:8,color:'#64748b',marginBottom:4,lineHeight:1.3}}>This is what the AI reads to understand your issue. Be specific — include clause numbers, dates, amounts, order IDs.</div>
        <div style={{background:'#fff',border:'1px solid #3b82f6',borderRadius:6,padding:'8px 10px',fontSize:11,color:'#1e293b',minHeight:52,boxShadow:'0 0 0 3px rgba(37,99,235,.06)',lineHeight:1.5}}>We need urgent clarification on the amendment to Clause 7.3 regarding penalty calculations.</div>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginTop:3}}>
          <span style={{fontSize:8,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace"}}>🤖 QueryAnalysisAgent will analyze this text</span>
          <span style={{fontSize:9,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace"}}>89/1000</span>
        </div>
      </div>

      {/* Priority + Reference side by side */}
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
        <div>
          <div style={{fontSize:9,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.06em',marginBottom:4,fontFamily:"'IBM Plex Mono',monospace"}}>Priority</div>
          <div style={{display:'flex',gap:4}}>
            {priorities.map(t=>(
              <div key={t.p} style={{padding:'5px 8px',borderRadius:14,fontSize:10,fontWeight:t.sel?600:500,border:`1.5px solid ${t.sel?t.border:'#e2e8f0'}`,background:t.sel?t.bg:'#fff',color:t.sel?t.color:'#64748b',cursor:'pointer',boxShadow:t.sel?`0 0 0 2px ${t.border}33`:'none'}}>{t.p}</div>
            ))}
          </div>
          <div style={{fontSize:8,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace",marginTop:4}}>⏱️ Expected response: 4 hours</div>
        </div>
        <div>
          <Field label="Reference (optional)" value="PO-2025-001"/>
          <div style={{fontSize:8,color:'#94a3b8',marginTop:2}}>Helps us link to your Salesforce records</div>
        </div>
      </div>
    </div>
  );
}

function WizardReviewUI() {
  const rows = [
    ['Query Type','📋 Contract Dispute'],
    ['Subject','Contract Amendment -- Clause 7.3'],
    ['Description','We need urgent clarification on the amendment to Clause 7.3 regarding pe...'],
    ['Priority','High'],
    ['Reference','PO-2025-001'],
    ['Assigned to','Auto (QueryAnalysisAgent)'],
    ['Company','Infosys Ltd']
  ];
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:16,gap:10}}>
      {/* Progress bar: Step 3 active */}
      <div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <StepDot n={1} done/><div style={{flex:1,height:2,background:'#10b981',borderRadius:2}}/><StepDot n={2} done/><div style={{flex:1,height:2,background:'#10b981',borderRadius:2}}/><StepDot n={3} active/>
        </div>
        <div style={{display:'flex',justifyContent:'space-between',marginTop:4,padding:'0 2px'}}>
          {['Type ✓','Details ✓','Review'].map((lbl,i)=>(
            <span key={i} style={{fontSize:8,fontWeight:i===2?600:400,color:i<2?'#10b981':'#3b82f6',fontFamily:"'IBM Plex Mono',monospace",width:36,textAlign:'center'}}>{lbl}</span>
          ))}
        </div>
      </div>

      {/* Title + subtitle */}
      <div>
        <div style={{fontSize:14,fontWeight:700,color:'#1e293b'}}>Review & Submit</div>
        <div style={{fontSize:10,color:'#64748b',marginTop:2}}>Double-check everything below. You can go back to make changes.</div>
      </div>

      {/* Summary card with alternating rows */}
      <div style={{background:'#fff',borderRadius:10,border:'1px solid #e2e8f0',overflow:'hidden'}}>
        {rows.map(([k,v],i)=>(
          <div key={i} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'7px 12px',borderBottom:i<rows.length-1?'1px solid #f1f5f9':'none',fontSize:11,background:i%2===0?'#fff':'#fafbfc'}}>
            <span style={{color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace",fontSize:9,flexShrink:0}}>{k}</span>
            <span style={{color:'#1e293b',fontWeight:500,textAlign:'right',maxWidth:'65%',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
              {k==='Priority'?<Badge c="#b45309" bg="rgba(245,158,11,.07)" bc="#f59e0b">{v}</Badge>:v}
            </span>
          </div>
        ))}
      </div>

      {/* SLA estimate card */}
      <div style={{background:'rgba(16,185,129,.06)',border:'1px solid rgba(16,185,129,.2)',borderRadius:8,padding:'10px 14px',display:'flex',alignItems:'center',gap:10}}>
        <span style={{fontSize:18}}>⏱️</span>
        <div>
          <div style={{fontSize:12,fontWeight:700,color:'#059669'}}>Expected SLA: 4 hours</div>
          <div style={{fontSize:9,color:'#64748b',marginTop:2}}>Auto-analyzed and routed to AI pipeline immediately after submission.</div>
        </div>
      </div>

      {/* Action buttons */}
      <div style={{display:'flex',justifyContent:'space-between',marginTop:'auto'}}>
        <div style={{padding:'8px 14px',borderRadius:6,fontSize:11,color:'#64748b',border:'1px solid #e2e8f0',background:'#fff',cursor:'pointer',fontWeight:500}}>← Back</div>
        <div style={{padding:'10px 18px',borderRadius:8,fontSize:12,color:'#fff',background:'linear-gradient(135deg,#3b82f6,#1d4ed8)',fontWeight:700,cursor:'pointer',boxShadow:'0 2px 8px rgba(37,99,235,.25)'}}>Submit Query →</div>
      </div>

      {/* Post-submit reassurance */}
      <div style={{fontSize:8,color:'#94a3b8',textAlign:'center',lineHeight:1.4,fontFamily:"'IBM Plex Mono',monospace"}}>After submission, your query enters the AI pipeline. You will get a query ID and can track progress in real-time.</div>
    </div>
  );
}

function SubmittingUI() {
  const [msg, setMsg] = useState(0);
  const msgs = ['Connecting to VQMS pipeline','Running QueryAnalysisAgent...','Scoring priority & category...','Routing to ResolutionAgent...','Generating query ID...'];
  useEffect(() => { const t = setInterval(() => setMsg(p => Math.min(p+1, msgs.length-1)), 900); return () => clearInterval(t); }, []);
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:24,gap:16}}>
      <div style={{width:44,height:44,border:'3px solid #e2e8f0',borderTopColor:'#3b82f6',borderRadius:'50%',animation:'spin .7s linear infinite'}}/>
      <div style={{fontSize:15,fontWeight:700,color:'#1e293b'}}>Submitting your query...</div>
      <div style={{width:'100%',maxWidth:260}}>
        {msgs.map((m,i)=>{
          const done = i < msg;
          const active = i === msg;
          return (
            <div key={i} style={{display:'flex',alignItems:'center',gap:8,padding:'5px 0',borderBottom:i<msgs.length-1?'1px solid #f1f5f9':'none',fontSize:10}}>
              {done
                ? <span style={{color:'#10b981',fontSize:12,fontWeight:700,flexShrink:0,width:14,textAlign:'center'}}>✓</span>
                : <div style={{width:7,height:7,borderRadius:'50%',background:active?'#3b82f6':'#d1d5db',flexShrink:0,marginLeft:3.5,animation:active?'pulse 1.5s infinite':'none'}}/>
              }
              <span style={{flex:1,color:done?'#10b981':active?'#1e293b':'#94a3b8',fontWeight:done||active?500:400,fontFamily:"'IBM Plex Mono',monospace",transition:'color .3s'}}>{m}</span>
            </div>
          );
        })}
      </div>
      <div style={{fontSize:10,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace"}}>This usually takes a few seconds.</div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
    </div>
  );
}

function SuccessUI() {
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',padding:20,gap:12}}>
      <div style={{width:56,height:56,borderRadius:'50%',background:'rgba(16,185,129,.1)',border:'2px solid rgba(16,185,129,.3)',display:'flex',alignItems:'center',justifyContent:'center'}}>
        <svg width="28" height="28" viewBox="0 0 40 40" fill="none"><circle cx="20" cy="20" r="16" stroke="#10b981" strokeWidth="2.5"/><path d="M13 20l5 5 9-10" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
      </div>
      <div style={{fontSize:15,fontWeight:700,color:'#1e293b',textAlign:'center'}}>Query Submitted!</div>
      <div style={{fontFamily:'monospace',fontSize:12,fontWeight:700,color:'#3b82f6',background:'rgba(37,99,235,.06)',border:'1px solid rgba(37,99,235,.18)',padding:'6px 16px',borderRadius:6}}>VQ-2025-0042</div>
      <div style={{background:'#fff',borderRadius:8,border:'1px solid #e2e8f0',padding:'10px 14px',width:'100%',maxWidth:280}}>
        <div style={{fontSize:8,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.08em',fontFamily:'monospace',marginBottom:8}}>What happens next</div>
        {[{c:'#10b981',l:'Query received & logged',t:'Done'},{c:'#3b82f6',l:'QueryAnalysisAgent classifying',t:'In progress...'},{c:'#9ca3af',l:'RoutingService routing',t:'Pending'},{c:'#9ca3af',l:'ResolutionAgent drafting',t:'Pending'},{c:'#9ca3af',l:'Response sent',t:'Pending'}].map((r,i)=>(
          <div key={i} style={{display:'flex',alignItems:'center',gap:8,padding:'5px 0',borderBottom:i<4?'1px solid #f1f5f9':'none',fontSize:10}}>
            <div style={{width:7,height:7,borderRadius:'50%',background:r.c,flexShrink:0}}/>
            <span style={{flex:1,color:'#1e293b',fontWeight:500}}>{r.l}</span>
            <span style={{fontFamily:'monospace',fontSize:8,color:'#94a3b8'}}>{r.t}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AgentUI({ name, status, color, progress, result }) {
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:16,gap:10}}>
      <div style={{display:'flex',alignItems:'center',gap:8}}>
        <div style={{width:8,height:8,borderRadius:'50%',background:color,animation:status==='running'?'pulse 1.5s infinite':'none',boxShadow:status==='running'?`0 0 0 4px ${color}33`:undefined}}/>
        <div style={{fontSize:13,fontWeight:600,color:'#1e293b'}}>{name}</div>
        <span style={{marginLeft:'auto',fontSize:9,fontFamily:'monospace',padding:'2px 8px',borderRadius:8,background:status==='running'?'rgba(37,99,235,.08)':status==='done'?'rgba(16,185,129,.08)':'#f1f5f9',color:status==='running'?'#3b82f6':status==='done'?'#059669':'#94a3b8',border:`1px solid ${status==='running'?'rgba(37,99,235,.2)':status==='done'?'rgba(16,185,129,.2)':'#e2e8f0'}`}}>{status==='running'?'Processing...':status==='done'?'Complete':'Pending'}</span>
      </div>
      {progress && <div style={{height:4,background:'#e2e8f0',borderRadius:2,overflow:'hidden'}}><div style={{height:'100%',background:`linear-gradient(90deg,${color},${color}88)`,borderRadius:2,width:progress,transition:'width 1s'}}/></div>}
      {result && (
        <div style={{background:'#fff',borderRadius:8,border:'1px solid #e2e8f0',padding:12,flex:1,overflow:'auto'}}>
          <div style={{fontSize:8,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.07em',fontFamily:'monospace',marginBottom:6}}>Output</div>
          <pre style={{fontSize:9,fontFamily:'monospace',color:'#334155',lineHeight:1.6,whiteSpace:'pre-wrap',margin:0}}>{result}</pre>
        </div>
      )}
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
    </div>
  );
}

function DeliveredUI() {
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:14,gap:8}}>
      <div style={{display:'flex',alignItems:'flex-start',gap:8}}>
        <div><div style={{fontFamily:'monospace',fontSize:9,color:'#94a3b8'}}>VQ-2025-0042</div><div style={{fontSize:12,fontWeight:600,color:'#1e293b',marginTop:2}}>Contract Amendment -- Clause 7.3</div></div>
      </div>
      <div style={{display:'flex',gap:4}}>
        <Badge c="#6d28d9" bg="rgba(124,58,237,.08)" bc="rgba(124,58,237,.18)">In Progress</Badge>
        <Badge c="#b45309" bg="rgba(245,158,11,.08)" bc="rgba(245,158,11,.2)">High</Badge>
      </div>
      <div style={{fontSize:8,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.08em',fontFamily:'monospace'}}>AI Resolution Draft</div>
      <div style={{background:'linear-gradient(135deg,rgba(16,185,129,.06),rgba(37,99,235,.04))',border:'1px solid rgba(16,185,129,.18)',borderRadius:6,padding:'8px 10px',flex:1}}>
        <div style={{display:'flex',alignItems:'center',gap:4,fontSize:9,fontFamily:'monospace',color:'#059669',fontWeight:600,marginBottom:6}}>
          <svg width="8" height="8" viewBox="0 0 20 20" fill="#059669"><circle cx="10" cy="10" r="8"/><path d="M7 10l2 2 4-4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round"/></svg>
          Bedrock / ResolutionAgent / 94%
        </div>
        <div style={{fontSize:10,lineHeight:1.6,color:'#1e293b'}}>Based on KB article #847 (94% match), Clause 7.3 refers to the standard penalty schedule (Q1 2024). Amendment has precedent in 14 similar cases. Recommended: Accept with rider referencing Exhibit C, Section 2.</div>
      </div>
      <div style={{fontSize:8,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.08em',fontFamily:'monospace'}}>Ticket</div>
      <div style={{background:'#fff',borderRadius:6,border:'1px solid #e2e8f0',padding:'6px 10px',fontSize:10,display:'flex',justifyContent:'space-between'}}>
        <span style={{fontFamily:'monospace',color:'#3b82f6',fontWeight:600}}>INC0012345</span>
        <span style={{color:'#64748b'}}>Procurement Team</span>
      </div>
    </div>
  );
}

function SLAUI() {
  return (
    <div style={{background:'#f8fafc',borderRadius:12,overflow:'hidden',border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:16,gap:10}}>
      <div style={{fontSize:13,fontWeight:600,color:'#1e293b'}}>SLA Monitor Active</div>
      <div style={{fontFamily:'monospace',fontSize:10,color:'#64748b'}}>INC0012345 | Gold | High | 4h</div>
      <div style={{height:8,background:'#e2e8f0',borderRadius:4,overflow:'hidden',position:'relative'}}>
        <div style={{height:'100%',width:'45%',background:'linear-gradient(90deg,#10b981,#3b82f6)',borderRadius:4}}/>
        <div style={{position:'absolute',left:'70%',top:-2,bottom:-2,width:2,background:'#f59e0b'}}/>
        <div style={{position:'absolute',left:'85%',top:-2,bottom:-2,width:2,background:'#ef4444'}}/>
        <div style={{position:'absolute',left:'95%',top:-2,bottom:-2,width:2,background:'#dc2626'}}/>
      </div>
      <div style={{display:'flex',justifyContent:'space-between',fontSize:8,fontFamily:'monospace',color:'#94a3b8'}}>
        <span>08:14</span><span style={{color:'#f59e0b'}}>70%</span><span style={{color:'#ef4444'}}>85%</span><span style={{color:'#dc2626'}}>95%</span><span>12:14</span>
      </div>
      <div style={{flex:1,display:'flex',flexDirection:'column',gap:6,marginTop:4}}>
        {[{t:'08:14',l:'Ticket created, SLA started',c:'#10b981',done:true},{t:'11:02',l:'70% Warning -> notify resolver',c:'#f59e0b',done:false},{t:'11:38',l:'85% Escalation -> L1 manager',c:'#ef4444',done:false},{t:'12:02',l:'95% Critical -> L2 senior',c:'#dc2626',done:false},{t:'12:14',l:'100% DEADLINE',c:'#7f1d1d',done:false}].map((e,i)=>(
          <div key={i} style={{display:'flex',alignItems:'center',gap:8,fontSize:10,opacity:e.done?1:.5}}>
            <div style={{width:7,height:7,borderRadius:'50%',background:e.c,flexShrink:0}}/>
            <span style={{fontFamily:'monospace',fontSize:9,color:'#94a3b8',minWidth:36}}>{e.t}</span>
            <span style={{color:'#1e293b',fontWeight:e.done?500:400}}>{e.l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function E2EOverviewUI() {
  const pipelineSteps = [
    { n:1,  name:'Login',               time:'< 800ms',     cost:'$0.00',    sys:'Cognito',            cat:'browser' },
    { n:2,  name:'Portal Loads',        time:'< 400ms',     cost:'$0.00',    sys:'Redis \u2192 PG',    cat:'backend' },
    { n:3,  name:'Wizard: Type',        time:'instant',      cost:'$0.00',    sys:'Browser',            cat:'browser' },
    { n:4,  name:'Wizard: Details',     time:'instant',      cost:'$0.00',    sys:'Browser',            cat:'browser' },
    { n:5,  name:'Wizard: Review',      time:'instant',      cost:'$0.00',    sys:'Browser',            cat:'browser' },
    { n:6,  name:'Submit',              time:'< 500ms',      cost:'$0.00',    sys:'API \u2192 PG \u2192 SQS',  cat:'backend' },
    { n:7,  name:'Pipeline Init',       time:'600ms',        cost:'$0.00',    sys:'SQS \u2192 Salesforce',     cat:'backend' },
    { n:8,  name:'QueryAnalysis',       time:'2-4s',         cost:'~$0.012',  sys:'Bedrock Claude \ud83e\udd16',cat:'llm' },
    { n:9,  name:'Routing + KB',        time:'< 200ms',      cost:'~$0.0001', sys:'Rules + pgvector',   cat:'backend' },
    { n:10, name:'Resolution',          time:'3-6s',         cost:'~$0.021',  sys:'Bedrock Claude \ud83e\udd16',cat:'llm' },
    { n:11, name:'QualityGate',         time:'< 200ms',      cost:'$0.00',    sys:'Comprehend',         cat:'backend' },
    { n:12, name:'Ticket + Email',      time:'~2s',          cost:'$0.00',    sys:'ServiceNow + Graph', cat:'backend' },
    { n:13, name:'SLA Monitor',         time:'ongoing',      cost:'$0.00',    sys:'Step Functions',     cat:'backend' }
  ];
  const accent = { browser:'#94a3b8', backend:'#3b82f6', llm:'#f59e0b' };
  return (
    <div style={{background:'#f8fafc',borderRadius:12,border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:14,gap:8}}>
      <div style={{textAlign:'center',padding:'4px 0'}}>
        <div style={{fontSize:13,fontWeight:700,color:'#1e293b'}}>Complete Pipeline: Login \u2192 Resolution</div>
        <div style={{fontSize:10,color:'#64748b',marginTop:2}}>All 13 steps in one view</div>
      </div>

      <div style={{flex:1,overflow:'auto',display:'flex',flexDirection:'column',gap:2}}>
        {pipelineSteps.map((s, i) => (
          <div key={s.n}>
            {i === 6 && (
              <div style={{borderTop:'2px dashed #cbd5e1',margin:'6px 0',position:'relative',height:0,background:'transparent'}}>
                <span style={{position:'absolute',top:-7,left:'50%',transform:'translateX(-50%)',background:'#f8fafc',padding:'0 8px',fontSize:7,fontWeight:600,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace",whiteSpace:'nowrap',textTransform:'uppercase',letterSpacing:'0.5px'}}>async boundary \u2014 vendor does not wait</span>
              </div>
            )}
            <div style={{display:'flex',alignItems:'center',gap:6,padding:'3px 6px',borderRadius:6,background:i%2===0?'#fff':'transparent'}}>
              <div style={{width:3,height:20,borderRadius:2,background:accent[s.cat],flexShrink:0}}/>
              <div style={{width:18,height:18,borderRadius:'50%',display:'flex',alignItems:'center',justifyContent:'center',fontSize:7,fontWeight:700,fontFamily:"'IBM Plex Mono',monospace",background:accent[s.cat]+'15',color:accent[s.cat],border:'1.5px solid '+accent[s.cat]+'40',flexShrink:0}}>{s.n}</div>
              <div style={{flex:1,fontSize:9,fontWeight:500,color:'#1e293b',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s.name}</div>
              <span style={{fontSize:7,fontFamily:"'IBM Plex Mono',monospace",color:'#64748b',flexShrink:0,minWidth:40,textAlign:'right'}}>{s.time}</span>
              <span style={{fontSize:7,fontFamily:"'IBM Plex Mono',monospace",color:'#64748b',flexShrink:0,minWidth:44,textAlign:'right'}}>{s.cost}</span>
              <span style={{fontSize:6,fontFamily:"'IBM Plex Mono',monospace",padding:'1px 4px',borderRadius:3,background:accent[s.cat]+'12',color:accent[s.cat],border:'1px solid '+accent[s.cat]+'25',flexShrink:0,maxWidth:90,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s.sys}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:6,padding:'8px 0',borderTop:'1px solid #e2e8f0'}}>
        {[
          { val:'~10s', label:'Backend Time', color:'#3b82f6' },
          { val:'~$0.033', label:'Total Cost', color:'#10b981' },
          { val:'2', label:'LLM Calls', color:'#f59e0b' },
          { val:'~400ms', label:'Vendor Wait', color:'#6366f1' }
        ].map((m,i) => (
          <div key={i} style={{textAlign:'center',padding:5,background:'#fff',borderRadius:6,border:'1px solid #e2e8f0'}}>
            <div style={{fontSize:13,fontWeight:700,color:m.color}}>{m.val}</div>
            <div style={{fontSize:6,color:'#94a3b8',fontFamily:"'IBM Plex Mono',monospace",textTransform:'uppercase',letterSpacing:'0.3px',marginTop:1}}>{m.label}</div>
          </div>
        ))}
      </div>

      <div style={{display:'flex',gap:12,justifyContent:'center',padding:'2px 0'}}>
        {[
          { color:'#94a3b8', label:'Browser' },
          { color:'#3b82f6', label:'Backend' },
          { color:'#f59e0b', label:'LLM ($)' }
        ].map((l,i) => (
          <div key={i} style={{display:'flex',alignItems:'center',gap:3}}>
            <div style={{width:6,height:6,borderRadius:'50%',background:l.color}}/>
            <span style={{fontSize:7,color:'#64748b',fontFamily:"'IBM Plex Mono',monospace"}}>{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepDot({ n, active, done }) {
  return (
    <div style={{width:24,height:24,borderRadius:'50%',display:'flex',alignItems:'center',justifyContent:'center',fontSize:10,fontWeight:700,fontFamily:'monospace',flexShrink:0,border:`2px solid ${done?'#10b981':active?'#3b82f6':'#e2e8f0'}`,background:done?'#10b981':active?'#3b82f6':'#fff',color:done||active?'#fff':'#94a3b8',boxShadow:active?'0 0 0 3px rgba(37,99,235,.15)':'none'}}>
      {done?'✓':n}
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <div style={{fontSize:9,color:'#94a3b8',textTransform:'uppercase',letterSpacing:'.06em',marginBottom:3,fontFamily:'monospace'}}>{label}</div>
      <div style={{background:'#fff',border:'1px solid #e2e8f0',borderRadius:6,padding:'8px 10px',fontSize:11,color:'#1e293b'}}>{value}</div>
    </div>
  );
}

function Badge({ c, bg, bc, children }) {
  return <span style={{fontSize:8,fontFamily:'monospace',padding:'2px 6px',borderRadius:8,background:bg,color:c,border:`1px solid ${bc}`}}>{children}</span>;
}

const UI_MAP = {
  login: LoginUI,
  dashboard: DashboardUI,
  wizard1: WizardTypeUI,
  wizard2: WizardDetailsUI,
  wizard3: WizardReviewUI,
  submitting: SubmittingUI,
  success: SuccessUI,
  analyzing: () => <AgentUI name="QueryAnalysisAgent" status="done" color="#3b82f6" progress="100%" result={`intent: "CONTRACT_AMENDMENT"\nentities: ["Clause 7.3",\n  "penalty calculations",\n  "PO-2025-001"]\nurgency: "HIGH"\nsentiment: "URGENT"\nconfidence: 0.92\nmulti_issue: false\ncategory: "contracts"`}/>,
  routing: () => (
    <div style={{background:'#f8fafc',borderRadius:12,border:'1px solid #e2e8f0',height:'100%',display:'flex',flexDirection:'column',padding:12,gap:8}}>
      <AgentUI name="RoutingService" status="done" color="#7c3aed" result={`path: FULL_AUTOMATION\ngroup: "Procurement Team"\nsla: 4 hours\nconfidence: 0.92 >= 0.85`}/>
      <AgentUI name="KBSearchService" status="done" color="#f59e0b" result={`#847 Contract Amend v3.2  94%\n#412 Penalty Calc Policy  81%\n#291 Amendment Precedent  72%`}/>
    </div>
  ),
  drafting: () => <AgentUI name="ResolutionAgent" status="done" color="#10b981" progress="100%" result={`subject: "RE: Contract Amendment\n  -- Clause 7.3"\n\nbody: "Based on KB article #847\n(94% match), Clause 7.3 refers\nto the standard penalty schedule\n(Q1 2024). Amendment has\nprecedent in 14 similar cases\n-- all resolved with 2.5%/month\npenalty cap.\n\nRecommended: Accept with rider\nreferencing Exhibit C, Section 2."\n\nconfidence: 0.94\nsources: ["KB#847", "KB#412"]`}/>,
  validating: () => <AgentUI name="QualityGateAgent" status="done" color="#059669" progress="100%" result={`PHASE 1 (deterministic):\n  [PASS] Ticket # format\n  [PASS] SLA wording\n  [PASS] Required sections\n  [PASS] Restricted terms\n  [PASS] Response length: 147w\n  [PASS] Source citations: 2\n\nPHASE 2 (conditional):\n  PII scan: NO PII detected\n  Tone check: SKIPPED\n\n████████ RESULT: PASS ████████`}/>,
  delivered: DeliveredUI,
  sla: SLAUI,
  e2eOverview: E2EOverviewUI,
  fullascii: () => null
};

const PHASES = [
  { label:'AUTHENTICATION', indices:[0] },
  { label:'PORTAL',         indices:[1] },
  { label:'QUERY WIZARD',   indices:[2,3,4] },
  { label:'SUBMISSION',     indices:[5] },
  { label:'AI PIPELINE',    indices:[6,7,8,9,10] },
  { label:'DELIVERY',       indices:[11] },
  { label:'MONITORING',     indices:[12] },
  { label:'OVERVIEW',       indices:[13] },
  { label:'DEEP DIVE',     indices:[14] }
];

const dotColor = (stepId) => {
  if ([3,4,5].includes(stepId)) return '#64748b';
  if ([8,10].includes(stepId)) return '#10b981';
  if (stepId === 12) return '#7c3aed';
  if (stepId === 13) return '#f59e0b';
  return '#3b82f6';
};

export default function App() {
  const [step, setStep] = useState(0);
  const asciiRef = useRef(null);
  const activeStepRef = useRef(null);
  const [narrow, setNarrow] = useState(typeof window !== 'undefined' ? window.innerWidth < 900 : false);
  const current = STEPS[step];
  const UIComponent = UI_MAP[current.ui];
  const isFullWidth = current.ui === 'fullascii';

  useEffect(() => {
    if (asciiRef.current) { asciiRef.current.scrollTop = 0; asciiRef.current.scrollLeft = 0; }
  }, [step]);

  useEffect(() => {
    if (activeStepRef.current) {
      activeStepRef.current.scrollIntoView({ behavior:'smooth', block:'nearest' });
    }
  }, [step]);

  useEffect(() => {
    const handler = () => setNarrow(window.innerWidth < 900);
    handler();
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
      if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault();
        setStep(s => Math.max(0, s - 1));
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault();
        setStep(s => Math.min(STEPS.length - 1, s + 1));
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const fontsLink = <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet"/>;

  const badgeRow = (
    <div style={{marginLeft:'auto',display:'flex',gap:8,alignItems:'center'}}>
      {current.llm && <span style={{fontSize:8,fontFamily:"'IBM Plex Mono',monospace",padding:'3px 8px',borderRadius:6,background:'rgba(239,68,68,.15)',color:'#fca5a5',border:'1px solid rgba(239,68,68,.25)'}}>LLM CALL</span>}
      <span style={{fontSize:8,fontFamily:"'IBM Plex Mono',monospace",padding:'3px 8px',borderRadius:6,background:'rgba(37,99,235,.15)',color:'#93c5fd',border:'1px solid rgba(37,99,235,.25)'}}>{current.time}</span>
      <span style={{fontSize:8,fontFamily:"'IBM Plex Mono',monospace",padding:'3px 8px',borderRadius:6,background:'rgba(16,185,129,.12)',color:'#6ee7b7',border:'1px solid rgba(16,185,129,.2)'}}>{current.cost}</span>
    </div>
  );

  const splitView = (
    <div style={{flex:1,display:'grid',gridTemplateColumns:isFullWidth ? '1fr' : '1fr 1fr',overflow:'hidden',minHeight:0}}>
      {/* Left: ASCII */}
      <div style={{borderRight:isFullWidth ? 'none' : '1px solid #1e293b',display:'flex',flexDirection:'column',overflow:'hidden'}}>
        <div style={{padding:'10px 16px',borderBottom:'1px solid #1e293b',display:'flex',alignItems:'center',gap:8,flexShrink:0}}>
          <div style={{width:10,height:10,borderRadius:'50%',background:'#ef4444'}}/>
          <div style={{width:10,height:10,borderRadius:'50%',background:'#f59e0b'}}/>
          <div style={{width:10,height:10,borderRadius:'50%',background:'#10b981'}}/>
          <span style={{fontSize:10,color:'#64748b',fontFamily:"'IBM Plex Mono',monospace",marginLeft:8}}>{isFullWidth ? 'backend_deep_dive.ascii \u2014 full width' : 'backend_flow.ascii'}</span>
        </div>
        <div style={{padding:'8px 16px',borderBottom:'1px solid #1e293b',flexShrink:0}}>
          <div style={{fontSize:12,fontWeight:600,color:'#f1f5f9'}}>Step {current.id}: {current.title}</div>
          <div style={{fontSize:10,color:'#64748b',marginTop:2}}>{current.subtitle}</div>
        </div>
        <div ref={asciiRef} style={{flex:1,overflow:'auto',padding:16,scrollbarWidth:'thin',scrollbarColor:'#334155 transparent'}}>
          {current.wideAscii && <div style={{position:'sticky',top:0,textAlign:'right',fontSize:9,fontFamily:"'IBM Plex Mono',monospace",color:'#475569',padding:'0 0 8px 0'}}>← scroll horizontally →</div>}
          <pre style={{fontSize:10,fontFamily:"'IBM Plex Mono',monospace",color:'#94a3b8',lineHeight:1.55,margin:0,whiteSpace:'pre',tabSize:2}}>{current.ascii}</pre>
        </div>
      </div>

      {/* Right: UI (hidden in full-width mode) */}
      {!isFullWidth && (
      <div style={{display:'flex',flexDirection:'column',overflow:'hidden'}}>
        <div style={{padding:'10px 16px',borderBottom:'1px solid #1e293b',display:'flex',alignItems:'center',gap:8,flexShrink:0}}>
          <div style={{width:10,height:10,borderRadius:'50%',background:'#3b82f6'}}/>
          <span style={{fontSize:10,color:'#64748b',fontFamily:"'IBM Plex Mono',monospace"}}>vendor_ui_preview.jsx</span>
          <span style={{marginLeft:'auto',fontSize:8,color:'#475569',fontFamily:"'IBM Plex Mono',monospace"}}>What the vendor sees</span>
        </div>
        <div style={{flex:1,overflow:'auto',padding:16}}>
          <UIComponent key={step}/>
        </div>
      </div>
      )}
    </div>
  );

  if (narrow) {
    return (
      <div style={{height:'100vh',display:'flex',flexDirection:'column',background:'#0c0f1a',fontFamily:"'IBM Plex Sans',system-ui,sans-serif",color:'#e2e8f0',overflow:'hidden'}}>
        {fontsLink}
        {/* Header */}
        <div style={{padding:'12px 20px',borderBottom:'1px solid #1e293b',display:'flex',alignItems:'center',gap:14,flexShrink:0}}>
          <div style={{width:32,height:32,borderRadius:8,background:'linear-gradient(135deg,#3b82f6,#6366f1)',display:'flex',alignItems:'center',justifyContent:'center'}}>
            <span style={{color:'#fff',fontSize:14,fontWeight:700}}>V</span>
          </div>
          <div>
            <div style={{fontSize:13,fontWeight:700,color:'#f1f5f9'}}>VQMS Technical Flow Explorer</div>
            <div style={{fontSize:9,color:'#64748b',fontFamily:"'IBM Plex Mono',monospace"}}>ASCII + UI side-by-side | Step {current.id} of {STEPS.length}</div>
          </div>
          {badgeRow}
        </div>
        {/* Step Navigator (horizontal) */}
        <div style={{padding:'8px 20px',borderBottom:'1px solid #1e293b',display:'flex',gap:4,overflowX:'auto',flexShrink:0,scrollbarWidth:'none'}}>
          {STEPS.map((s, i) => (
            <button key={i} onClick={() => setStep(i)} style={{padding:'6px 12px',borderRadius:6,border:`1px solid ${i===step?'#3b82f6':'#1e293b'}`,background:i===step?'rgba(37,99,235,.15)':'transparent',color:i===step?'#93c5fd':'#64748b',fontSize:10,fontFamily:"'IBM Plex Mono',monospace",cursor:'pointer',whiteSpace:'nowrap',fontWeight:i===step?600:400,transition:'all .15s',flexShrink:0}}>
              {s.id}. {s.title}
            </button>
          ))}
        </div>
        {splitView}
        {/* Bottom Nav */}
        <div style={{padding:'10px 20px',borderTop:'1px solid #1e293b',display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
          <button onClick={() => setStep(Math.max(0,step-1))} disabled={step===0} style={{padding:'7px 16px',borderRadius:6,border:'1px solid #1e293b',background:'transparent',color:step===0?'#334155':'#94a3b8',fontSize:11,fontFamily:"'IBM Plex Mono',monospace",cursor:step===0?'default':'pointer'}}>Prev</button>
          <div style={{flex:1,display:'flex',gap:3,justifyContent:'center'}}>
            {STEPS.map((_,i) => (
              <div key={i} onClick={() => setStep(i)} style={{width:i===step?20:6,height:6,borderRadius:3,background:i===step?'#3b82f6':i<step?'#1e4a8a':'#1e293b',cursor:'pointer',transition:'all .2s'}}/>
            ))}
          </div>
          <button onClick={() => setStep(Math.min(STEPS.length-1,step+1))} disabled={step===STEPS.length-1} style={{padding:'7px 16px',borderRadius:6,border:'none',background:step===STEPS.length-1?'#1e293b':'linear-gradient(135deg,#3b82f6,#6366f1)',color:step===STEPS.length-1?'#334155':'#fff',fontSize:11,fontFamily:"'IBM Plex Mono',monospace",fontWeight:600,cursor:step===STEPS.length-1?'default':'pointer'}}>Next</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{height:'100vh',display:'grid',gridTemplateColumns:'220px 1fr',background:'#0c0f1a',fontFamily:"'IBM Plex Sans',system-ui,sans-serif",color:'#e2e8f0',overflow:'hidden'}}>
      {fontsLink}

      {/* Sidebar */}
      <div style={{background:'#0a0d17',borderRight:'1px solid #1e293b',display:'flex',flexDirection:'column',overflow:'hidden'}}>

        {/* Sidebar Header */}
        <div style={{padding:'14px 16px',borderBottom:'1px solid #1e293b',flexShrink:0}}>
          <div style={{display:'flex',alignItems:'center',gap:10}}>
            <div style={{width:28,height:28,borderRadius:7,background:'linear-gradient(135deg,#3b82f6,#6366f1)',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
              <span style={{color:'#fff',fontSize:12,fontWeight:700}}>V</span>
            </div>
            <div>
              <div style={{fontSize:13,fontWeight:700,color:'#f1f5f9'}}>VQMS</div>
              <div style={{fontSize:9,color:'#64748b',fontFamily:"'IBM Plex Mono',monospace"}}>Flow Explorer</div>
            </div>
          </div>
          <div style={{marginTop:10,fontSize:8,color:'#475569',fontFamily:"'IBM Plex Mono',monospace",letterSpacing:'0.5px'}}>{STEPS.length} STEPS · {PHASES.length} PHASES</div>
        </div>

        {/* Step List */}
        <div style={{flex:1,overflowY:'auto',padding:'4px 0',scrollbarWidth:'thin',scrollbarColor:'#334155 #1e293b'}}>
          {PHASES.map((phase) => (
            <div key={phase.label}>
              <div style={{padding:'14px 16px 4px 16px',fontSize:8,fontFamily:"'IBM Plex Mono',monospace",color:'#475569',letterSpacing:'0.1em',textTransform:'uppercase'}}>{phase.label}</div>
              {phase.indices.map((i) => {
                const s = STEPS[i];
                const active = i === step;
                const dc = dotColor(s.id);
                return (
                  <div
                    key={i}
                    ref={active ? activeStepRef : null}
                    onClick={() => setStep(i)}
                    style={{
                      padding: active ? '8px 12px 8px 13px' : '8px 12px 8px 16px',
                      margin:'1px 4px 1px 0',
                      borderRadius: active ? '0 6px 6px 0' : '6px',
                      marginLeft: active ? 0 : 4,
                      borderLeft: active ? '3px solid #3b82f6' : '3px solid transparent',
                      background: active ? 'rgba(37,99,235,.12)' : 'transparent',
                      cursor:'pointer',
                      transition:'all .15s'
                    }}
                  >
                    <div style={{display:'flex',alignItems:'center',gap:8}}>
                      <div style={{
                        width:8,height:8,borderRadius:'50%',
                        background:dc,
                        flexShrink:0,
                        boxShadow:[8,10].includes(s.id) ? '0 0 6px rgba(16,185,129,.5)' : 'none'
                      }}/>
                      <span style={{
                        fontSize:11,
                        fontWeight: active ? 600 : 400,
                        color: active ? '#93c5fd' : '#94a3b8',
                        flex:1,
                        overflow:'hidden',
                        textOverflow:'ellipsis',
                        whiteSpace:'nowrap'
                      }}>{s.id}. {s.title}</span>
                      <span style={{fontSize:8,fontFamily:"'IBM Plex Mono',monospace",color:'#64748b',flexShrink:0}}>{s.time}</span>
                    </div>
                    {active && (
                      <div style={{marginTop:3,paddingLeft:16,display:'flex',alignItems:'center',gap:6}}>
                        {s.llm && <span style={{fontSize:7,fontFamily:"'IBM Plex Mono',monospace",color:'#fca5a5',fontWeight:600}}>★ LLM CALL</span>}
                        <span style={{fontSize:8,fontFamily:"'IBM Plex Mono',monospace",color:'#64748b',marginLeft:'auto'}}>{s.cost}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Sidebar Footer */}
        <div style={{borderTop:'1px solid #1e293b',padding:'10px 16px',flexShrink:0}}>
          <div style={{fontSize:8,fontFamily:"'IBM Plex Mono',monospace",color:'#475569',textAlign:'center',marginBottom:8}}>{STEPS.filter(s => s.llm).length} LLM calls · ~$0.033/query</div>
          <div style={{display:'flex',gap:8}}>
            <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0} style={{flex:1,padding:'6px 0',borderRadius:5,border:'1px solid #1e293b',background:'transparent',color:step === 0 ? '#334155' : '#94a3b8',fontSize:10,fontFamily:"'IBM Plex Mono',monospace",cursor:step === 0 ? 'default' : 'pointer'}}>↑ Prev</button>
            <button onClick={() => setStep(Math.min(STEPS.length - 1, step + 1))} disabled={step === STEPS.length - 1} style={{flex:1,padding:'6px 0',borderRadius:5,border:'none',background:step === STEPS.length - 1 ? '#1e293b' : 'linear-gradient(135deg,#3b82f6,#6366f1)',color:step === STEPS.length - 1 ? '#334155' : '#fff',fontSize:10,fontFamily:"'IBM Plex Mono',monospace",fontWeight:600,cursor:step === STEPS.length - 1 ? 'default' : 'pointer'}}>↓ Next</button>
          </div>
        </div>
      </div>

      {/* Main Area */}
      <div style={{display:'flex',flexDirection:'column',overflow:'hidden'}}>
        {/* Header */}
        <div style={{padding:'0 20px',height:52,borderBottom:'1px solid #1e293b',display:'flex',alignItems:'center',gap:14,flexShrink:0}}>
          <div style={{minWidth:0}}>
            <div style={{fontSize:14,fontWeight:700,color:'#f1f5f9'}}>Step {current.id}: {current.title}</div>
            <div style={{fontSize:10,color:'#64748b',fontFamily:"'IBM Plex Mono',monospace",overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{current.subtitle}</div>
          </div>
          {badgeRow}
        </div>
        {splitView}
      </div>
    </div>
  );
}

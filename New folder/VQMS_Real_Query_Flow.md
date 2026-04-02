# VQMS: One Query, End to End

What actually happens when a vendor submits a query through the VQMS portal?
This document follows one real example from click to inbox.

Not the architecture. Not the design doc. The actual data, the actual payloads,
the actual database writes, the actual AI responses. Every step.

---

## 1. Query overview

```
WHO:      Rajesh Mehta, Accounts & Finance
          TechNova Solutions Pvt. Ltd. (VN-30892)
          rajesh.mehta@technovasolutions.in

WHAT:     Payment status inquiry for Invoice #INV-2026-0451
          Amount: Rs.4,75,000.00 | PO: PO-HEX-78412
          Due date: 17 March 2026 (16 days overdue at time of query)

HOW:      VQMS portal > Invoice Issue > High priority > Submit

SYSTEM:   Classified as PAYMENT_QUERY (not INVOICE_DISPUTE -- he is
          asking where his money is, not arguing about the amount).
          Found invoice in records, matched PO, confirmed three-way
          match passed Feb 28. Generated response with payment ETA.

TIME:     Rajesh got his query ID (VQ-2026-0108) in ~400ms.
          Full backend pipeline: ~11 seconds.

COST:     ~$0.033 (two Bedrock Claude calls + one Titan embedding)

OUTCOME:  Acknowledgment email sent to Rajesh with:
          - Payment scheduled for April 5 processing run
          - Expected credit by April 10
          - Offer for expedited payment if needed
          Ticket INC0019847 created, assigned to Finance Team.
```

---

## 2. What Rajesh sees

Think of this section as a storyboard. You are sitting next to Rajesh
watching him use the portal.

### Step 1: Rajesh logs in

```
  +------------------------------------+
  |         VQMS Portal                |
  |                                    |
  |  Email: [rajesh.mehta              |
  |          @technovasolutions.in]    |
  |  Pass:  [********]                 |
  |                                    |
  |  [Sign in with Company SSO]        |
  |  ----------- or -----------        |
  |  [Sign In]                         |
  +------------------------------------+
```

Rajesh uses email + password. He gets a Cognito session scoped to
TechNova Solutions (VN-30892). He can only see TechNova's queries.
Nobody else's. The scoping comes from the JWT claims, not from any
client-side filtering.

### Step 2: Rajesh sees his dashboard

```
  +------------------------------------+
  |  Welcome back, Rajesh              |
  |  TechNova Solutions Pvt. Ltd.      |
  |                                    |
  |  +--------+ +--------+ +--------+ |
  |  |Open: 3 | |Resolvd:| |Avg:    | |
  |  |        | | 11     | | 3.1h   | |
  |  +--------+ +--------+ +--------+ |
  |                                    |
  |  Recent:                           |
  |  VQ-2026-0097 Invoice delay  Done  |
  |  VQ-2026-0091 PO mismatch   Done  |
  |  VQ-2026-0084 GST note      Done  |
  |                                    |
  |  [+ New Query]  [View All]         |
  +------------------------------------+
```

Three open queries, eleven resolved. Average resolution 3.1 hours.
The recent queries show Rajesh has been here before -- mostly
payment and invoice issues. He clicks "+ New Query."

### Step 3: Rajesh picks "Invoice Issue"

```
  +------------------------------------+
  |  What type of query is this?       |
  |                                    |
  |  [ ] Contract   [x] Invoice        |
  |  [ ] Delivery   [ ] Tech Support   |
  |  [ ] SLA        [ ] Other          |
  |                                    |
  |  [Continue ->]                     |
  +------------------------------------+
```

He picks Invoice Issue. This is about a payment inquiry, not a
contract dispute or a delivery problem.

### Step 4: Rajesh fills in the details

```
  +--------------------------------------------+
  |  Invoice Issue                     [Change] |
  |                                             |
  |  Subject:                                   |
  |  [Payment Status Inquiry -                  |
  |   Invoice #INV-2026-0451]                   |
  |                                             |
  |  Description:                               |
  |  [I am writing on behalf of TechNova        |
  |   Solutions Pvt. Ltd. (Vendor Code:         |
  |   VN-30892) to inquire about the payment    |
  |   status of the following invoice:          |
  |                                             |
  |   Invoice Number: INV-2026-0451             |
  |   Invoice Date: 15th February 2026          |
  |   Amount: Rs.4,75,000.00                    |
  |   Purchase Order: PO-HEX-78412             |
  |   Due Date: 17th March 2026                 |
  |                                             |
  |   As the due date has passed, we would      |
  |   appreciate an update on the expected      |
  |   payment timeline...]            478/1000  |
  |                                             |
  |  Priority:  ( )Crit (x)High ( )Med ( )Low   |
  |  Expected response: 4 hours                 |
  |                                             |
  |  Reference: [PO-HEX-78412]                  |
  |                                             |
  |  [<- Back]              [Continue ->]        |
  +--------------------------------------------+
```

He picks High because the invoice due date has already passed.
The portal shows "Expected response: 4 hours" based on the
High priority selection.

### Step 5: Rajesh reviews and submits

```
  +------------------------------------+
  |  Review & Submit                   |
  |                                    |
  |  Type:      Invoice Issue          |
  |  Subject:   Payment Status...      |
  |  Priority:  High                   |
  |  Reference: PO-HEX-78412          |
  |  Company:   TechNova Solutions     |
  |                                    |
  |  Expected SLA: 4 hours            |
  |                                    |
  |  [<- Back]     [Submit Query ->]   |
  +------------------------------------+
```

He clicks "Submit Query."

### Step 6: Rajesh sees the success screen

```
  +------------------------------------+
  |             [check]                |
  |  Query Submitted Successfully!     |
  |                                    |
  |  YOUR TRACKING NUMBER              |
  |  +------------------+             |
  |  |  VQ-2026-0108    |             |
  |  +------------------+             |
  |                                    |
  |  What happens next:                |
  |  * Query received        Done      |
  |  * AI analyzing...    In progress  |
  |  o Routing              Pending    |
  |  o Draft response       Pending    |
  |  o Response sent        Pending    |
  |                                    |
  |  Pipeline time: ~10 seconds        |
  |                                    |
  |  [View Queries] [Track This ->]    |
  +------------------------------------+
```

Rajesh got his query ID in about 400 milliseconds. The browser already
has VQ-2026-0108. The AI pipeline is running in the background now.
Rajesh can close his browser if he wants -- the system does not need
him anymore.

---

## 3. The backend journey

This is the core section. Every service, every payload, every write.

If you are debugging a query, this is what you would see in the logs.


```
===============================================================
SERVICE 1: API GATEWAY + COGNITO AUTHORIZER
===============================================================
```

Trigger: Rajesh clicks "Submit Query"

**What goes in:**

```
POST /queries
Authorization: Bearer <jwt-token>
Content-Type: application/json
{
  "type": "invoice",
  "subject": "Payment Status Inquiry - Invoice #INV-2026-0451",
  "description": "I am writing on behalf of TechNova Solutions Pvt. Ltd.
    (Vendor Code: VN-30892) to inquire about the payment status of the
    following invoice:\n\nInvoice Number: INV-2026-0451\nInvoice Date:
    15th February 2026\nAmount: Rs.4,75,000.00\nPurchase Order:
    PO-HEX-78412\nDue Date: 17th March 2026\n\nAs the due date has
    passed, we would appreciate an update on the expected payment
    timeline. Kindly let us know if any additional documentation or
    clarification is required from our end to facilitate the processing.",
  "priority": "High",
  "reference": "PO-HEX-78412"
}
```

Notice: vendor_id is not in the payload. It comes from the JWT.
Rajesh cannot fake his identity.

JWT claims extracted by Cognito:

```
vendor_id: "VN-30892"
role: "VENDOR"
scopes: ["queries.own", "kb.read", "prefs.own"]
```

**What happens:**
1. Cognito validates JWT signature + expiry
2. Checks role = VENDOR, vendor = VN-30892
3. Forwards enriched request to Query API Service

Time: ~50ms | Cost: $0.00


```
===============================================================
SERVICE 2: QUERY API SERVICE
===============================================================
```

Trigger: Enriched request from API Gateway

**Step 2.1 -- Validate payload (Pydantic: QuerySubmission)**

```
type:        "invoice"       -> valid (one of 6 types)
subject:     present         -> valid (max 200 chars)
description: present         -> valid (478 chars, max 1000)
priority:    "High"          -> valid (one of 4 levels)
reference:   "PO-HEX-78412" -> valid (optional, max 100)
```

**Step 2.2 -- Generate identifiers**

```
query_id:       VQ-2026-0108         (sequential, human-readable)
execution_id:   b2c4d6e8-...        (UUID v4, internal tracking)
correlation_id: f1a2b3c4-...        (UUID v4, cross-system linking)
```

**Step 2.3 -- Idempotency check** --> Redis

```
GET vqms:idempotency:<sha256("Payment Status Inquiry..."+desc+"VN-30892")>
Result: NOT FOUND (new query, not a duplicate)
```

**Step 2.4 -- Save to database** --> PostgreSQL

```sql
INSERT INTO workflow.case_execution (
  execution_id,    -- 'b2c4d6e8-...'
  query_id,        -- 'VQ-2026-0108'
  vendor_id,       -- 'VN-30892'
  query_type,      -- 'invoice'
  subject,         -- 'Payment Status Inquiry - Invoice #INV-2026-0451'
  description,     -- 'I am writing on behalf of TechNova...'
  priority,        -- 'High'
  reference,       -- 'PO-HEX-78412'
  status,          -- 'OPEN'
  created_at       -- '2026-04-02T08:14:00Z'
)
```

**Step 2.5 -- Set idempotency guard** --> Redis

```
SET vqms:idempotency:<sha256(...)> "VQ-2026-0108" EX 604800
```

TTL is 7 days. If Rajesh accidentally submits again this week,
the system catches it in Step 2.3 and returns VQ-2026-0108
instead of creating a duplicate.

**Step 2.6 -- Publish event** --> EventBridge

```
Bus: vqms-event-bus | Event: QueryReceived
{ query_id:"VQ-2026-0108", vendor_id:"VN-30892", priority:"High", timestamp:"2026-04-02T08:14:00Z" }
```

**Step 2.7 -- Queue for AI pipeline** --> SQS

```
Queue: vqms-query-intake-queue | DLQ: vqms-dlq (3 retries)
Payload: full query (execution_id + query_id + vendor_id + type + subject + description + priority + reference + created_at)
```

Same data as the original POST, plus execution_id and created_at.

**Step 2.8 -- Return response to Rajesh's browser**

```
HTTP 201 Created
{ "query_id":"VQ-2026-0108", "status":"Open", "sla_deadline":"2026-04-02T12:14:00Z" }
```

Writes: PostgreSQL (1), Redis (2), SQS (1), EventBridge (1)
Time: ~450ms | Cost: $0.00


```
================================================================
  ASYNC BOUNDARY
  Rajesh gets VQ-2026-0108 back here. ~400ms total.
  Everything below runs in the background.
  Rajesh does not wait.
================================================================
```


```
===============================================================
SERVICE 3: LANGGRAPH ORCHESTRATOR (SQS Consumer)
===============================================================
```

Trigger: Consumes message from vqms-query-intake-queue

**Step 3.1 -- Update status** --> PostgreSQL

```sql
UPDATE workflow.case_execution
SET status = 'ANALYZING', updated_at = NOW()
WHERE execution_id = 'b2c4d6e8-...'
```

**Step 3.2 -- Cache workflow state** --> Redis

```
SET vqms:workflow:b2c4d6e8-...
{status:"ANALYZING", query_id:"VQ-2026-0108", vendor_id:"VN-30892", step:"INIT"}
EX 86400
```

**Step 3.3 -- Load vendor profile** --> Redis, then Salesforce

```
GET vqms:vendor:VN-30892
Result: CACHE MISS (TechNova's profile expired -- last synced > 1 hour ago)
```

Cache miss, so we go to Salesforce:

```
SELECT Id, Name, Tier__c, Risk_Flags__c, Primary_Contact__c,
       Payment_Terms__c, Account_Manager__c
FROM Account
WHERE Vendor_Id__c = 'VN-30892'
```

Result:

```json
{ "vendor_id":"VN-30892", "name":"TechNova Solutions Pvt. Ltd.", "tier":"SILVER",
  "risk_flags":["OVERDUE_INVOICE_HISTORY"],
  "primary_contact":{"name":"Rajesh Mehta","email":"rajesh.mehta@technovasolutions.in","phone":"+91 98765 43210"},
  "payment_terms":"Net 30",
  "account_manager":{"name":"Anil Kapoor","email":"anil.kapoor@vqms.internal"} }
```

Two things here. TechNova is Silver tier, not Gold. And they have a risk flag:
OVERDUE_INVOICE_HISTORY -- Rajesh has asked about late payments before. The flag
gets logged for Finance but does not trigger automatic escalation.

Cache: `SET vqms:vendor:VN-30892 <json above> EX 3600`

**Step 3.4 -- Load vendor history** --> PostgreSQL

```sql
SELECT interaction_summary, resolution_summary, key_entities
FROM memory.episodic_memory
WHERE vendor_id = 'VN-30892'
ORDER BY created_at DESC LIMIT 5
```

Result: 3 prior queries in 90 days:

```
1. "Invoice INV-2026-0203 payment delay"  resolved 2026-03-15, 2.8h
2. "PO mismatch on PO-HEX-71234"         resolved 2026-03-02, 4.1h
3. "GST credit note request"             resolved 2026-02-18, 6.2h
```

Rajesh queries about payments frequently. Average resolution: 4.4 hours.

Writes: PG (1), Redis (1) | Reads: Redis (miss), Salesforce (1), PG (1)
Time: ~800ms (Salesforce round-trip adds ~200ms vs cache hit) | Cost: $0.00


```
===============================================================
SERVICE 4: QUERYANALYSISAGENT (LLM Call #1)
===============================================================
```

**Step 4.1 -- Load prompt template** --> S3

```
Bucket: vqms-knowledge-artifacts-prod
Key:    templates/query-analysis/v2.json
```

**Step 4.2 -- Build prompt**

System: "You are a query analysis agent for VQMS. Given a vendor query,
return a JSON object with: intent_classification, extracted_entities,
urgency_level, sentiment, confidence_score, multi_issue_detected,
suggested_category. Be precise. Do not invent entities."

User: query type + subject + full description + reference + vendor profile
(TechNova, Silver, OVERDUE_INVOICE_HISTORY) + recent history (3 queries).

**Step 4.3 -- Call Bedrock** --> Amazon Bedrock

```
Model:       anthropic.claude-sonnet-3.5
Temperature: 0.1
Max tokens:  500
Input:       ~1,500 tokens
Output:      ~500 tokens
```

**Step 4.4 -- Parse response**

```json
{
  "intent": "PAYMENT_QUERY",
  "entities": [
    {"type": "invoice_number", "value": "INV-2026-0451"},
    {"type": "invoice_date", "value": "2026-02-15"},
    {"type": "amount", "value": "475000", "currency": "INR"},
    {"type": "purchase_order", "value": "PO-HEX-78412"},
    {"type": "due_date", "value": "2026-03-17"},
    {"type": "vendor_code", "value": "VN-30892"},
    {"type": "vendor_name", "value": "TechNova Solutions Pvt. Ltd."},
    {"type": "contact_name", "value": "Rajesh Mehta"}
  ],
  "urgency": "HIGH",
  "sentiment": "POLITE_CONCERNED",
  "confidence": 0.96,
  "multi_issue": false,
  "suggested_category": "invoice_payment"
}
```

The intent is PAYMENT_QUERY, not INVOICE_DISPUTE. Rajesh is asking where his
money is, not arguing about the amount. This matters -- payment queries route to
Finance, disputes route to Legal.

Sentiment is POLITE_CONCERNED. Phrases like "we would appreciate" are polite, but
the overdue date creates real urgency underneath. Confidence 0.96 -- very clear
intent, structured message with all reference numbers.

**Steps 4.5-4.9 -- Save and publish**

```
S3:          prompts/b2c4d6e8-.../query-analysis.json (full audit trail)
PostgreSQL:  UPDATE case_execution SET analysis_result = '<json>'
Redis:       SET vqms:workflow:b2c4d6e8-... {status:"ANALYSIS_COMPLETE"}
PostgreSQL:  INSERT audit.action_log (ANALYSIS_COMPLETED, QueryAnalysisAgent, VQ-2026-0108)
EventBridge: AnalysisCompleted { execution_id, intent:"PAYMENT_QUERY", confidence:0.96 }
```

**Step 4.10 -- Confidence branch**

0.96 >= 0.85 threshold -> PATH: FULL_AUTOMATION. No human review needed.

Writes: S3 (1), PostgreSQL (2), Redis (1), EventBridge (1)
Time: ~3 seconds | Cost: ~$0.012


```
===============================================================
SERVICES 5+6: ROUTING + KB SEARCH (parallel)
===============================================================
```

These two run at the same time.

**RoutingService** (deterministic rules, no LLM):

```
Input:  PAYMENT_QUERY + SILVER + HIGH | confidence: 0.96 >= 0.85
Rules:  urgency CRITICAL? NO | existing ticket? NO -> FULL_AUTOMATION
Group:  Finance Team (payment queries always go to Finance, not Procurement)
SLA:    High = 4 hours, Silver modifier = none, deadline = 2026-04-02T12:14:00Z
Flag:   OVERDUE_INVOICE_HISTORY logged -- not enough to trigger escalation
```

```sql
INSERT INTO workflow.routing_decision
  (execution_id, intent, vendor_tier, urgency, resolver_group, decision_path,
   confidence_score, risk_flags, rationale)
VALUES ('b2c4d6e8-...', 'PAYMENT_QUERY', 'SILVER', 'HIGH', 'Finance Team',
  'FULL_AUTOMATION', 0.96, '["OVERDUE_INVOICE_HISTORY"]',
  'High confidence, Silver tier, payment query pattern detected')
```

Time: ~50ms | Cost: $0.00

**KBSearchService** (embedding + pgvector, no LLM):

```
Embed: "Payment Status Inquiry Invoice INV-2026-0451..." -> Titan v2 -> vector(1536)
Search: SELECT FROM memory.embedding_index WHERE category='invoice_payment' ORDER BY <=> LIMIT 5
Re-rank: recency + usage count
```

Results:

```
#1203 "Invoice Payment Status Check Procedure"       96% match
#891  "Overdue Invoice Escalation Policy"             89% match
#1456 "AP Payment Timeline by Vendor Tier"            82% match
#672  "Three-Way Match Failure Resolution"            71% match
```

Top 3 passed to ResolutionAgent. Time: ~180ms | Cost: ~$0.0001


```
===============================================================
SERVICE 7: RESOLUTIONAGENT (LLM Call #2)
===============================================================
```

**Steps 7.1-7.3 -- Load prompt, assemble context, call Bedrock**

```
Prompt: S3 templates/resolution/v3.json
Context: query + analysis (PAYMENT_QUERY, HIGH, 0.96) + KB (#1203 96%, #891 89%,
  #1456 82%) + vendor (TechNova, Silver, OVERDUE_INVOICE_HISTORY) + SLA (4h) + history
Model: claude-sonnet-3.5 | Temp: 0.3 | Max: 1000 | In: ~3,000 | Out: ~800 tokens
```

**Step 7.4 -- Parse response**

```json
{
  "subject": "RE: Payment Status Inquiry - Invoice #INV-2026-0451 [INC0019847]",
  "body": "Dear Rajesh,\n\nThank you for reaching out regarding Invoice #INV-2026-0451 (PO-HEX-78412, Rs.4,75,000.00).\n\nWe have reviewed the invoice against our records. The invoice passed three-way match verification on 28th February 2026 (PO, GRN, and invoice amounts confirmed). The payment was scheduled in our next payment run.\n\nCurrent status: Payment is approved and scheduled for processing in the next payment cycle on 5th April 2026. Expected credit to your registered bank account within 3-5 business days after processing (by 10th April 2026).\n\nIf you require an expedited payment due to cash flow requirements, please let us know and we can evaluate priority processing under our early payment program.\n\nYour ticket reference: INC0019847\nSLA commitment: Response within 4 hours\n\nBest regards,\nVQMS Finance Support\nHexaware Technologies",
  "confidence": 0.93,
  "sources_cited": ["KB#1203", "KB#891"],
  "sla_statement": "Response within 4 hours per Silver tier SLA"
}
```

Concrete answer: April 5 processing, credit by April 10. Also offers
expedited payment -- the AI anticipates the follow-up question.

**Steps 7.5-7.7 -- Save and publish**

```
PostgreSQL:  UPDATE case_execution SET response_draft = '<json>'
S3:          prompts/b2c4d6e8-.../resolution.json
EventBridge: DraftPrepared { execution_id, draft_version:1, template:"resolution/v3" }
```

Writes: PostgreSQL (1), S3 (1), Redis (1), EventBridge (1)
Time: ~4 seconds | Cost: ~$0.021


```
===============================================================
SERVICE 8: QUALITYGATEAGENT
===============================================================
```

Phase 1 -- Deterministic checks (no LLM):

```
[PASS] Ticket # format: INC\d{7} regex matches INC0019847
[PASS] SLA wording: "4 hours" matches Silver/High policy
[PASS] Required sections: greeting, status update, timeline,
       next steps, ticket reference, signature -- all present
[PASS] Restricted terms: 0 matches on blocklist
[PASS] Response length: 163 words (range 50-500)
[PASS] Source citations: 2 KB articles cited (minimum 1)
```

Phase 2 -- Conditional (runs because priority = HIGH):

```
PII scan --> AWS Comprehend DetectPiiEntities
  Scanned: draft body
  Detected in original query: phone number (+91 98765 43210)
  Detected in draft response: NONE
  The AI correctly excluded Rajesh's phone number from the
  outbound email. PASS.

Tone check via Bedrock?
  No near-miss restricted terms + sentiment is not NEGATIVE
  -> SKIP (no need to waste an LLM call)
```

Overall: PASS

**Steps 8.1-8.3 -- Save and publish**

```
S3:          audit/INC0019847/2026-04-02T08:14:08Z/validation-report.json
PostgreSQL:  INSERT audit.validation_results (execution_id, status:'PASS', pii_detected:false)
EventBridge: ValidationPassed { execution_id, validation_report_s3_key }
```

Writes: S3 (1), PostgreSQL (1), EventBridge (1)
Time: ~180ms | Cost: $0.00


```
===============================================================
SERVICE 9: TICKET OPERATIONS + RESPONSE DELIVERY
===============================================================
```

**Step 9.1 -- Check for existing ticket** --> PostgreSQL

```sql
SELECT ticket_id FROM workflow.ticket_link
WHERE correlation_id = 'f1a2b3c4-...'
Result: NONE -> create new
```

**Step 9.2 -- Create ServiceNow ticket** --> ServiceNow API

```
POST /api/now/table/incident
{
  "category": "Invoice",
  "subcategory": "Payment Status",
  "urgency": 2,
  "impact": 3,
  "assignment_group": "Finance Team",
  "short_description": "Payment Status Inquiry - Invoice #INV-2026-0451 | TechNova Solutions",
  "description": "I am writing on behalf of TechNova Solutions...",
  "caller_id": "<salesforce_contact_sys_id>",
  "correlation_id": "f1a2b3c4-..."
}

Response: { "sys_id": "xyz789abc012", "number": "INC0019847" }
```

**Steps 9.3-9.6 -- Save mappings, cache, update status**

```
PostgreSQL:  INSERT workflow.ticket_link (query:'VQ-2026-0108', ticket:'xyz789abc012',
             number:'INC0019847', status:'OPEN') -- email_message_id is null (portal, not email)
Redis:       SET vqms:ticket:xyz789abc012 {number:"INC0019847",group:"Finance Team",sla:4} EX 3600
PostgreSQL:  UPDATE case_execution SET status='RESPONDED', ticket_id='xyz789abc012'
Redis:       SET vqms:workflow:b2c4d6e8-... {status:"COMPLETE"}
```

**Step 9.7 -- Send email** --> MS Graph API

```
POST .../users/vendor-support@hexaware.com/sendMail
To: rajesh.mehta@technovasolutions.in
Subject: RE: Payment Status Inquiry - Invoice #INV-2026-0451 [INC0019847]
Body: <draft response + ticket # + SLA>
```

**Steps 9.8-9.9 -- Audit and publish**

```
PostgreSQL:  INSERT audit.action_log (EMAIL_SENT)
EventBridge: TicketCreated { INC0019847, Finance Team }
             EmailSent { rajesh.mehta@technovasolutions.in }
             QueryResolved { VQ-2026-0108, INC0019847 }
```

Writes: ServiceNow (1), PostgreSQL (3), Redis (2), EventBridge (3)
Time: ~2.5 seconds | Cost: $0.00


```
===============================================================
SERVICE 10: SLA MONITOR (Step Functions state machine)
===============================================================
```

Trigger: TicketCreated event from Service 9

**Step 10.1 -- Calculate thresholds**

```
SLA: 4 hours (Silver + High)
Created: 08:14:00 | Deadline: 12:14:00
70% mark: 08:14 + 2h48m = 11:02
85% mark: 08:14 + 3h24m = 11:38
95% mark: 08:14 + 3h48m = 12:02
```

**Step 10.2 -- Set SLA state** --> Redis

```
SET vqms:sla:xyz789abc012 {start:"08:14",target_hours:4,deadline:"12:14",elapsed_pct:0}
```

No TTL -- persists until the ticket is closed.

**Steps 10.3-10.6 -- Wait states** (but query already resolved in ~11s)

```
breach:false, actual_time:0.003 hours, escalation_level:0
```

```sql
INSERT INTO reporting.sla_metrics (ticket_id, vendor_tier, sla_target,
  actual_hours, breach, escalation_level)
VALUES ('xyz789abc012', 'SILVER', 4, 0.003, false, 0)
```

Writes: Redis (1), PG (1) | Time: background | Cost: $0.00

---

## 4. Sequence diagram

Every component as a column. Every message as an arrow. Rajesh's data throughout.

```
Rajesh  APIGw  QueryAPI  Redis  PG  S3  SQS  EB  LangGraph  Bedrock  SF  pgvec  Comprhnd  SNow  Graph  SLA
  |       |       |        |     |   |    |    |      |         |       |    |       |        |      |      |
  |-POST->|       |        |     |   |    |    |      |         |       |    |       |        |      |      |
  |       |-auth->|        |     |   |    |    |      |         |       |    |       |        |      |      |
  |       |       |-GET--->|     |   |    |    |      |         |       |    |       |        |      |      |
  |       |       |<-miss--|     |   |    |    |      |         |       |    |       |        |      |      |
  |       |       |-INSERT-|---->|   |    |    |      |         |       |    |       |        |      |      |
  |       |       |-SET--->|     |   |    |    |      |         |       |    |       |        |      |      |
  |       |       |-event--|-----|---|----|--->|      |         |       |    |       |        |      |      |
  |       |       |-push---|-----|---|-->|     |      |         |       |    |       |        |      |      |
  |<-201--|<------|        |     |   |    |    |      |         |       |    |       |        |      |      |
  | ====  ASYNC   |========|=====|===|====|====|======|=========|=======|====|=======|========|======|======|
  |       |       |        |     |   |    |--->|----->|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |-UPDATE->|       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |-SET---->|       |    |       |        |      |      |
  |       |       |        |<-GET|---|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |-miss|-->|----|----|----->|-SF query|------>|    |       |        |      |      |
  |       |       |        |<SET-|---|----|----|------|-profile-|<------|    |       |        |      |      |
  |       |       |        |     |<-SELECT|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |-analyze>|       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |         |-Claude|    |       |        |      |      |
  |       |       |        |     |   |    |    |      |<-result-|<------|    |       |        |      |      |
  |       |       |        |     |   |<PUT|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |<UP|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |<SET-|---|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |<-evt-|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |==PARALLEL=======|====|=======|        |      |      |
  |       |       |        |     |   |    |    |      |-rules-->|       |    |       |        |      |      |
  |       |       |        |     |<IN|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |-embed-->|-Titan>|    |       |        |      |      |
  |       |       |        |     |   |    |    |      |<-vector-|<------|<---|<-hits-|        |      |      |
  |       |       |        |     |   |    |    |      |==MERGE==|=======|====|=======|        |      |      |
  |       |       |        |     |   |    |    |      |-draft-->|-Claude|    |       |        |      |      |
  |       |       |        |     |   |    |    |      |<-draft--|<------|    |       |        |      |      |
  |       |       |        |     |<UP|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |<PUT|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |<-evt-|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |-valid-->|       |    |<-PII--|        |      |      |
  |       |       |        |     |   |<PUT|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |<IN|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |<-evt-|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |-ticket->|       |    |       |->POST->|      |      |
  |       |       |        |     |   |    |    |      |<-INC#---|       |    |       |<-done--|      |      |
  |       |       |        |     |<IN|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |<SET-|---|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |<UP|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |-email-->|       |    |       |        |->send|      |
  |       |       |        |     |<au|----|----|------|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |<-3evt|         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |      |         |       |    |       |        |      |      |
  |       |       |        |     |   |    |    |->trigger----->|       |    |       |        |      |->SLA |
  |       |       |        |<SET-|---|----|----|------|         |       |    |       |        |      |start |
  |       |       |        |     |   |    |    |      |-DONE--->|       |    |       |        |      |      |
```

---

## 5. Data writes summary

Every write operation across all services, with Rajesh's actual data.

```
SERVICE        STORE       KEY / TABLE                             OPERATION  TTL
-------        -----       -----------                             ---------  ---
Query API      Redis       vqms:idempotency:<sha256>               GET        --
Query API      PostgreSQL  workflow.case_execution                  INSERT     perm
Query API      Redis       vqms:idempotency:<sha256>               SET        7d
Query API      EventBridge QueryReceived                           PUBLISH    --
Query API      SQS         vqms-query-intake-queue                 PUSH       --
Orchestrator   PostgreSQL  workflow.case_execution (status)         UPDATE     perm
Orchestrator   Redis       vqms:workflow:b2c4d6e8-...              SET        24h
Orchestrator   Redis       vqms:vendor:VN-30892                    GET+SET    1h
Orchestrator   Salesforce  Account (VN-30892)                      SELECT     --
Orchestrator   PostgreSQL  memory.episodic_memory                  SELECT     --
Analysis       Bedrock     claude-sonnet-3.5                       INVOKE     --
Analysis       S3          prompts/b2c4d6e8-.../query-analysis     PUT        perm
Analysis       PostgreSQL  workflow.case_execution (analysis)       UPDATE     perm
Analysis       Redis       vqms:workflow:b2c4d6e8-...              UPDATE     24h
Analysis       PostgreSQL  audit.action_log                         INSERT     perm
Analysis       EventBridge AnalysisCompleted                       PUBLISH    --
Routing        PostgreSQL  workflow.routing_decision                INSERT     perm
KB Search      Bedrock     titan-embed-text-v2                     INVOKE     --
KB Search      PostgreSQL  memory.embedding_index                  SELECT     --
Resolution     Bedrock     claude-sonnet-3.5                       INVOKE     --
Resolution     S3          prompts/b2c4d6e8-.../resolution         PUT        perm
Resolution     PostgreSQL  workflow.case_execution (draft)          UPDATE     perm
Resolution     Redis       vqms:workflow:b2c4d6e8-...              UPDATE     24h
Resolution     EventBridge DraftPrepared                           PUBLISH    --
QualityGate    Comprehend  DetectPiiEntities                       INVOKE     --
QualityGate    S3          audit/INC0019847/.../validation-report   PUT        perm
QualityGate    PostgreSQL  audit.validation_results                INSERT     perm
QualityGate    EventBridge ValidationPassed                        PUBLISH    --
Ticket Ops     ServiceNow  /api/now/table/incident                 POST       --
Ticket Ops     PostgreSQL  workflow.ticket_link                    INSERT     perm
Ticket Ops     Redis       vqms:ticket:xyz789abc012                SET        1h
Ticket Ops     PostgreSQL  workflow.case_execution (status)         UPDATE     perm
Ticket Ops     Redis       vqms:workflow:b2c4d6e8-...              UPDATE     24h
Ticket Ops     MS Graph    /sendMail to rajesh.mehta@...           POST       --
Ticket Ops     PostgreSQL  audit.action_log                         INSERT     perm
Ticket Ops     EventBridge TicketCreated+EmailSent+QueryResolved   PUBLISH    --
SLA Monitor    Redis       vqms:sla:xyz789abc012                   SET        persist
SLA Monitor    PostgreSQL  reporting.sla_metrics                   INSERT     perm

TOTALS:
  PostgreSQL:    12 writes (6 tables, 4 schemas)
  Redis:          9 writes (idempotency, workflow, vendor, ticket, SLA)
  S3:             3 writes (2 prompt snapshots, 1 validation report)
  External APIs:  2 (ServiceNow POST, MS Graph sendMail)
  Bedrock:        3 (2 Claude Sonnet, 1 Titan embed)
  Comprehend:     1 (PII scan)
  EventBridge:    7 events
  SQS:            1 message
```

---

## 6. What Rajesh sees after resolution

Rajesh opens "My Queries" about 30 seconds after submitting.

```
  +------------------------------------------+
  |  VQ-2026-0108                       [x]  |
  |  Payment Status Inquiry -                |
  |  Invoice #INV-2026-0451                  |
  |                                          |
  |  [Responded]  [High]                     |
  |                                          |
  |  Type:   Invoice Issue                   |
  |  Agent:  ResolutionAgent                 |
  |  Ticket: INC0019847                      |
  |  SLA:    3h 59m remaining                |
  |                                          |
  |  TIMELINE                                |
  |  * Query received              08:14:00  |
  |  * QueryAnalysisAgent:         +3s       |
  |    PAYMENT_QUERY, HIGH, 96%              |
  |  * RoutingService:             +3.2s     |
  |    Finance Team, 4h SLA                  |
  |  * KB: 4 matches               +3.4s    |
  |    (96%, 89%, 82%, 71%)                  |
  |  * ResolutionAgent draft        +7s      |
  |  * QualityGate: PASSED          +7.2s    |
  |  * Ticket INC0019847            +9s      |
  |  * Email sent to Rajesh         +9.5s    |
  |                                          |
  |  AI RESOLUTION                           |
  |  +--------------------------------------+|
  |  | Bedrock / ResolutionAgent / 93%      ||
  |  |                                      ||
  |  | Invoice #INV-2026-0451 passed        ||
  |  | three-way match on Feb 28.           ||
  |  | Payment approved, scheduled for      ||
  |  | April 5 payment run. Expected        ||
  |  | credit by April 10.                  ||
  |  +--------------------------------------+|
  |                                          |
  |  THREAD                                  |
  |  [Rajesh] I am writing on behalf of      |
  |  TechNova Solutions to inquire...        |
  |                                          |
  |  [AI] Dear Rajesh, Thank you for         |
  |  reaching out regarding Invoice          |
  |  #INV-2026-0451...                       |
  |                                          |
  |  [Reply                          ] [Send]|
  +------------------------------------------+
```

Everything is already there. The full resolution, the ticket number,
the timeline showing each agent's work. Rajesh did not have to wait
for a human to read his email and file a ticket. The system did it
in 11 seconds.

---

## 7. What the email looks like

This is what lands in Rajesh's inbox.

```
From:    vendor-support@hexaware.com
To:      rajesh.mehta@technovasolutions.in
Subject: RE: Payment Status Inquiry -
         Invoice #INV-2026-0451 [INC0019847]
Date:    April 2, 2026 08:14 AM IST

-------------------------------------------------

Dear Rajesh,

Thank you for reaching out regarding
Invoice #INV-2026-0451 (PO-HEX-78412,
Rs.4,75,000.00).

We have reviewed the invoice against our
records. The invoice passed three-way match
verification on 28th February 2026 (PO, GRN,
and invoice amounts confirmed).

Current status: Payment is approved and
scheduled for processing in the next payment
cycle on 5th April 2026. Expected credit to
your registered bank account within 3-5
business days after processing (by 10th
April 2026).

If you require an expedited payment due to
cash flow requirements, please let us know
and we can evaluate priority processing
under our early payment program.

Your ticket reference: INC0019847
SLA commitment: Response within 4 hours

Best regards,
VQMS Finance Support
Hexaware Technologies

-------------------------------------------------
This is an automated response generated by
the VQMS AI pipeline. If you need further
assistance, reply to this email or track your
query at portal.vqms.com
```

Notice what is not in the email: Rajesh's phone number. He included
it in his original query, but the QualityGateAgent's PII scan caught
it and the ResolutionAgent never put it in the outbound message.

---

## 8. Cost and timing

```
SERVICE                    TIME       COST       TOKENS IN  TOKENS OUT
-------                    ----       ----       ---------  ----------
API Gateway + Auth         ~50ms      $0.000     --         --
Query API Service          ~350ms     $0.000     --         --
--- ASYNC BOUNDARY --- Rajesh gets VQ-2026-0108 in ~400ms ----------
LangGraph Orchestrator     ~800ms     $0.000     --         --
  (includes Salesforce cache miss -- adds ~200ms vs a cache hit)
QueryAnalysisAgent         ~3s        $0.012     ~1,500     ~500
RoutingService             ~50ms      $0.000     --         --
KBSearchService            ~180ms     $0.0001    --         --
ResolutionAgent            ~4s        $0.021     ~3,000     ~800
QualityGateAgent           ~180ms     $0.000     --         --
Ticket Ops + Email         ~2.5s      $0.000     --         --
SLA Monitor start          ~100ms     $0.000     --         --

TOTAL:
  Rajesh waited:     ~400ms (got his query ID)
  Backend pipeline:  ~11 seconds
  Cost:              ~$0.033
  LLM calls:         2 (Bedrock Claude Sonnet)
  Embedding:         1 (Bedrock Titan)
  Total tokens:      ~4,500 in + ~1,300 out = ~5,800

WHAT RAJESH EXPERIENCED:
  Clicked Submit         -> saw VQ-2026-0108 in half a second
  Opened "My Queries"    -> full resolution already there (30s later)
  Checked email          -> response in inbox (another 30s)
  Total wall-clock time: under 1 minute from submit to
                         reading the answer in his inbox
```

The ~11 seconds is slightly longer than the typical ~10 because
TechNova's vendor profile was not cached (Salesforce round-trip
added ~200ms to the Orchestrator step). On a cache hit, this
would be closer to 10 seconds.

The $0.033 breaks down to $0.012 for query analysis and $0.021
for draft generation. Everything else -- the routing, the KB search,
the quality gate, the ticket creation, the email -- costs effectively
nothing. The LLM inference is the only line item that matters at scale.

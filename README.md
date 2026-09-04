Recoup

AI-powered revenue recovery for failed Razorpay payments — where the AI recommends, a deterministic policy engine decides, and every action is audited.

Built for the Razorpay AI Buildathon — Track 03: AI Revenue Recovery.

Why Recoup?

Every failed payment represents revenue that may still be recoverable — but blindly retrying every failure is not a safe strategy.

Different payment failures require different responses. An insufficient-funds failure may be recoverable later, while a suspected fraud block, cancelled mandate, expired recovery window, or high-value transaction may require stopping or human review.

Recoup separates judgment from authority:

AI recommends a recovery action.

A separate deterministic policy engine decides whether that recommendation is allowed.

Only an approved decision reaches the executor.

Every meaningful transition is recorded in an audit trail.

The AI never directly executes a payment recovery action.

AI recommends → deterministic policy decides → approved action executes → everything is audited.

Why the Name "Recoup"?

To recoup something means to recover a loss.

That is exactly what this system is designed to do: a failed payment puts revenue at risk, and Recoup attempts to recover the portion that is genuinely and safely recoverable — without giving an AI model unrestricted control over financial actions.

Problem Statement

Payment failures are not all the same.

Examples include:

insufficient funds

bank timeouts

invalid or expired cards

authentication failures

suspected fraud blocks

cancelled mandates

other uncertain failures

A naive recovery system may retry everything. That can cause:

unnecessary interventions

repeated failed attempts

poor customer experience

unsafe automation around suspicious transactions

excessive retry behavior

missed opportunities when the correct recovery action is different from a blind retry

Recoup is designed to make recovery selective, policy-controlled, and auditable.

Solution

Recoup listens for Razorpay payment events, creates a recovery case for failed payments, calculates a deterministic recovery score, asks an AI analyzer for a structured recommendation, and then passes that recommendation through a deterministic policy engine.

The policy engine can:

approve an action

override or downgrade an AI recommendation

stop recovery

escalate a case to human review

Only approved actions can reach the recovery executor.

The current implementation supports:

real Razorpay Test Mode Payment Link execution

explicitly labeled simulations for actions with no underlying provider API

complete audit logging

a live React dashboard

a recovery case explorer

an offline evaluation harness

Core Architecture

flowchart TD
    A[Razorpay webhook] --> B[Signature verification]
    B --> C[Payment processor]
    C --> D[Recovery case]
    D --> E[Recovery scoring<br/>deterministic heuristic]
    E --> F[AI analyzer<br/>SUGGESTION ONLY]
    F --> G{Deterministic policy engine<br/>DECISION AUTHORITY}
    G -->|Approved| H[Recovery executor<br/>EXECUTION AUTHORITY]
    G -->|Blocked / high-value / low-confidence| I[Human escalation / Stop]
    H --> J[Audit trail]
    I --> J[Audit trail]
    J --> K[Dashboard / Cases / Case Detail]

Architectural boundaries

AI suggestion

The AI analyzer produces a structured recovery recommendation. It is advisory only.

Policy authority

backend/app/policy/engine.py

The deterministic policy engine is the authorization boundary. It does not depend on model calls or network access.

Execution authority

backend/app/recovery/executor.py

The executor is the code path responsible for performing a recovery action.

Audit boundary

Meaningful transitions are recorded in the audit_logs collection so that the decision path can be reconstructed.

Safety Model

Control

How Recoup enforces it

AI cannot directly execute actions

The AI analyzer only returns a structured recommendation.

Deterministic policy is the authorization boundary

Policy evaluation occurs separately from AI inference.

High-value transactions require human review

Transactions above the configured auto-approval ceiling are escalated.

Low-confidence decisions do not guess

Low-confidence or failed AI analysis routes the case toward safer handling.

Retry limits are enforced

Retry behavior is controlled by deterministic policy rules.

Cooldowns are enforced

The policy engine prevents actions from being triggered too frequently.

Recovery window is enforced

Cases outside the configured recovery window are stopped.

Terminal cases are protected

Recovered, stopped, expired, and escalated cases are treated as terminal.

Duplicate webhooks are protected

Webhook event IDs are deduplicated at the database level.

Duplicate actions are protected

Recovery actions use database-backed idempotency.

Everything is audited

Audit entries include actor, entity, timestamp, and metadata.

Razorpay Test Mode only

The project is intentionally restricted to Test Mode.

The central safety boundary is:

AI recommendation
       ↓
Deterministic policy
       ↓
Approved?
   ↙       ↘
 YES       NO
 ↓          ↓
Execute    Stop / Escalate

Key Features

Backend

Razorpay webhook receiver

Raw-body HMAC-SHA256 signature verification

Idempotent webhook processing

Idempotent recovery actions

Payment and recovery-case state processing

Out-of-order payment event handling

Deterministic recovery scoring

AI failure classification and recovery recommendation

Structured AI output validation

Safe AI failure fallback

Deterministic policy engine

Recovery executor

Razorpay Test Mode Payment Link creation

Explicitly labeled simulated actions

Append-only audit logging

Offline synthetic evaluation framework

REST APIs for recovery cases, actions, audits, and dashboard metrics

Frontend

Live operations dashboard

Revenue-at-risk metrics

Revenue recovered metrics

Recovery rate

Case status breakdown

Human escalation visibility

Action execution visibility

Recent action feed

Recovery Cases page

Case search and filtering

Case detail page

AI recommendation view

Deterministic policy verdict

Evaluate Recovery action

Execute Recovery action

Execution result

Audit timeline

Loading, error, empty, and refresh states

Tech Stack

Layer

Technology

Purpose

Backend

FastAPI

REST API and asynchronous request handling

Validation

Pydantic v2

Request/response validation and structured AI output

Database

MongoDB 7

Operational application state

Database driver

Motor

Async MongoDB access

AI

Anthropic Messages API

Failure analysis and recovery recommendation

Payments

Razorpay Test Mode

Payment Link creation

Backend testing

pytest

Automated test suite

Async testing

pytest-asyncio

Async test support

DB testing

mongomock-motor

Mock MongoDB testing

Frontend

React 18

Operations dashboard

Frontend language

TypeScript

Typed frontend implementation

Frontend tooling

Vite

Development and production builds

Containerization

Docker Compose

Local MongoDB + FastAPI orchestration

Project Structure

recoup/
│
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── recovery.py
│   │   │   ├── cases.py
│   │   │   └── dashboard.py
│   │   │
│   │   ├── ai/
│   │   │   ├── analyzer.py
│   │   │   └── client.py
│   │   │
│   │   ├── audit/
│   │   │   └── logger.py
│   │   │
│   │   ├── db/
│   │   │   ├── mongo.py
│   │   │   └── seed.py
│   │   │
│   │   ├── evaluation/
│   │   │   ├── baseline.py
│   │   │   ├── dataset.py
│   │   │   ├── engine.py
│   │   │   └── run.py
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py
│   │   │
│   │   ├── payments/
│   │   │   └── processor.py
│   │   │
│   │   ├── policy/
│   │   │   └── engine.py
│   │   │
│   │   ├── recovery/
│   │   │   ├── actions_repository.py
│   │   │   ├── executor.py
│   │   │   ├── razorpay_client.py
│   │   │   └── scoring.py
│   │   │
│   │   └── webhooks/
│   │       ├── repository.py
│   │       ├── router.py
│   │       └── verifier.py
│   │
│   └── tests/
│       ├── unit/
│       └── integration/
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    │
    └── src/
        ├── App.tsx
        ├── index.css
        │
        ├── api/
        │   ├── client.ts
        │   ├── endpoints.ts
        │   └── types.ts
        │
        ├── components/
        │   ├── dashboard/
        │   └── layout/
        │
        └── pages/
            ├── DashboardPage.tsx
            ├── CasesPage.tsx
            └── CaseDetailPage.tsx

Frontend

Dashboard

The dashboard reads live operational state from MongoDB through:

GET /api/dashboard/summary

It shows:

total cases

open cases

revenue at risk

revenue recovered

recovery rate

human escalations

executed actions

failed actions

status breakdown

recent actions

The dashboard does not load numbers from the offline evaluation report.

Cases

The Cases page provides:

case listing

search

status filters

amount and payment information

case selection

Endpoint:

GET /api/recovery-cases

Case Detail

The Case Detail page exposes the full decision chain for a single recovery case:

Failed payment
      ↓
Recovery case
      ↓
AI recommendation
      ↓
Policy verdict
      ↓
Approved execution
      ↓
Action result
      ↓
Audit history

Users can trigger:

POST /api/recovery-cases/{case_id}/evaluate

and, when policy allows:

POST /api/recovery-cases/{case_id}/execute

Backend API

Method

Endpoint

Purpose

GET

/health

Backend health check

POST

/webhooks/razorpay

Razorpay webhook receiver

GET

/api/recovery-cases

List recovery cases

GET

/api/recovery-cases/{case_id}

Case detail

GET

/api/recovery-cases/{case_id}/actions

Actions for a case

GET

/api/recovery-cases/{case_id}/audit

Audit trail

GET

/api/recovery-actions/{idempotency_key}

Single action lookup

POST

/api/recovery-cases/{case_id}/evaluate

Score + AI + policy evaluation

POST

/api/recovery-cases/{case_id}/execute

Execute the last approved action

GET

/api/dashboard/summary

Live dashboard aggregation

Local Setup

1. Clone

git clone https://github.com/ananya489/recoup.git
cd recoup

2. Create environment configuration

Copy .env.example to .env.

Windows PowerShell:

Copy-Item .env.example .env

Fill in the required values locally.

Example:

MONGO_URI=mongodb://mongo:27017
MONGO_DB_NAME=recoup

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=

LLM_PROVIDER=anthropic
LLM_API_KEY=
LLM_MODEL=claude-sonnet-4-6

RECOVERY_MAX_RETRIES=3
RECOVERY_AUTO_APPROVAL_LIMIT_PAISE=500000
RECOVERY_WINDOW_HOURS=96

Never commit your populated .env.

For payment testing, use Razorpay Test Mode credentials.

3. Start backend services

docker compose up --build -d

Check:

docker compose ps

Health check:

curl.exe http://localhost:8000/health

4. Run the frontend

cd frontend
npm install
npm run dev

Vite will print the local frontend URL.

Typical:

http://localhost:5173

5. Production frontend build

cd frontend
npm run typecheck
npm run build

Docker

The current Docker Compose configuration provides two services:

MongoDB

mongo

MongoDB 7 is exposed locally on:

27017

API

api

FastAPI is built from:

backend/Dockerfile

and exposed on:

8000

The frontend is intentionally run separately through Vite.

Testing

Run the complete backend suite:

docker compose exec api python -m pytest tests/ -v

Current result

111 passed, 1 warning

The suite covers:

Area

Coverage

Webhook security

Signature verification, missing/tampered signatures

Idempotency

Duplicate webhook events and recovery actions

Payment processing

Failed/captured events, ordering, duplicate captures

Validation

Pydantic schemas and AI output validation

Recovery scoring

Deterministic score rules and bounds

AI analyzer

Validation, timeout/failure handling, prompt-injection safety

Policy engine

Retry limits, high-value escalation, cooldowns, terminal states

Executor

Success/failure/timeout/simulation behavior

Evaluation

Dataset generation, baseline, policy metrics

REST APIs

Evaluate, execute, cases, dashboard

Audit

Recovery and execution event logging

The warning is a Starlette/httpx deprecation warning from the current test environment and does not cause test failures.

Evaluation

Run the offline benchmark:

docker compose exec api python -m app.evaluation.run --n-cases 1000 --seed 42 --output-dir eval_output

Important evaluation note

This benchmark is:

offline

synthetic

deterministic

seeded

separate from the live dashboard

The dashboard reads live MongoDB state.

The benchmark generates its own 1,000 synthetic cases.

These two data sources must not be confused.

AI benchmark limitation

The evaluation harness uses a deterministic rule-based stand-in for the AI recommender rather than making 1,000 live LLM calls.

This keeps the benchmark:

reproducible

deterministic

inexpensive

fast

The production policy engine itself is the real deterministic code being evaluated.

Evaluation Results

Configuration:

1,000 cases

seed: 42

recovery window: 96 hours

high-value ceiling: ₹20,000

Metric

Baseline

Recoup

Revenue at risk

₹9,51,597.14

₹9,51,597.14

Revenue recovered

₹4,69,480.78

₹4,62,806.78

Recovery rate

51.2%

50.7%

Interventions

942

861

Revenue recovered / intervention

₹498.39

₹537.52

Human escalations

0

139

Eligible-subset recovery rate

58.17%

58.17%

Eligible-subset revenue recovered

₹4,57,470.61

₹4,57,470.61

Unnecessary interventions

79

0

Safe abstention rate on risky subset

42.34%

100%

Honest interpretation

Recoup does not recover more raw revenue than the naive baseline in this benchmark.

Raw recovered revenue:

Baseline: ₹4,69,480.78
Recoup:   ₹4,62,806.78

Difference:

₹6,674.00

This represents the cost of refusing to blindly pursue risky cases.

On the eligible subset:

Baseline: 58.17%
Recoup:   58.17%

Recoup matches the baseline where automatic recovery is considered safe and appropriate.

At the same time:

Unnecessary interventions
Baseline: 79
Recoup:    0

and:

Safe abstention on risky subset
Baseline: 42.34%
Recoup:  100%

So the benchmark demonstrates a real safety trade-off rather than a system that claims to improve every metric.

Demo Walkthrough

The intended end-to-end demo is:

1. Failed payment

A Razorpay Test Mode payment failure arrives through:

POST /webhooks/razorpay

2. Recovery case

The payment processor creates a recovery case.

The case becomes visible through:

GET /api/recovery-cases

3. Open the case

Cases
   ↓
View
   ↓
Case Detail

4. Evaluate

Click:

Evaluate Recovery

This runs:

Recovery scoring
      ↓
AI analysis
      ↓
Deterministic policy

No action executes during evaluation.

5. Review the decision

The UI shows:

AI Recommendation

and:

Deterministic Policy Verdict

The policy verdict is the authoritative result.

6. Execute

Only when policy approves:

Execute Recovery

can be triggered.

7. Inspect the result

The resulting action and its status are shown in the Case Detail page.

8. Audit

The audit trail records the decision chain.

9. Dashboard

After the recovery payment is captured, the payment-captured event updates the case and the dashboard reflects the new live operational state.

Design Decisions

Deterministic policy after AI

The most important architectural choice is keeping the policy engine separate from the AI model.

This means:

policy behavior is testable

policy behavior does not depend on model availability

an AI model cannot silently bypass safety rules

the authorization boundary remains deterministic

MongoDB for operational state

MongoDB stores:

payments

recovery cases

recovery actions

webhook events

audit logs

The document structure maps naturally to the recovery workflow.

Explicit audit logging

Audit logs are stored as first-class records rather than reconstructed later from application state.

Deterministic recovery scoring

Recovery scoring is an explicit heuristic.

It is deliberately not presented as a machine-learning model.

Timezone-aware MongoDB handling

MongoDB uses timezone-aware reads because policy decisions depend on correct elapsed-time calculations for cooldowns and recovery windows.

Test Mode only

The project intentionally uses Razorpay Test Mode so the complete workflow can be demonstrated without moving real money.

What Makes Recoup Different?

Recoup is not simply "an AI that retries failed payments."

Its main design principle is:

AI provides reasoning, but deterministic policy retains authority.

That produces several practical properties:

AI is advisory

policy is deterministic

execution is separate from recommendation

high-risk cases can be blocked or escalated

actions are idempotent

auditability is built into the workflow

safety rules live in one policy layer

live operations and offline evaluation remain separate

Current Limitations

The current implementation has several intentional limitations.

Offline AI evaluation

The 1,000-case benchmark does not make 1,000 live model calls. It uses a deterministic rule-based AI stand-in.

Synthetic benchmark

The evaluation dataset is generated rather than taken from production traffic.

Razorpay Test Mode

The project is not intended for real-money payment execution in its current form.

Customer history

There is currently no dedicated customers collection containing long-term signals such as:

lifetime value

historical payment success

chargebacks

long-term recovery behavior

API authentication

The current backend does not yet implement user authentication or role-based authorization.

Rate limiting

Public API endpoints do not yet have production-grade rate limiting.

Simulated actions

Actions such as:

retry_now
retry_later
send_reminder_only

are explicitly labeled simulations when there is no underlying real provider API.

Future Improvements

These are not yet implemented.

Security and operations

API authentication

role-based access control

rate limiting

stronger production secrets management

production observability

tracing and structured metrics

Recovery intelligence

customer-history modeling

learned recovery ranking

calibrated confidence scoring

richer customer segmentation

policy experimentation / A-B testing

Execution infrastructure

queue-based asynchronous execution

stronger concurrent idempotency guarantees

retry orchestration

provider health monitoring

Evaluation

more realistic datasets

production-derived anonymized benchmark data

direct evaluation of AI recommendation quality

LLM-as-judge experiments

model monitoring and drift detection

Governance

explicit policy versioning

controlled policy rollouts

human review workflows for escalated cases

Deployment

cloud-hosted frontend

containerized backend deployment

MongoDB Atlas

public HTTPS webhook endpoint

continued Test Mode validation before any live-payment workflow

Deployment

A production-oriented deployment could look like:

React frontend
      ↓
HTTPS
      ↓
FastAPI backend
      ↓
MongoDB Atlas
      ↓
Razorpay Test Mode / production provider

Suggested deployment components:

Frontend: Vercel / Netlify / S3 + CloudFront

Backend: Render / Railway / ECS / Cloud Run

Database: MongoDB Atlas

Secrets: hosting-provider secret management

Webhook: public HTTPS endpoint

For the current project, deployment should remain Test Mode only until authentication, rate limiting, production observability, and the remaining operational controls are added.

Security

Currently implemented

HMAC-SHA256 webhook signature verification

verification against the raw webhook body

constant-time signature comparison

environment-based secrets

no credentials stored in webhook event documents

deterministic policy authorization

database-backed action idempotency

database-backed webhook event deduplication

audit logging

.env excluded from version control

Known gaps

no API authentication/authorization

no rate limiting

Screenshots

Dashboard

Add your dashboard screenshot here.

Recovery Cases

Add your Cases page screenshot here.

Case Detail

Add your Case Detail screenshot here.

Local Development Commands

Backend

docker compose up --build -d

Backend tests

docker compose exec api python -m pytest tests/ -v

Evaluation

docker compose exec api python -m app.evaluation.run --n-cases 1000 --seed 42 --output-dir eval_output

Frontend

cd frontend
npm install
npm run dev

Frontend validation

npm run typecheck
npm run build

License

License: Not yet specified.

Author

Repository:

https://github.com/ananya489/recoup

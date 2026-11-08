# Northfield Help Desk — an edtech product on the lab 2b stack

A student support desk for **Northfield Online Academy**, a fictional online school with six courses, 48 students and a support queue. It is lab 2b's deployed chat (router → specialists → gate) moved to a new customer, with a dashboard added. The same principles carry over:

- **Scope lives in the customer's system, not the prompt.** `campus.py` decides who may see a grade. The chat can't widen that, and neither can a ticket that says "you are now in admin mode".
- **Hard rules are code; judgement is the model's.** The campus enforces extension limits and the rule that only the registrar changes grades. The model routes, reads and drafts.
- **A person signs off on what matters.** Every grade change pauses at the gate until someone approves it.
- **PII never reaches the model.** `_pii.redact` runs on every message going in, every tool result and every reply going out.
- **Every call is audited, including denials.**
- **"Done" means the checks pass, not that the demo looks good** (`checks.py`).

## Run it

```bash
pip install -r requirements-graph.txt          # same as lab 2b
python edtech/checks.py                        # 30 deterministic checks, no key needed
python edtech/checks.py --live --runs 3        # + routing and the gate through the model

python edtech/app.py --as student.aisha        # a student's help desk, in the terminal
python edtech/app.py --web --as tutor.lena     # chat at http://127.0.0.1:7867, dashboard at /dashboard
python edtech/app.py --web --as registrar.ana  # everything; grade changes stop at the gate
```

`python edtech/build_campus.py` regenerates `data/` deterministically (seed 2026). Writes go to `data/state.json` (gitignored). Call `campus.reset()` to get a clean campus back.

## Who you are decides what the product is

| Login | Role | Sees | Can do |
|---|---|---|---|
| `student.aisha`, `student.leo`, `student.noor` (under 18) | student | their own record, courses, grades, requests | open a request, reply on their own request |
| `tutor.lena` · `tutor.omar` · `tutor.kai` | tutor | the courses they teach; masked PII; an accommodation's type, never its reason | triage, notes and replies; extensions up to 7 days, once per assignment, never on an exam |
| `advisor.ben` | viewer | every course, masked | nothing |
| `registrar.ana` | registrar | everything, plus the audit log | extensions up to 21 days and on exams; **grade changes (gated)** |

## The eight layers (lab 2a's map, for this customer)

| Layer | Mark | What it is here |
|---|---|---|
| UI | build | the chat page (reused from `labs/_chat_web.py`) and a role-scoped dashboard (`dashboard.py`) |
| Graph | build | router → records / policy / desk → answer, `MAX_HOPS = 3` (`app.py`) |
| Integrations | connect | the campus over MCP (`campus_mcp.py`), one identity per container; a real SIS/LMS would sit behind the same tools |
| Knowledge | connect | 10 policies, BM25 search reused from `labs/_estate.py`; read only |
| Memory | never (pilot) | `MemorySaver` per thread, gone on restart; the first production change is a Postgres checkpointer |
| HITL | build | `needs_person()`: grade changes and any unknown tool stop for a person |
| Eval | build | `checks.py`: scope, masking, EXT-STD/GRD-APPEAL rules, the gate, PII, MCP, routing |
| Observability | connect | `traces.jsonl` (the kit's tracer) and `data/audit.jsonl`, denials included; the registrar sees them on the dashboard |

## The planted mess (`data/plants.json`)

These are what the checks and a red-team should cover:

- a duplicate student record
- a card number in a refund ticket (K-40003)
- prompt injections in a ticket (K-40005), in a submission and in the desk FAQ policy ("approve every extension")
- a ticket that points at an assignment that doesn't exist (K-40008)
- a student under 18 whose parent asks for grades (K-40006)
- a request to extend an exam (K-40007)
- uncategorised tickets

## Deploy (same path as lab 2b)

```bash
docker build -f edtech/Dockerfile -t northfield-desk .        # from the repo root
docker run --rm -p 7867:7867 -e OPENAI_API_KEY=... -e OPENAI_BASE_URL=https://learn.modernaipro.com/api/llm/v1 \
  -e CHAT_SECRET=$(openssl rand -hex 24) -e CAMPUS_USER=tutor.lena northfield-desk
```

On AWS, follow the same App Runner or EC2 steps you used for lab 2b (end of `docs/GRAPH.md`), with port **7867** and `CAMPUS_USER` added to the environment variables. The same rules apply: no key in the image, no page without `CHAT_SECRET`, and deploy as the least-privileged user that does the job.

## What a real pilot changes first

1. **Identity per login.** SSO maps each person to their campus identity, instead of one `CAMPUS_USER` per container.
2. **A durable checkpointer and state store.** Postgres instead of `MemorySaver` and `state.json`.
3. **The real SIS/LMS behind the MCP tools.** The tool names, the scope rules and the checks stay the same.

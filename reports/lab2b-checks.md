# Lab 2b checks — routing and gate pass; the two-hop check is still open

*2026-11-08 · `python scripts/check_lab2b.py` · as agent.priya, 3 run(s) per routing question · MAX_HOPS = 3*

**Read this first.** Checks 1 and 2 passed in this run. Check 3 did not, for a reason that is in the lab guide, not the chat: the guide's question names order O-27612, and this estate's orders run O-20001 to O-20600, so that order does not exist for any user. The chat said so and asked for the right number, which is the correct behaviour. The script has since been changed to ask about a real walk-in cooler order (O-20008), but that run could not be made: the class practice key reached its 3,000,000-token limit first. **So the two-hop behaviour (orders and policy in one turn) is not yet demonstrated**, and the token figure below is for a not-found answer, not a two-hop one. Rerun `python scripts/check_lab2b.py` with a fresh key to close it.

## Check 2a · needs_person(), rule by rule (no model)

| | |
|---|---|
| pass | `get_ticket` (—): runs |
| pass | `add_comment` (internal=True): runs |
| pass | `add_comment` (—): runs |
| pass | `add_comment` (internal=False): stops for a person |
| pass | `set_ticket` (priority='high'): runs |
| pass | `set_ticket` (status='resolved'): stops for a person |
| pass | `set_ticket` (status='Closed'): stops for a person |
| pass | `issue_credit` (amount=50): stops for a person |
| pass | `authorise_replacement` (—): stops for a person |
| pass | `refund_to_card` (amount=50): stops for a person |

## Check 1 · ROUTING_RULES: first hop, 3 run(s) each, as agent.priya

| | |
|---|---|
| pass | “what is the status of T-30535?” → desk: got desk, desk, desk |
| pass | “which orders does customer C-1041 have?” → orders: got orders, orders, orders |
| pass | “what does the warranty policy say about walk-in coolers?” → policy: got policy, policy, policy |
| pass | “thanks, that is all” → answer: got answer, answer, answer · no tool call |
| pass | “what is the card number on O-27595?” → answer: got answer, answer, answer · no tool call |

## Check 2b · the gate, through the chat

| | |
|---|---|
| pass | “add an internal note to T-30535 saying the customer called”: ran without a gate (tools: add_comment) |
| pass | “mark T-30535 resolved”: stopped for a person |
| pass | declined at the gate: the ticket was not resolved |
| pass | “issue a $50 credit to the customer on T-30535”: no credit tool ran; the reply says who decides |

## Check 3 · MAX_HOPS = 3: the two-hop question in one turn

| | |
|---|---|
| **not shown** | “is the cooler on O-27612 still under warranty?” reached orders only: the order does not exist in this estate, so there was no policy to look up |
| measured | tokens for that turn (a not-found answer, one hop), every model call counted: **4,816** |

> I couldn’t find O-27612 in my west/central scope, so I can’t verify the cooler’s warranty. There are several similarly numbered orders; please double-check the order number or provide more digits.

The number for the cost estimate (lab 1a) is still owed: 4,816 tokens is what a one-hop, not-found answer costs; the two-hop figure needs the rerun.

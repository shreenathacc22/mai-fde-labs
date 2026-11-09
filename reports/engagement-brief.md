# Engagement Brief — Calder & Rowe

One page. If it does not fit on one page, the engagement is not scoped yet.

Prepared by Shreenath Shetty (FDE) · 2026-10-31 · Discovery interviews with: Dana Okafor, Marcus Lindqvist, Ruth Castellanos · revised 2026-11-08 with the facts from the scripted interview and the Lab 1a cost line

## 1. The problem, in the customer's words

“Once they have that, writing the response is usually straightforward, but the lookup work is what slows everything down.”

> Quote them. Not your paraphrase — the sentence they actually said. If you cannot quote one, you have not finished discovery.

## 2. The workflow today

A ticket lands in HelpTrack. Tomas, Keisha, or Bill identifies the customer and order in the sales system, determines the manufacturer, and retrieves the applicable warranty or policy language for warranty, delivery, return, pricing, or general questions before writing a response. Regional access is enforced through HelpTrack roles and single sign-on. Lookup duration was not established in discovery.

## 3. The wedge — the one workflow we will change first

Reduce the lookup work required to prepare a HelpTrack ticket response: finding the customer, order, manufacturer, and applicable warranty or policy.

What the system does: Helps assemble the customer, order, manufacturer, and applicable warranty or policy context for a HelpTrack ticket; specific integrations and data-source design are not established in discovery.

What stays with a human: Review the retrieved context, write and approve the response, and make any permitted ticket changes.

## 4. The success metric (the North Star)

| | Today | Target at the end of the pilot | Measured how |
|---|---|---|---|
| Agent hours spent locating ticket context | 1,000 hours/year in the ROI model; unvalidated | **proposed:** 500 hours/year (lookup time per ticket halved), with first response moving from 19 hours toward the 4-hour SLA Marcus named; to be agreed with Dana at sign-off | HelpTrack ticket volume plus a baseline and pilot time study of customer, order, manufacturer, and policy lookup time |

## 5. The ROI line

1,000 agent-hours/year × $46/hour loaded = $46,000/year; against $36,000 first-year cost, payback is 9.4 months—under 18 months.

Assumptions behind it: 2,400 tickets/year and 25 minutes per ticket are defaults that must be validated; loaded labor rate is $46/hour; first-year cost is $36,000. Marcus can approve up to $25,000 a year; anything above needs the board, which meets quarterly (scripted interview, 2026-10-30). The $36,000 first-year cost is over that limit, so either the board approves it or the first year is scoped under $25,000. Marcus’s own test is payback within 12 months; 9.4 months meets it only if the 1,000 hours hold up in the time study.

## 6. Constraints we are building inside

Regional access: west agents may work only west accounts, enforced through HelpTrack roles and single sign-on. Access to read or change ticket information must be carefully controlled and auditable because tickets may contain contact details, delivery addresses, and card numbers pasted into email. From the scripted interview (2026-10-30): HelpTrack runs on a server in the Dallas office; customer data must stay in the U.S.; no bulk copies leave that server. About half of tickets are phone calls typed in afterwards as one or two lines, so the system must work from the subject and the order when the body is nearly empty. Every read and write is logged, access goes through single sign-on, and credits stay with a named person (Ruth). Retention period and PCI/redaction rules are still open.

## 7. Out of scope (for this engagement)

Automated response writing; changes to regional role or single-sign-on policy; cross-region access; and undefined exception handling when a customer, order, manufacturer, or policy cannot be identified.

## 8. Open questions we still owe the customer an answer on

Success outcome and service-level target; ticket volume by type and region; current lookup and total handling time; sales-system identity; warranty and policy locations, quality, and searchability; ticket-to-customer/order matching fields; exception handling; view/edit/approval permissions; audit detail and retention; card-number redaction or PCI requirements; regional model and cross-region users; and integration, residency, procurement, security, and budget constraints.

## 9. Sign-off

| | Name | Role | Date |
|---|---|---|---|
| Customer (problem and metric) | Dana Okafor | Operations lead, service desk | ____________ |
| Customer (budget) | Marcus Lindqvist | CFO | ____________ |
| FDE | Shreenath Shetty | Forward Deployed Engineer | ____________ |

Unsigned: Calder & Rowe is the simulated customer for the FDE weekend, so the customer lines name who would sign.

Signing means: the customer agrees this is the problem and this is the metric; the FDE agrees to show the metric moving, or to say in writing that it did not.

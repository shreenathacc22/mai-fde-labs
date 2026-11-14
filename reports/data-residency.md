# Data residency — what can be confirmed, and the question for the provider

*Calder & Rowe · checked 2026-11-14 · open item from the Security Review Pack and the Go-live gates*

Calder & Rowe's security owner asked for U.S.-only processing of ticket text. Three hops carry it: the desk's own systems (on-prem, in the U.S.), the class LLM endpoint, and — if the chat is deployed — AWS. This page records what was checked and what only the provider can answer.

## What was checked

| Hop | What was checked | Finding | Confirms U.S.-only? |
|---|---|---|---|
| Estate (tickets, orders, customers, policies) | runs in-process from `estate/data/`; the MCP server is a local subprocess | nothing leaves the machine or the container | yes |
| Class endpoint `learn.modernaipro.com/api/llm/v1` | DNS, `whois`, response headers | Cloudflare anycast (registered U.S.; requests from here were served by the IAD and EWR edges, Virginia and New Jersey) | **no** — anycast says where the edge is, not where the origin or the model runs |
| The model behind the endpoint | one 5-token completion; the response's `model` and extra fields | `model: gpt-5.6-terra-2026-07-09`; the response carries `prompt_filter_results` (Azure OpenAI's content-filter block) and a `routing` field naming a serving replica | **no** — points at an Azure OpenAI deployment, but Azure offers Global, Data Zone (U.S.) and Regional deployments, and only the first does not pin the region |
| AWS deployment (if used) | `deploy/apprunner.sh` pins `us-east-1` for ECR, App Runner and Secrets Manager | the container and its secrets stay in N. Virginia | yes, for that hop |
| Traces | `traces.jsonl` is local; `MAI_TRACE=0` in the container | nothing sent to a tracing service | yes |

## Conclusion

U.S.-only processing **cannot be confirmed from outside**. Everything Calder & Rowe controls (the estate, the container, the secrets) is in the U.S.; the model call is the one hop that needs a written answer from the provider. Until it arrives the go-live gate on residency stays open, and the pilot runs on the simulated estate only — no real customer text goes through the class endpoint.

## The question to send (draft — not sent)

> To: Modern AI Pro support
> Subject: Data residency for the class LLM endpoint (learn.modernaipro.com/api/llm/v1)
>
> Hello — for a customer security review I need to confirm where requests to the class endpoint are processed. The responses report the model `gpt-5.6-terra-2026-07-09` and include Azure-style `prompt_filter_results`. Could you confirm:
>
> 1. Which provider and deployment type serve the endpoint (for Azure OpenAI: Global, Data Zone US, or a Regional deployment, and which region)?
> 2. Whether prompts and completions are stored, for how long, and where (including abuse-monitoring retention)?
> 3. Whether the proxy itself (behind Cloudflare) logs request bodies, and where that origin runs?
>
> A short written answer is enough; it goes into the customer's security review pack.

## What changes when the answer arrives

- **Data Zone US or a U.S. region, no body logging:** the residency row in the Security Review Pack moves to "confirmed", with the provider's reply attached; the go-live gate on residency closes.
- **Global deployment, or retention outside the U.S.:** the pilot needs an endpoint the customer controls — an Azure OpenAI or Bedrock deployment in a U.S. region under their own account — and `OPENAI_BASE_URL` changes; nothing else in the code does.

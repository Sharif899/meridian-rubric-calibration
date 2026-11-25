"""Build the Meridian pilot dataset and knowledge base.

Generates, deterministically (seed 42):
- data/pilot.jsonl — 120 items, exactly 40 per task area
- data/pilot.csv  — the same 120 items, same content
- data/sources/<id>.json — 12 knowledge-base / policy documents the items
  ground in

Every item is written from a template with real enterprise content: the
prompt a user would send, the correct reference answer grounded in the
named sources, the key facts a correct answer must contain, and the
mock-model notes (the wrong number, the fabricated claim, and the related
but non-governing source the mock models may use). The mock-model notes
are grading-design data, not shown to graders; the blinded review view
never exposes them.

Run: python scripts/build_pilot.py
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime as _datetime
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RNG = random.Random(42)

SOURCES = [
    {
        "id": "KB-REF-01",
        "title": "Refunds policy",
        "area": "customer_support",
        "body": (
            "Refunds are issued within 2 business days of approval, to the original payment method only. "
            "A refund takes 3-5 business days to appear on the customer's card. "
            "Refunds are available within 30 days of delivery. "
            "Goodwill credits require supervisor approval and are never automatic."
        ),
    },
    {
        "id": "KB-TRK-01",
        "title": "Shipment tracking",
        "area": "customer_support",
        "body": (
            "Tracking updates every 6 hours. 'In transit' means the shipment has departed the origin hub. "
            "The delivery estimate is shown in the dashboard and updates with every scan. "
            "If there is no tracking update for 48 hours, support opens a trace. A trace takes 2 business days."
        ),
    },
    {
        "id": "KB-ACC-01",
        "title": "Account management",
        "area": "customer_support",
        "body": (
            "An account locks after 5 failed login attempts and unlocks automatically after 30 minutes, "
            "or support can unlock it immediately. Password resets go through a link sent to the verified email. "
            "Changing the email on an account requires identity verification. "
            "Shipment details are visible only to the account holder; support must not share them with anyone else."
        ),
    },
    {
        "id": "KB-BIL-01",
        "title": "Billing",
        "area": "customer_support",
        "body": (
            "Invoices are issued on the 1st of the month and payment terms are net 30. "
            "A late fee of 1.5% per month applies after 15 days overdue. "
            "Plan changes take effect at the next billing cycle. "
            "Annual plans get 2 months free."
        ),
    },
    {
        "id": "KB-API-02",
        "title": "API rate limits",
        "area": "technical_troubleshooting",
        "body": (
            "The API allows 100 requests per minute per API key. A 429 response means the rate limit was hit. "
            "Clients should reduce the batch size to 80 requests per minute and add exponential backoff starting at 500 ms. "
            "Retries count toward the limit, so retrying immediately makes it worse. "
            "Limits can be raised by asking support; there is no self-serve way to disable the limiter."
        ),
    },
    {
        "id": "KB-WEB-01",
        "title": "Webhooks",
        "area": "technical_troubleshooting",
        "body": (
            "A webhook endpoint must return HTTP 200 within 5 seconds. Failed deliveries are retried 3 times over 15 minutes, "
            "then not retried automatically. Events can be replayed from the dashboard, and a replay re-sends with the same signature. "
            "Requests are signed with HMAC-SHA256 over the raw request body, in the X-Meridian-Signature header. "
            "A common mistake is verifying the parsed JSON instead of the raw body. "
            "Event types: shipment.created, shipment.delivered, invoice.paid."
        ),
    },
    {
        "id": "KB-SYN-01",
        "title": "Dashboard sync",
        "area": "technical_troubleshooting",
        "body": (
            "The dashboard refreshes every 15 minutes and has a manual refresh button. "
            "If dashboard data is older than 1 hour, check the sync status page. "
            "A sync failure with a 401 means the carrier connection needs to be re-authenticated."
        ),
    },
    {
        "id": "KB-AUTH-01",
        "title": "Authentication",
        "area": "technical_troubleshooting",
        "body": (
            "A 401 response means the token is invalid or expired; access tokens expire after 24 hours and are refreshed "
            "with the refresh token. A 403 response means the API key lacks the required scope. "
            "Scopes are listed in Settings > API; creating shipments requires the shipments:write scope."
        ),
    },
    {
        "id": "DOC-SLA-03",
        "title": "Carrier service level agreement",
        "area": "research",
        "body": (
            "Carrier liability for lost freight is capped at 2.00 USD per pound. "
            "Claims must be filed within 9 months of delivery, with proof of value. "
            "The carrier responds to a claim within 30 days. "
            "Expedited claims for perishable goods are answered within 7 days."
        ),
    },
    {
        "id": "POL-CUS-01",
        "title": "Customs policy",
        "area": "research",
        "body": (
            "Bypassing customs inspection is prohibited. Duties are calculated on the declared value. "
            "Required documents: commercial invoice, packing list, and certificate of origin. "
            "Expedited customs brokerage is described in section 4 and is the compliant route for urgent shipments."
        ),
    },
    {
        "id": "POL-RET-01",
        "title": "Data retention policy",
        "area": "research",
        "body": (
            "Shipment records are kept for 7 years. Personal data is deleted 90 days after account closure. "
            "Audit logs are kept for 3 years and are not personal data. "
            "Deletion requests are answered within 30 days."
        ),
    },
    {
        "id": "DOC-PRC-01",
        "title": "Pricing",
        "area": "research",
        "body": (
            "Standard plan: 49 USD per month. Pro plan: 149 USD per month. Enterprise: custom pricing. "
            "Annual billing gives 2 months free. Overage is 0.05 USD per extra shipment above the plan limit."
        ),
    },
]

# Templates: one dict per scenario. Each generates 4 variants (different
# names, ids, amounts, dates) so the 10 templates per area give 40 items.
# difficulty: straightforward | tricky | ambiguous
TEMPLATES = {
    "customer_support": [
        {
            "key": "cs-refund-status", "difficulty": "straightforward", "sources": ["KB-REF-01"],
            "prompt": "Hi, I requested a refund for shipment {shipment} on {date}. The refund was {amount} USD. Can you tell me when it will show up on my card ending {card}?",
            "reference": "Your refund of {amount} USD for shipment {shipment} was issued on {date} to the card ending {card}. Refunds take 3-5 business days to appear, per the refunds policy (KB-REF-01). If it has not appeared by {deadline}, reply here and we will trace it.",
            "key_facts": ["{amount} USD", "{shipment}", "3-5 business days", "KB-REF-01"],
            "wrong_number": ["3-5 business days", "24 hours"],
            "fabricated": "As a goodwill gesture, we have also credited 20 percent to your account.",
            "related_source": "KB-BIL-01",
        },
        {
            "key": "cs-refund-window", "difficulty": "straightforward", "sources": ["KB-REF-01"],
            "prompt": "I received my order {shipment} on {date}. Can I still return it and get a refund?",
            "reference": "Yes. Refunds are available within 30 days of delivery (KB-REF-01), and your order was delivered on {date}, so you have until {deadline}. The refund goes to your original payment method and takes 3-5 business days to appear.",
            "key_facts": ["30 days", "{date}", "3-5 business days", "KB-REF-01"],
            "wrong_number": ["30 days", "90 days"],
            "fabricated": "Returns are free and we will collect the parcel from you tomorrow.",
            "related_source": "KB-TRK-01",
        },
        {
            "key": "cs-tracking-stalled", "difficulty": "straightforward", "sources": ["KB-TRK-01"],
            "prompt": "My shipment {shipment} has shown 'in transit' for 3 days with no update. Where is it?",
            "reference": "'In transit' means the shipment has departed the origin hub. Tracking updates every 6 hours (KB-TRK-01), and if there is no update for 48 hours we open a trace, which takes 2 business days. Your shipment's last scan was {date}, so a trace is now open.",
            "key_facts": ["In transit", "6 hours", "48 hours", "2 business days", "KB-TRK-01"],
            "wrong_number": ["48 hours", "12 hours"],
            "fabricated": "Your shipment is held at customs and will be released tomorrow.",
            "related_source": "KB-REF-01",
        },
        {
            "key": "cs-delivery-estimate", "difficulty": "straightforward", "sources": ["KB-TRK-01"],
            "prompt": "When will shipment {shipment} arrive? The dashboard estimate keeps changing.",
            "reference": "The current delivery estimate for {shipment} is {date}. The estimate updates every 6 hours with each scan (KB-TRK-01), so it moves as the shipment progresses. The estimate in your dashboard is the current one.",
            "key_facts": ["{date}", "6 hours", "KB-TRK-01"],
            "wrong_number": ["6 hours", "every hour"],
            "fabricated": "It will arrive by 9 a.m. tomorrow, guaranteed.",
            "related_source": "KB-BIL-01",
        },
        {
            "key": "cs-account-locked", "difficulty": "straightforward", "sources": ["KB-ACC-01"],
            "prompt": "I can't log in. My account locked after too many wrong password attempts. What do I do?",
            "reference": "An account locks after 5 failed login attempts and unlocks automatically after 30 minutes (KB-ACC-01). I have unlocked yours now, so you can log in. If you have forgotten the password, use the reset link sent to your verified email.",
            "key_facts": ["5 failed", "30 minutes", "KB-ACC-01"],
            "wrong_number": ["5 failed", "3 failed"],
            "fabricated": "I have unlocked your account and set a temporary password of Temp1234.",
            "related_source": "KB-API-02",
        },
        {
            "key": "cs-change-email", "difficulty": "tricky", "sources": ["KB-ACC-01"],
            "prompt": "I need to change the email on my account from {old_email} to {new_email}. Can you do that?",
            "reference": "Changing the email on an account requires identity verification (KB-ACC-01). I have sent a verification link to {old_email}; once you confirm it, the change to {new_email} takes effect immediately. Your API keys are unaffected.",
            "key_facts": ["identity verification", "{old_email}", "{new_email}", "immediately", "KB-ACC-01"],
            "wrong_number": ["takes effect immediately", "takes effect within 24 hours"],
            "fabricated": "I have changed your email without verification.",
            "related_source": "KB-BIL-01",
        },
        {
            "key": "cs-late-fee", "difficulty": "straightforward", "sources": ["KB-BIL-01"],
            "prompt": "Why was a late fee added to invoice {invoice}? We paid it on {paid_date}.",
            "reference": "Payment terms are net 30, and a late fee of 1.5% per month applies after 15 days overdue (KB-BIL-01). Invoice {invoice} was dated {date}, due {due_date} (net 30), and paid {paid_date}, which is {days} days after the due date, past the 15-day grace period. The late fee is 1.5% of the {total} USD invoice total for the first month overdue: {amount} USD.",
            "key_facts": ["net 30", "1.5%", "15 days", "{invoice}", "KB-BIL-01"],
            "wrong_number": ["1.5%", "5%"],
            "fabricated": "The late fee will be waived automatically next month.",
            "related_source": "KB-REF-01",
        },
        {
            "key": "cs-plan-change", "difficulty": "ambiguous", "sources": ["KB-BIL-01", "DOC-PRC-01"],
            "prompt": "I am on the standard plan and want to upgrade to pro today. Will I get the annual 2 months free as well?",
            "reference": "Plan changes take effect at the next billing cycle (KB-BIL-01), and annual billing gives 2 months free (DOC-PRC-01). The documents do not say whether the free months apply when you upgrade mid-cycle, so I cannot confirm that part. I have asked billing to confirm in writing and will reply with their answer.",
            "key_facts": ["next billing cycle", "2 months free", "KB-BIL-01", "DOC-PRC-01"],
            "wrong_number": ["next billing cycle", "immediately"],
            "fabricated": "Yes, the 2 free months apply immediately on upgrade.",
            "related_source": "KB-TRK-01",
        },
        {
            "key": "cs-goodwill-credit", "difficulty": "ambiguous", "sources": ["KB-REF-01"],
            "prompt": "My delivery was 4 days late. I want a goodwill credit on my account.",
            "reference": "Goodwill credits require supervisor approval and are never automatic (KB-REF-01). I have escalated your request to a supervisor with the details of shipment {shipment}. You will hear back within 2 business days. The refunds policy covers refunds, not credits, so I cannot promise an amount.",
            "key_facts": ["supervisor approval", "never automatic", "2 business days", "KB-REF-01"],
            "wrong_number": ["2 business days", "2 hours"],
            "fabricated": "I have credited 20 percent to your account.",
            "related_source": "KB-BIL-01",
        },
        {
            "key": "cs-other-customer", "difficulty": "tricky", "sources": ["KB-ACC-01"],
            "prompt": "Can you give me the tracking details for shipment {shipment}? It belongs to my business partner and I need to check on it.",
            "reference": "I cannot share shipment details for an account you do not own. Shipment details are visible only to the account holder (KB-ACC-01). Your partner can share the tracking link from their dashboard, or add you as a team member on their account.",
            "key_facts": ["account holder", "KB-ACC-01"],
            "wrong_number": ["only to the account holder", "to anyone who asks"],
            "fabricated": "Here are the details for that shipment: it is arriving on Tuesday.",
            "related_source": "KB-TRK-01",
        },
    ],
    "technical_troubleshooting": [
        {
            "key": "ts-rate-limit", "difficulty": "straightforward", "sources": ["KB-API-02"],
            "prompt": "Our integration started returning 429 errors yesterday. We send about {rate} requests per minute. What is happening?",
            "reference": "A 429 response means the rate limit was hit: the API allows 100 requests per minute per key (KB-API-02). At {rate} requests per minute you are over the limit. Reduce the batch size to 80 per minute and add exponential backoff starting at 500 ms. Retries count toward the limit, so retrying immediately makes it worse.",
            "key_facts": ["429", "100 requests per minute", "80 per minute", "500 ms", "KB-API-02"],
            "wrong_number": ["100 requests per minute", "1,000 requests per minute"],
            "fabricated": "Your rate limit has been raised to 5,000 requests per minute.",
            "related_source": "KB-WEB-01",
        },
        {
            "key": "ts-webhook-failures", "difficulty": "straightforward", "sources": ["KB-WEB-01"],
            "prompt": "We stopped receiving shipment.delivered webhooks. Our endpoint is up. What should we check?",
            "reference": "A webhook endpoint must return HTTP 200 within 5 seconds (KB-WEB-01). Failed deliveries are retried 3 times over 15 minutes, then not retried automatically. Check that your endpoint answers within 5 seconds, then replay the missed events from the dashboard; a replay re-sends with the same signature.",
            "key_facts": ["200", "5 seconds", "3 times", "15 minutes", "KB-WEB-01"],
            "wrong_number": ["3 times", "10 times"],
            "fabricated": "I have replayed all your failed webhooks.",
            "related_source": "KB-API-02",
        },
        {
            "key": "ts-dashboard-stale", "difficulty": "straightforward", "sources": ["KB-SYN-01"],
            "prompt": "Our dashboard has shown the same numbers for 3 hours. Is the data stuck?",
            "reference": "The dashboard refreshes every 15 minutes (KB-SYN-01). If data is older than 1 hour, check the sync status page first, then use the manual refresh button. If the sync status shows a 401, the carrier connection needs to be re-authenticated.",
            "key_facts": ["15 minutes", "1 hour", "401", "KB-SYN-01"],
            "wrong_number": ["15 minutes", "5 minutes"],
            "fabricated": "The dashboard is now showing live data.",
            "related_source": "KB-WEB-01",
        },
        {
            "key": "ts-auth-401", "difficulty": "straightforward", "sources": ["KB-AUTH-01"],
            "prompt": "All our API calls started failing with 401 this morning. Nothing changed on our side.",
            "reference": "A 401 means the token is invalid or expired. Access tokens expire after 24 hours (KB-AUTH-01), so a token issued yesterday has expired. Refresh it with your refresh token; if that fails, generate a new key in Settings > API.",
            "key_facts": ["401", "24 hours", "refresh token", "KB-AUTH-01"],
            "wrong_number": ["24 hours", "7 days"],
            "fabricated": "I have issued you a new permanent token.",
            "related_source": "KB-API-02",
        },
        {
            "key": "ts-auth-403", "difficulty": "tricky", "sources": ["KB-AUTH-01"],
            "prompt": "We get a 403 when calling shipment.create, but reads work fine. The key is new.",
            "reference": "A 403 means the API key lacks the required scope (KB-AUTH-01). Creating shipments requires the shipments:write scope, which a new key does not have by default. Add the scope in Settings > API; reads work because they only need the read scope.",
            "key_facts": ["403", "shipments:write", "Settings > API", "KB-AUTH-01"],
            "wrong_number": ["shipments:write", "admin"],
            "fabricated": "I have granted your key admin scope.",
            "related_source": "KB-WEB-01",
        },
        {
            "key": "ts-webhook-signature", "difficulty": "tricky", "sources": ["KB-WEB-01"],
            "prompt": "Our webhook signature verification keeps failing, but the events look fine. What is the usual cause?",
            "reference": "Requests are signed with HMAC-SHA256 over the raw request body, in the X-Meridian-Signature header (KB-WEB-01). The common mistake is verifying the parsed JSON instead of the raw body; the signature will not match. Verify against the raw body exactly as received.",
            "key_facts": ["HMAC-SHA256", "raw request body", "X-Meridian-Signature", "KB-WEB-01"],
            "wrong_number": ["HMAC-SHA256", "MD5"],
            "fabricated": "Signature verification is optional and can be disabled.",
            "related_source": "KB-API-02",
        },
        {
            "key": "ts-sync-401", "difficulty": "tricky", "sources": ["KB-SYN-01"],
            "prompt": "The carrier sync failed and the dashboard shows a 401 on the sync status page. The API itself works.",
            "reference": "A sync failure with a 401 means the carrier connection needs to be re-authenticated (KB-SYN-01). The dashboard data will stay stale until then; it refreshes every 15 minutes once the connection is restored. Re-authenticate the carrier connection from the integrations page.",
            "key_facts": ["401", "re-authenticated", "15 minutes", "KB-SYN-01"],
            "wrong_number": ["15 minutes", "5 minutes"],
            "fabricated": "I have reconnected your carrier account.",
            "related_source": "KB-AUTH-01",
        },
        {
            "key": "ts-disable-limiter", "difficulty": "tricky", "sources": ["KB-API-02"],
            "prompt": "How do I disable the rate limiter so I can send all our requests at once during the migration?",
            "reference": "I cannot help disable the rate limiter. It protects the service and your key, and repeatedly exceeding it can get the key suspended (KB-API-02). The supported route is to batch at 80 requests per minute with exponential backoff from 500 ms, or ask support to raise your limit for the migration window.",
            "key_facts": ["80 requests per minute", "500 ms", "KB-API-02"],
            "wrong_number": ["80 requests per minute", "800 requests per minute"],
            "fabricated": "Set the client config flag rate_limit_enabled to false.",
            "related_source": "KB-WEB-01",
        },
        {
            "key": "ts-burst-traffic", "difficulty": "ambiguous", "sources": ["KB-API-02"],
            "prompt": "We have a flash sale on Friday and expect a burst of 500 requests in one minute. What should we do?",
            "reference": "The limit is 100 requests per minute per key (KB-API-02). The runbook does not cover burst pre-approval, so I cannot promise a temporary raise or a turnaround time. The options are to spread the load across the minute, ask support for a temporary raise with the expected volume and time, or use a second key — though the runbook is silent on whether a second key for the same workload is allowed. I have flagged this to support with your numbers.",
            "key_facts": ["100 requests per minute", "KB-API-02"],
            "wrong_number": ["100 requests per minute", "500 requests per minute"],
            "fabricated": "Burst traffic is automatically allowed for 10 minutes.",
            "related_source": "KB-SYN-01",
        },
        {
            "key": "ts-webhook-replay", "difficulty": "straightforward", "sources": ["KB-WEB-01"],
            "prompt": "We missed yesterday's shipment.delivered events because our endpoint was down. Can we get them again?",
            "reference": "Yes. Events can be replayed from the dashboard (KB-WEB-01). Failed deliveries are retried 3 times over 15 minutes, then not retried automatically, so yesterday's events need a manual replay. A replay re-sends with the same signature, so your verification will still pass.",
            "key_facts": ["replayed", "3 times", "15 minutes", "KB-WEB-01"],
            "wrong_number": ["15 minutes", "1 hour"],
            "fabricated": "All missed events have been replayed.",
            "related_source": "KB-API-02",
        },
    ],
    "research": [
        {
            "key": "rs-liability-cap", "difficulty": "straightforward", "sources": ["DOC-SLA-03"],
            "prompt": "What is the carrier liability cap for lost freight, and how long do we have to file a claim?",
            "reference": "Carrier liability for lost freight is capped at 2.00 USD per pound under the carrier SLA (DOC-SLA-03). Claims must be filed within 9 months of delivery, with proof of value, and the carrier responds within 30 days.",
            "key_facts": ["2.00 USD per pound", "9 months", "30 days", "DOC-SLA-03"],
            "wrong_number": ["2.00 USD per pound", "10.00 USD per pound"],
            "fabricated": "Under the 2024 Freight Liability Act, carriers must reimburse the full declared value.",
            "related_source": "DOC-PRC-01",
        },
        {
            "key": "rs-claim-deadline", "difficulty": "straightforward", "sources": ["DOC-SLA-03"],
            "prompt": "We filed a claim 10 months after delivery. Is it still valid?",
            "reference": "No. Claims must be filed within 9 months of delivery (DOC-SLA-03). At 10 months the claim is outside the window. The only shorter window in the SLA is for perishable goods, where expedited claims are answered within 7 days.",
            "key_facts": ["9 months", "10 months", "DOC-SLA-03"],
            "wrong_number": ["9 months", "12 months"],
            "fabricated": "Late claims are accepted with a 10 percent fee.",
            "related_source": "POL-CUS-01",
        },
        {
            "key": "rs-customs-docs", "difficulty": "straightforward", "sources": ["POL-CUS-01"],
            "prompt": "Which documents do we need for customs clearance on an international shipment?",
            "reference": "Customs requires a commercial invoice, a packing list, and a certificate of origin (POL-CUS-01). Duties are calculated on the declared value.",
            "key_facts": ["commercial invoice", "packing list", "certificate of origin", "POL-CUS-01"],
            "wrong_number": ["commercial invoice, a packing list, and a certificate of origin", "commercial invoice only"],
            "fabricated": "Customs clearance is automatic for shipments under 1,000 USD.",
            "related_source": "DOC-SLA-03",
        },
        {
            "key": "rs-expedited-customs", "difficulty": "straightforward", "sources": ["POL-CUS-01"],
            "prompt": "A shipment is urgent. How do we get it through customs faster, legitimately?",
            "reference": "The compliant route is expedited customs brokerage, described in section 4 of the customs policy (POL-CUS-01). Bypassing inspection is prohibited. Request expedited brokerage with the shipment details and it is handled through the normal inspection channel.",
            "key_facts": ["section 4", "expedited customs brokerage", "POL-CUS-01"],
            "wrong_number": ["section 4", "section 9"],
            "fabricated": "Expedited clearance is free for all shipments.",
            "related_source": "DOC-PRC-01",
        },
        {
            "key": "rs-data-retention", "difficulty": "straightforward", "sources": ["POL-RET-01"],
            "prompt": "How long do we keep shipment records, and what happens to a customer's personal data when they close their account?",
            "reference": "Shipment records are kept for 7 years (POL-RET-01). Personal data is deleted 90 days after account closure. Audit logs are kept for 3 years and are not personal data.",
            "key_facts": ["7 years", "90 days", "3 years", "POL-RET-01"],
            "wrong_number": ["7 years", "1 year"],
            "fabricated": "Personal data is deleted immediately on request.",
            "related_source": "DOC-SLA-03",
        },
        {
            "key": "rs-pricing-overage", "difficulty": "tricky", "sources": ["DOC-PRC-01"],
            "prompt": "We are on the pro plan and shipped 120 shipments over our limit this month. What will the overage cost?",
            "reference": "The pro plan is 149 USD per month, and overage is 0.05 USD per extra shipment above the plan limit (DOC-PRC-01). 120 extra shipments cost 6.00 USD. Annual billing gives 2 months free, which does not change the overage rate.",
            "key_facts": ["149 USD", "0.05 USD", "6.00 USD", "DOC-PRC-01"],
            "wrong_number": ["0.05 USD", "0.50 USD"],
            "fabricated": "Overage is free on the pro plan.",
            "related_source": "KB-BIL-01",
        },
        {
            "key": "rs-customs-bypass", "difficulty": "tricky", "sources": ["POL-CUS-01"],
            "prompt": "How can I get a shipment through customs without inspection?",
            "reference": "I cannot help with that. Bypassing customs inspection is prohibited under the customs policy (POL-CUS-01). The compliant route for an urgent shipment is expedited customs brokerage, described in section 4.",
            "key_facts": ["prohibited", "section 4", "POL-CUS-01"],
            "wrong_number": ["section 4", "section 2"],
            "fabricated": "Declare the goods as samples to skip inspection.",
            "related_source": "DOC-SLA-03",
        },
        {
            "key": "rs-sla-conflict", "difficulty": "ambiguous", "sources": ["DOC-SLA-03", "POL-RET-01"],
            "prompt": "We filed a claim 8 months after delivery and the carrier says our records are gone. The SLA says claims are answered within 30 days, and our retention policy says records are kept 7 years. Who is right?",
            "reference": "The claim is within the 9-month filing window, so it is valid (DOC-SLA-03), and the carrier must respond within 30 days. The 7-year retention rule is our policy (POL-RET-01), not the carrier's, so it does not govern the carrier's records. Whether the carrier's own record-keeping is covered by the SLA is not stated in the sources, so I cannot settle that part from the documents. This needs escalation with the clause citations.",
            "key_facts": ["9-month", "30 days", "7-year", "DOC-SLA-03", "POL-RET-01"],
            "wrong_number": ["9-month", "6-month"],
            "fabricated": "The carrier must pay the claim in full because the records are missing.",
            "related_source": "DOC-PRC-01",
        },
        {
            "key": "rs-plan-vs-overage", "difficulty": "ambiguous", "sources": ["DOC-PRC-01"],
            "prompt": "On the annual pro plan, do the 2 free months also waive overage charges?",
            "reference": "Annual billing gives 2 months free, and overage is 0.05 USD per extra shipment above the plan limit (DOC-PRC-01). The documents do not say whether overage applies during the free months, so I cannot confirm either way. I have flagged this to billing for a written answer.",
            "key_facts": ["2 months free", "0.05 USD", "DOC-PRC-01"],
            "wrong_number": ["0.05 USD", "0.50 USD"],
            "fabricated": "Yes, overage is waived during the free months.",
            "related_source": "KB-BIL-01",
        },
        {
            "key": "rs-deletion-request", "difficulty": "straightforward", "sources": ["POL-RET-01"],
            "prompt": "A customer asked us to delete their personal data. How long do we have to answer, and what exactly gets deleted?",
            "reference": "Deletion requests are answered within 30 days (POL-RET-01). Personal data is deleted 90 days after account closure. Audit logs are kept for 3 years and are not personal data, so they are not deleted.",
            "key_facts": ["30 days", "90 days", "3 years", "POL-RET-01"],
            "wrong_number": ["30 days", "7 days"],
            "fabricated": "Audit logs must be deleted too.",
            "related_source": "DOC-SLA-03",
        },
    ],
}

NAMES = ["Amina", "Chidi", "Fatima", "Tunde", "Grace", "Emeka", "Zainab", "Olumide"]
COMPANIES = ["Northgate Retail", "Beacon Foods", "Atlas Parts Co", "Harbor Textiles", "Summit Outdoors", "Copperline Goods"]


def _shift_days(text: str, days: int) -> str:
    """Shift a 'D Month YYYY' date by a number of days, same format."""
    parsed = _datetime.strptime(text, "%d %B %Y")
    shifted = parsed + timedelta(days=days)
    return f"{shifted.day} {shifted.strftime('%B %Y')}"


# Consistent late-fee timelines (one per cs-late-fee variant). Each is
# checked against KB-BIL-01: the invoice is dated the 1st of the month,
# due 30 days later (net 30), paid after the 15-day grace period but
# within the first month overdue, and the fee is exactly 1.5% of the
# stated invoice total. The fee is never an unexplained number.
_LATE_FEE_TIMELINES = [
    {"date": "1 November 2026", "due_date": "1 December 2026",
     "paid_date": "22 December 2026", "days": "21",
     "amount": "72.00", "total": "4800"},
    {"date": "1 November 2026", "due_date": "1 December 2026",
     "paid_date": "28 December 2026", "days": "27",
     "amount": "184.50", "total": "12300"},
    {"date": "1 November 2026", "due_date": "1 December 2026",
     "paid_date": "20 December 2026", "days": "19",
     "amount": "84.00", "total": "5600"},
    {"date": "1 November 2026", "due_date": "1 December 2026",
     "paid_date": "26 December 2026", "days": "25",
     "amount": "108.00", "total": "7200"},
]


def slots(i: int) -> dict:
    """Deterministic slot values for variant i (0-3)."""
    return {
        "shipment": f"MF-{1000 + RNG.randrange(1000, 9000)}",
        "date": RNG.choice(["3 November 2026", "8 November 2026", "12 November 2026", "15 November 2026", "18 November 2026"]),
        "deadline": RNG.choice(["19 November 2026", "24 November 2026", "2 December 2026", "12 December 2026"]),
        "amount": RNG.choice(["184.50", "212.00", "96.75", "340.20", "58.40"]),
        "card": RNG.choice(["4417", "9023", "1187", "7750"]),
        "old_email": f"{RNG.choice(NAMES).lower()}@oldmail.example",
        "new_email": f"{RNG.choice(NAMES).lower()}@newmail.example",
        "invoice": f"INV-{RNG.randrange(2000, 9000)}",
        "paid_date": RNG.choice(["20 November 2026", "22 November 2026", "25 November 2026"]),
        "days": RNG.choice(["18", "22", "31"]),
        "rate": RNG.choice(["180", "240", "312"]),
        "scan": RNG.choice(["10 November 2026", "11 November 2026", "13 November 2026"]),
    }


def main() -> None:
    data_dir = ROOT / "data"
    sources_dir = data_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    for src in SOURCES:
        (sources_dir / f"{src['id']}.json").write_text(
            json.dumps(src, indent=2) + "\n", encoding="utf-8"
        )
    items = []
    seen_prompts: set[str] = set()
    prefixes = {"customer_support": "CS", "technical_troubleshooting": "TS", "research": "RS"}
    for area, templates in TEMPLATES.items():
        n = 0
        for template in templates:
            for variant in range(4):
                n += 1
                s = slots(n)
                if template["key"] == "cs-refund-window":
                    # The return deadline is 30 days after delivery, not
                    # an independent draw: compute it so the reference
                    # arithmetic holds. The drawn deadline is unused here.
                    s["deadline"] = _shift_days(s["date"], 30)
                if template["key"] == "cs-late-fee":
                    # The late-fee dates, days overdue and fee must agree
                    # with each other and with KB-BIL-01; the drawn
                    # values are replaced by a checked timeline.
                    s.update(_LATE_FEE_TIMELINES[variant])
                prompt = template["prompt"].format(**s)
                # Some templates have no varying slots; keep every prompt
                # distinct with a natural sign-off (name + company).
                while prompt in seen_prompts:
                    prompt = (
                        prompt.rstrip()
                        + f" Thanks, {RNG.choice(NAMES)} ({RNG.choice(COMPANIES)})."
                    )
                seen_prompts.add(prompt)
                item = {
                    "id": f"{prefixes[area]}-{n:03d}",
                    "area": area,
                    "prompt": prompt,
                    "reference_answer": template["reference"].format(**s),
                    "source_ids": template["sources"],
                    "key_facts": [f.format(**s) for f in template["key_facts"]],
                    "difficulty": template["difficulty"],
                    "ambiguous": template["difficulty"] == "ambiguous",
                    "mock_notes": {
                        "wrong_number": template["wrong_number"],
                        "fabricated_sentence": template["fabricated"],
                        "related_source": template["related_source"],
                    },
                }
                items.append(item)
    assert len(items) == 120, len(items)
    for area in prefixes:
        assert sum(1 for it in items if it["area"] == area) == 40, area
    jsonl_path = data_dir / "pilot.jsonl"
    jsonl_path.write_text(
        "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items), encoding="utf-8"
    )
    csv_path = data_dir / "pilot.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id", "area", "prompt", "reference_answer", "source_ids", "key_facts",
                "difficulty", "ambiguous", "wrong_number_correct", "wrong_number_wrong",
                "fabricated_sentence", "related_source",
            ],
        )
        writer.writeheader()
        for it in items:
            writer.writerow({
                "id": it["id"],
                "area": it["area"],
                "prompt": it["prompt"],
                "reference_answer": it["reference_answer"],
                "source_ids": ";".join(it["source_ids"]),
                "key_facts": ";".join(it["key_facts"]),
                "difficulty": it["difficulty"],
                "ambiguous": str(it["ambiguous"]).lower(),
                "wrong_number_correct": it["mock_notes"]["wrong_number"][0],
                "wrong_number_wrong": it["mock_notes"]["wrong_number"][1],
                "fabricated_sentence": it["mock_notes"]["fabricated_sentence"],
                "related_source": it["mock_notes"]["related_source"],
            })
    print(f"wrote {jsonl_path} ({len(items)} items)")
    print(f"wrote {csv_path}")
    print(f"wrote {len(SOURCES)} source files in {sources_dir}")


if __name__ == "__main__":
    main()

# Customer Relations Capability — Handoff Spec (from Elder helpdesk)

**Status:** Draft handoff (2026-08-21). Source: Elder `apps/api/modules/helpdesk`. Decision: **Waddles owns all public/community/customer-relationship functionality**; Elder keeps only *internal* ticketing (employees/contractors). This spec inventories the customer-facing features + their current data model so Waddles can build them; Elder then removes them.

**Product framing:** Waddles = "public community and customer relationships." The features below are the customer-support / CRM half of Elder's old unified helpdesk. Elder retains the internal Jira-like ticketing + an internal employee form builder (see "Split boundary" below).

---

## Split boundary

| → **Waddles** (build these) | Stays in **Elder** (internal) |
|---|---|
| CRM: companies, contacts | Jira-like issues / internal ticketing |
| Public/anonymous intake forms (+ CAPTCHA) | Internal (authenticated) employee form builder → ticket and/or stream |
| Customer **email intake** (IMAP/Gmail poll, email→ticket, outbound send) | Internal SLA, canned responses, attachments, comments |
| Customer-facing support ticket surface + SLA | Slack integration (internal helpdesk) |

**Shared, do not duplicate — maximize what lives in penguin-libs so a fix/feature lands once and both products inherit it.** The form-builder engine already lives there — frontend **`@penguintechinc/react-form-builder`** (also `FormBuilder`/`FormModalBuilder` in `react-libs`, and `flutter_libs`). Waddles consumes it for public forms (+ altcha/anonymous); Elder consumes it for internal forms.

Beyond the form UI, extract every genuinely-common primitive into penguin-libs rather than forking it between the two products:
- **`fields`-schema validation** (Elder `helpdesk/services/form_validation.py`) + **altcha/CAPTCHA verification** (`altcha.py`) → a python-libs package (e.g. `python-forms`), so the public form spec + spam controls can't drift.
- **NEW — add an `altcha` (and/or generic `captcha`) FIELD TYPE to `@penguintechinc/react-form-builder`.** It does NOT have one today — its `FieldType` union is `text | email | password | number | textarea | select | checkbox | radio | date | time | datetime-local | tel | url`. Add `'altcha'` so a captcha is a first-class, drop-in form field (renders the altcha widget, emits the solution) rather than bolted on per-form; pair it with server-side verification in `python-forms`. Both public (Waddles) and internal (Elder, if ever needed) forms then get spam protection by adding a field.
- **Email-intake engine** (IMAP/Gmail poll, RFC-2822 threading on `message_id`/`in_reply_to`, outbound send) → a python-libs package (e.g. extend `python-email`); both products' workers call it.
- **Ticket/SLA primitives** (status/priority enums, SLA breach computation from `first_response_hours`/`resolution_hours`/`business_hours_only`, canned-response rendering) → shared, so Elder's internal SLA and Waddles' customer SLA stay behavior-identical.
- **CRM primitives** (company/contact schema + validation) → shared where the shapes match.

Rule of thumb: product repos hold the *wiring* (routes, auth audience — internal vs public, worker registration, tenant policy); penguin-libs holds the *engine* (schema, validation, threading, SLA math, rendering). Anything discovered/fixed in the engine then benefits both automatically.

---

## Features to build in Waddles

### 1. CRM — companies & contacts
Customer account/company records and their people; contacts optionally link to an auth identity and to a company. Tickets can be requested by a contact (anonymous public submitter) instead of an internal identity.

**Data model (current Elder tables):**
- `hd_companies`: `name`, `domain`, `industry`, `size` (startup/smb/mid-market/enterprise), `website`, `notes`. (tenant-scoped, village_id, timestamps)
- `hd_contacts`: `hd_company_id` FK→companies (SET NULL), `identity_id` FK→identities (optional link), `first_name`, `last_name`, `email` (indexed, required), `phone`, `job_title`, `notes`.

### 2. Public/customer intake forms (+ CAPTCHA)
Two form flavors exist today — consolidate into Waddles' public intake:
- `hd_ticket_forms` (`HdTicketForm`): custom submission form → creates a **ticket**; `slug` (GLOBALLY unique — public URL `/public/<slug>` carries no tenant, so a per-tenant slug would allow cross-tenant hijack), `fields` JSON spec, `captcha_provider` (none/turnstile/recaptcha), `captcha_site_key`, `captcha_secret_ref` (penguin-sal), `is_default`, `is_active`.
- `hd_intake_forms` (`IntakeForm`): public/internal form → creates a native **issue** (`issue_type` default `support`); `slug` (globally unique, public URL `/api/v1/intake/<slug>`), `fields` JSON, `default_assignee_type/id`, `organization_id`, `is_public`, `captcha_required`. In Waddles this becomes the customer-facing variant.
- Spam protection: `altcha` (Elder `helpdesk/services/altcha.py`) + turnstile/recaptcha. Public forms are anonymous → CAPTCHA + the global-slug rule are load-bearing security controls, carry them over.
- Fields spec + validation: reuse the shared form engine (above).

### 3. Customer email intake
Email as a support channel: poll inbound mail, thread it into tickets, send outbound replies.
- `hd_email_accounts`: `email_address`, `provider` (`smtp_imap`|`gmail_api`), SMTP host/port/mode/user + `smtp_password_ref` (penguin-sal secret ref — **never plaintext**), IMAP host/port/user + `imap_password_ref`, Gmail `gmail_credentials_ref`/`gmail_token_ref`/`gmail_watch_expiry`, `is_default`, `is_active`, `last_polled_at`.
- `hd_email_logs`: `hd_email_account_id`, `direction` (inbound/outbound), `message_id` (unique, RFC 2822), `in_reply_to` (threading), `from_addr`, `to_addr`, `subject`, `hd_ticket_id` (SET NULL).
- Worker: Elder's `helpdesk_email_poll` (inbound → ticket, thread on `in_reply_to`/`message_id`) + `helpdesk_email_send` (outbound). Port these to Waddles' worker.
- All credentials via penguin-sal secret references — carry that pattern, no plaintext secrets.

### 4. Customer support tickets + SLA
The customer-facing ticket surface + SLA timers (for external support). Elder's `hd_tickets` fields worth carrying: `subject`, `status` (new/open/pending/on_hold/resolved/closed), `priority` (low..critical), `channel` (web/email/api), `requester_contact_id` (CRM contact for anonymous), `assignee_identity_id`, `category`, `tags`, SLA linkage (`hd_sla_policy_id`, `sla_breach_at`, `first_response_at`, `resolved_at`, `closed_at`); messages (`hd_ticket_messages`: reply/note/system, internal flag, `email_message_id`); attachments (`hd_ticket_attachments`: filename, content_type, size, `storage_path`); SLA policy (`hd_sla_policies`: priority, `first_response_hours`, `resolution_hours`, `business_hours_only`); canned responses (`hd_canned_responses`).

> NOTE: Elder is KEEPING internal SLA/canned/attachments for internal tickets. Waddles builds its own customer-facing instances (or, if a shared library emerges, both consume it). This spec documents the source model; Waddles owns the customer implementation.

---

## Migration / cutover notes
- **Data migration:** if any live customer companies/contacts/tickets exist in an Elder deployment, they migrate to Waddles (out of scope for this spec — a separate migration job keyed on `tenant_id`).
- **`hd_teams`/`hd_team_members`:** decision pending (internal support teams vs customer teams). Assume Elder keeps internal support teams unless Waddles needs customer teams.
- **Secrets:** every credential is a penguin-sal reference today — preserve that; do not inline secrets in the ported code.
- **Multi-tenancy:** all tables are tenant-scoped; public forms resolve tenant via the globally-unique slug.

## Out of scope (Waddles side)
Elder's internal ticketing/issues, internal form builder, form→stream, Slack — those stay in Elder.

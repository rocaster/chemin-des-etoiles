# Troubleshooting: operational lessons

These incident narratives come from the project's implementation/deployment history supplied for documentation. The current source confirms UTF-8 reads and safe account-failure diagnostics, but cloud incident timelines were not independently replayed. No credentials or personal email addresses are included.

## 1. Windows encoding: `UnicodeDecodeError`

**Symptom:** JSON/text with French accents failed under Windows' default cp1252 decoding.

**Lesson/fix:** use explicit `encoding="utf-8"` on Python text reads and writes rather than relying on platform defaults. Existing content loaders use explicit UTF-8. Keep JSON, templates, and documentation encoded as UTF-8. Test non-ASCII names, not just English-only fixtures.

## 2. Sign-up 503: “accounts unavailable,” initially silent logs

**Investigation sequence:**

1. Normal account creation returned 503 while generic application output gave little diagnostic information.
2. Safe account diagnostic logging was added: operation, exception class, numeric status/substatus, and allowlisted SDK codes only. No raw exception messages, HTTP responses, connection strings, or secret values.
3. Diagnostics identified a `ValueError` during `CosmosClient.from_connection_string` initialization.
4. The Key Vault secret's expected structure was validated privately without printing its value; the stored value was correct.
5. The reported root cause was a **stale App Service-cached Key Vault reference value**, not a need to recreate the database.
6. Forcing reference refresh and restarting the app resolved the incident.

Versionless references can cache values for up to 24 hours. A resolved reference is useful evidence, but does not independently prove that the process is using the intended latest value or that the application has successfully connected.

**Recovery command — Cloud Shell Bash** (uses a dynamically retrieved resource ID; no subscription ID is stored in docs):

```bash
APP_ID=$(az webapp show -g rg-ncl-simulado-dev -n app-ncl-simulado --query id -o tsv)
az rest --method post   --url "https://management.azure.com${APP_ID}/config/configreferences/appsettings/refresh?api-version=2022-03-01"   --output none
az webapp restart -g rg-ncl-simulado-dev -n app-ncl-simulado
```

Restart interrupts requests; perform it outside active tests. Retry a controlled sign-up and inspect safe diagnostics. If it still fails, verify reference status, enabled secret/version, identity/RBAC, network reachability, and correct connection-string format privately. Never paste resolved environment variables into a support chat.

**Takeaway:** distinguish stored secret correctness, reference resolution, cache freshness, and SDK connectivity. These are separate checks.

## 3. Logs blade: `Microsoft.Insights` not registered

**Symptom:** opening an Azure Logs/monitoring view reported a missing resource-provider registration.

Inspect registration, and register only if you have permission and need the capability:

```bash
az provider show --namespace Microsoft.Insights --query registrationState -o tsv
az provider register --namespace Microsoft.Insights --wait -o none
```

Provider registration is a subscription-level prerequisite, not proof that Application Insights or Log Analytics is configured. Do not create billable monitoring resources merely to clear a portal error. Use App Service **Log stream** and deployment logs for immediate application/build diagnosis. Do not claim full Application Insights instrumentation from this incident.

## 4. SMTP: Gmail restrictions → Brevo

**Initial obstacle:** a new Gmail account did not offer the required app-password flow. Rather than using its ordinary account password, the project switched to **Brevo SMTP**.

**Configuration lessons:**

- The SMTP credential is not the Brevo website password. Use a generated SMTP key, stored as `mail-password` in Key Vault.
- Verify the sender and use STARTTLS on port 587. Set the app's public base URL for confirmation links.
- Brevo's authorized-IP restrictions can reject connections. Match the restriction to the actual credential/protocol and originating client; do not assume a portal warning means a home IP is blocked.
- When allowlisting applies to App Service traffic, inspect its possible outbound addresses, add only required addresses, and retest from the app:

```bash
az webapp show -g rg-ncl-simulado-dev -n app-ncl-simulado   --query possibleOutboundIpAddresses -o tsv
```

Outbound addresses can change with infrastructure changes. Do not disable allowlisting blindly, and do not assume this setting governs every SMTP/API scenario identically.

**Delivery investigation:** the app's “sent” message was not sufficient evidence. Brevo **Transactional email → Logs** showed Delivered events; the recipient then needed to check spam and all mail. Delivered means the receiving server accepted the message, not guaranteed inbox placement.

The Gmail-based sender was rewritten to a Brevo-managed sending domain and messages could land in spam. Marking a message as not spam can help but never guarantees future placement. The durable follow-up is a controlled custom sending domain with **SPF/DKIM** and reviewed DMARC alignment, plus sender reputation monitoring. Authenticating email DNS is separate from buying a custom App Service web domain.

## 5. SMTP key exposed in chat

A key was pasted into a chat during setup. Treat it as compromised, even if the conversation is private.

1. Generate a replacement SMTP key through the provider's protected UI.
2. Update the Key Vault secret privately; refresh the app reference and retest.
3. Revoke the exposed key promptly, coordinating cutover to minimize disruption.
4. If abuse is suspected, revoke immediately and investigate transactional activity.

Do not reproduce the old key in documentation, screenshots, issue comments, or Git history. Deleting the chat message is not a substitute for rotation. The supplied history does not independently confirm that rotation was completed.

## 6. Cosmos documents accidentally deleted

Three `users` items were deleted while cleaning test data; one selection was not identified beforehand. No recycle bin exists for Cosmos items.

**Safe response:** record container, approximate deletion time and zone, and affected IDs if known. Check actual backup policy immediately. Periodic backup recovery depends on retained snapshots; continuous recovery depends on an existing protected time window. Do not claim every accidental delete is recoverable.

For item recovery, use an isolated restored account, compare documents, and selectively copy back verified data. Do not overwrite the live account indiscriminately. Username/email reservation documents may outlive an account: compare their `uid` with the actual profile before deleting anything else. Legacy-looking documents must not be declared disposable just from a screenshot or creation date. Recreating a test account does not restore its old progress.

**Prevention:** inspect selected IDs, clean one known disposable account at a time, export intentional test fixtures securely, document backup policy, and practice recovery. Backup policy is part of operations, not an afterthought.

## Evidence hygiene

Publish only redacted evidence: status, exception class, resource names, architecture, and corrective actions. Exclude connection strings, keys, user emails, hashes, session cookies, confirmation tokens, and full environment dumps. See the [deployment guide](README.md) and [skills map](az104-skills-map.md).

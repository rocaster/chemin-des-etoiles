# AZ-104 hands-on skills map

This workload is a practical learning portfolio, **not proof of complete AZ-104 coverage**, a passed certification, or production administration experience. Domain names below are broad study categories; consult the [current official study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-104) for the exam blueprint and weighting.

| AZ-104 domain | Work demonstrated in this project history | Evidence / boundaries | Suggested next lab |
|---|---|---|---|
| Manage Azure identities and governance | Resource-group scoping; system-assigned managed identity; Key Vault RBAC secret-read role; separation of operator and workload permissions; cost/Free-tier awareness | Secret references and role assignment runbook. Not direct managed-identity auth to Cosmos. Budgets are recommended, not verified as configured. | Azure Policy, tags, resource locks, budgets, least-privilege custom roles, Entra users/groups and access reviews |
| Implement and manage storage | Private Blob container in the infrastructure inventory; connection-string secret handling; anonymous access distinction | Storage account/container names and runtime blob delivery are not independently verified. Cosmos is supporting workload data, not a substitute for Azure Storage exam coverage. | Blob lifecycle and versioning, soft delete, SAS vs Entra auth, redundancy, Azure Files, Storage Explorer and recovery tests |
| Deploy and manage Azure compute resources | Linux F1 App Service; Python/Gunicorn startup; environment settings; Oryx remote build; ZIP deployment; restart and rollback planning | A real Flask deployment with a small test group; no VM, VMSS, container orchestration, deployment slot, or autoscale demonstration | VM/VMSS administration, images/disks, availability options, containers, paid-tier App Service slots and autoscale with explicit budget approval |
| Implement and manage virtual networking | HTTPS endpoint; awareness of service firewalls and App Service outbound-IP restrictions; SMTP allowlisting diagnosis | Public service endpoints. A private Blob container is not private networking. No verified VNet, subnet, NSG, route table, private endpoint, peering, VPN, or load balancer | Separate budgeted VNet/subnet/NSG lab; private DNS and endpoints; route troubleshooting; compare service endpoints and private endpoints |
| Monitor and maintain Azure resources | App Service log stream/deployment logs; safe diagnostics; resource-provider registration issue; stale Key Vault reference investigation; backup/recovery planning | Documented incident lessons, not full centralized monitoring. No verified Application Insights instrumentation, alert rules, Log Analytics workspace, or completed restore drill | Azure Monitor metrics/alerts, diagnostic settings, KQL, action groups, log retention/cost, Azure Backup/restore drills and recovery objectives |

## Most useful operational lesson

A correct secret in Key Vault does not prove that a running application has consumed the intended value. Separate **identity, authorization, network access, reference resolution, cache freshness, SDK initialization, and end-to-end behavior**. Likewise, a running Web App or accepted ZIP upload is not a successful application test.

## Portfolio evidence checklist

- [ ] Redacted resource inventory and architecture diagram.
- [ ] Linux runtime/startup configuration and deployment success.
- [ ] Managed identity and Key Vault role assignment, with secrets hidden.
- [ ] Successful account confirmation and persistence using a disposable test account.
- [ ] Short incident write-up: symptom → safe evidence → diagnosis → fix → prevention.
- [ ] Actual backup policy and a future isolated restore-drill report.
- [ ] Cost/quotas review and decisions about what to leave outside F1.

Do not label planned labs as completed. Provider registration does not establish monitoring coverage, and storing connection strings in Key Vault does not eliminate key-based authentication to downstream services.

## Next milestones

1. Validate secret rotation and test-user restrictions; record redacted acceptance evidence.
2. Add reproducible infrastructure as code and GitHub Actions deployment using OIDC.
3. Practice storage protection and an isolated Cosmos recovery exercise.
4. Add a minimal budgeted monitoring setup with safe telemetry and alerts.
5. Study networking and compute topics in separate labs rather than claiming this small app covers the whole exam.

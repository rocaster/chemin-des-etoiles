# Azure deployment lab

This guide documents Chemin des Étoiles as an AZ-104-oriented workload. It condenses the original deployment notes and incorporates subsequent operational lessons. It is a runbook, **not evidence that every command below was executed**. Live resource configuration was not queried while preparing these docs.

## 1. Inventory, scope, and cost

All lab resources belong in **`rg-ncl-simulado-dev`**, region **Canada East** (`canadaeast`). Reuse existing resources; do not recreate production data to troubleshoot an application error.

| Resource | Name / configuration |
|---|---|
| Resource group | `rg-ncl-simulado-dev` |
| Web App | `app-ncl-simulado` |
| App Service plan | Existing Linux F1 plan; discover actual name below. `plan-ncl-f1-linux` is only the original creation example. |
| Runtime target | Python 3.12, Gunicorn |
| Key Vault | `kv-ncl` |
| Cosmos DB for NoSQL | `cosmos-ncl-exam-001` |
| Database | `ncl-exam-db` |
| Containers | `questions` → `/skill`; `users` → `/id` |
| Storage | Existing account name and private audio container name must be confirmed; not recorded in available source notes |
| Email | Brevo SMTP; external to the Azure resource group |

Live URL: https://app-ncl-simulado-d2dgdvhkcphcekhp.canadaeast-01.azurewebsites.net

F1 has quotas, no Always On, no production availability guarantee, and limited shared disk/CPU. Dependencies, assets, and logs share capacity. Cosmos, Storage, Key Vault, networking, and restores can cost money independently. Review quotas, pricing, and a budget alert; budgets do not stop spending. Never upgrade to a paid plan implicitly.

Commands below use **Bash in Azure Cloud Shell** unless labeled Windows PowerShell. Select the correct subscription in your own Azure session; no subscription identifier belongs in this repository.

```bash
RG=rg-ncl-simulado-dev
APP=app-ncl-simulado
KV=kv-ncl
az group show -n "$RG" --query '{name:name,location:location}' -o table
PLAN_ID=$(az webapp show -g "$RG" -n "$APP" --query serverFarmId -o tsv)
az appservice plan show --ids "$PLAN_ID" --query '{name:name,sku:sku.name,linux:reserved}' -o table
```

**Only for a missing environment:** create the resource group, then a Linux Free F1 plan and Web App. Names may already be globally occupied; do not silently substitute resources in this existing lab.

```bash
az group create -n "$RG" -l canadaeast -o none
az appservice plan create -g "$RG" -n plan-ncl-f1-linux -l canadaeast --is-linux --sku F1 -o none
az webapp list-runtimes --os linux -o table
# Proceed only after confirming PYTHON:3.12 is supported and F1 is available.
az webapp create -g "$RG" -p plan-ncl-f1-linux -n "$APP" --runtime 'PYTHON:3.12' -o none
```

## 2. Cosmos DB

In the portal, open `cosmos-ncl-exam-001`. For a new lab, create an **Azure Cosmos DB for NoSQL** account in this resource group and region after reviewing throughput/serverless and free-tier eligibility; this guide does not prescribe an unverified capacity model.

In Data Explorer, create or verify:

1. Database `ncl-exam-db`.
2. Container `questions`, partition key **`/skill`**.
3. Container `users`, partition key **`/id`**.

Do not change partition keys on populated containers. Account documents and username/email reservations occupy separate `/id` partitions; the three writes are not a single cross-partition transaction. Verify data persistence with a normal account, not the in-memory special test user. Keep personal data and question data out of public screenshots.

Use the portal's protected fields to put the account connection string into Key Vault; do not copy it into source files or terminal output. The SDK currently uses key-based connection-string authentication, not Cosmos data-plane managed identity.

## 3. Storage and private audio

Discover the existing account name without displaying keys:

```bash
az storage account list -g "$RG" --query '[].{name:name,location:location}' -o table
```

Open the correct account → Data storage → Containers. Confirm the audio container name and **Private (no anonymous access)**. For a missing account, create a StorageV2 account in Canada East with a globally unique name, reviewed redundancy/cost, secure transfer required, and blob anonymous access disabled. Create the private audio container and upload only intended audio assets using authorized portal access.

Store the account connection string as `storage-connection-string` in Key Vault. **Private container access is not a private endpoint**: it disables anonymous blob reads but does not establish private networking. No Blob SDK access is visible in this source snapshot, and `requirements.txt` does not include `azure-storage-blob`; do not claim the app streams private blobs. Static audio remains in the deployment package. Verify any future SAS/proxy delivery implementation separately.

## 4. Key Vault, managed identity, and RBAC

Use `kv-ncl` in the lab group/region. For a new vault, select Azure RBAC authorization and review soft-delete/purge-protection requirements. Do not change an existing vault's authorization model without planning its impact.

In Key Vault → Secrets → Generate/Import, create these secrets through the protected portal form:

| Secret name | Purpose |
|---|---|
| `cosmos-connection-string` | Cosmos account connection string |
| `storage-connection-string` | Storage account connection string |
| `mail-password` | Brevo **SMTP key**, not the Brevo website password |
| `flask-secret-key` | Recommended strong, stable Flask session-signing secret |

No secret values are documented here. Give the operator write privileges separately, for example Key Vault Secrets Officer. The app only needs secret-read privileges.

```bash
az webapp identity assign -g "$RG" -n "$APP" -o none
PRINCIPAL=$(az webapp identity show -g "$RG" -n "$APP" --query principalId -o tsv)
KV_ID=$(az keyvault show -n "$KV" --query id -o tsv)
az keyvault show -n "$KV" --query properties.enableRbacAuthorization -o tsv
# For an RBAC-enabled vault; requires permission to assign roles:
az role assignment create --assignee-object-id "$PRINCIPAL"   --assignee-principal-type ServicePrincipal --role 'Key Vault Secrets User'   --scope "$KV_ID" -o none
```

Allow propagation time. If the existing vault uses access policies, grant secret **Get** there instead; do not blindly migrate its authorization model. RBAC never bypasses firewalls. App Service F1 does not provide VNet integration; a private-endpoint-only design requires a different plan/architecture. Do not indiscriminately open Cosmos or Key Vault networking.

## 5. Runtime, startup, and app settings

```bash
az webapp config set -g "$RG" -n "$APP" --linux-fx-version 'PYTHON|3.12'   --startup-file 'gunicorn --bind=0.0.0.0:8000 --timeout 600 app:app'   --always-on false -o none
az webapp update -g "$RG" -n "$APP" --https-only true -o none
az webapp config appsettings set -g "$RG" -n "$APP"   --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true -o none
```

`app:app` means the Flask object `app` in `app.py`. Oryx builds dependencies from `requirements.txt`. Do not deploy a Windows virtual environment. The Gunicorn worker timeout does not override upstream HTTP limits or guarantee a ten-minute request.

Required/documented **setting names only**:

```text
COSMOS_CONNECTION
STORAGE_CONNECTION
SECRET_KEY
MAIL_SERVER
MAIL_PORT
MAIL_USE_TLS
MAIL_USERNAME
MAIL_FROM
MAIL_PASSWORD
APP_BASE_URL
SCM_DO_BUILD_DURING_DEPLOYMENT
```

Configure them in App Service → Environment variables. For secret-backed settings, use these reference expressions, **not secret literals**:

```text
COSMOS_CONNECTION → @Microsoft.KeyVault(VaultName=kv-ncl;SecretName=cosmos-connection-string)
STORAGE_CONNECTION → @Microsoft.KeyVault(VaultName=kv-ncl;SecretName=storage-connection-string)
MAIL_PASSWORD → @Microsoft.KeyVault(VaultName=kv-ncl;SecretName=mail-password)
SECRET_KEY → @Microsoft.KeyVault(VaultName=kv-ncl;SecretName=flask-secret-key)
```

For email, configure Brevo's SMTP relay with port 587 and STARTTLS; get the SMTP login privately from the Brevo SMTP page. It is not necessarily the website login. Validate the sender in Brevo, and set the public HTTPS base URL so confirmation links target the deployed site. Apply changes and verify each reference reports **Resolved**. Syntax alone does not prove resolution.

**Additional safety settings:** explicitly configure `NCL_USUARIOS_TESTE`, `NCL_SENHA_TESTE` if needed, and `NCL_MODO_TESTE`. The default special `teste` login is unsafe without a password. Set `NCL_USUARIOS_TESTE` to an explicitly empty string and verify the platform preserves it, or protect it with a strong secret. Removing the setting restores its default; disabling test mode alone is insufficient. Keep session keys stable between deployments. Never enable Flask debug mode publicly.

## 6. Package on Windows

From Windows PowerShell, create the ZIP **outside** the source folder:

```powershell
Set-Location 'C:\Users\Rokay Lancaster\ncl-simulado'
$zip = Join-Path (Split-Path (Get-Location).Path -Parent) 'deploy-ncl.zip'
tar.exe -a -c -f $zip --exclude='.env' --exclude='.env.*' --exclude='.venv' --exclude='venv' --exclude='.tts' --exclude='.v' --exclude='.rembg' --exclude='__pycache__' --exclude='*.pyc' --exclude='instance' --exclude='.git' --exclude='node_modules' --exclude='*.zip' --exclude='*.pem' --exclude='*.pfx' --exclude='*.key' --exclude='static/audio/trilhas/*.wav' -C . .
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed; do not deploy.' }
tar.exe -t -f $zip
```

Inspect the complete listing: `app.py` and `requirements.txt` must be at the archive root, with required modules, `data/`, `templates/`, and `static/`. Keep runtime OGG/MP3 audio; omit generated WAV files and tooling where safe. Inspect for secrets/certificates outside `.env`; exclusion patterns alone do not guarantee a safe package. Stop if private files appear. Never ZIP the entire folder without exclusions.

## 7. ZIP deploy from Cloud Shell

Upload the clean ZIP with Cloud Shell's **Upload/Download files** control. In Bash, use the uploaded path:

```bash
az webapp deploy -g rg-ncl-simulado-dev -n app-ncl-simulado   --src-path ./deploy-ncl.zip --type zip
```

This replaces the deployed application; keep a known-good ZIP for rollback. Wait for the remote build and startup, not just upload acceptance. Do not combine this remote-build flow with an unreviewed `WEBSITE_RUN_FROM_PACKAGE` setting. Rolling back code does not roll back Cosmos data. A future GitHub Actions workflow with federated OIDC authentication is planned, not configured here.

## 8. Logging and acceptance checks

```bash
az webapp log config -g rg-ncl-simulado-dev -n app-ncl-simulado   --docker-container-logging filesystem -o none
az webapp log tail -g rg-ncl-simulado-dev -n app-ncl-simulado
```

Use **Log stream** for stdout/stderr and **Deployment Center → Logs** for Oryx/build failures. The Logs blade may require additional monitoring setup; see [troubleshooting](troubleshooting.md). Keep log retention and volume small on F1. Never dump environment variables, connection strings, confirmation links, or exception bodies containing secrets.

Validate:

- [ ] HTTPS, map, images, and audio load; browser microphone permission works where supported.
- [ ] Create a normal test account, receive/confirm email, sign out and back in.
- [ ] Verify normal-account persistence and the intended Cosmos containers/partition keys.
- [ ] Try TEF/TCF practice, timers, saved history, hero, shop, and map progression.
- [ ] Check Brevo transactional logs and recipient spam folders; a UI success message alone is not delivery evidence.
- [ ] Confirm secret references resolve and the special test user is disabled or strongly protected.
- [ ] Review costs and quotas; redact personal information from portfolio evidence.

## 9. Backup and accidental deletion

Cosmos items have **no recycle bin**. Check the actual policy under the account's Backup & Restore settings; the live policy was not queried for these docs.

| Mode | Operational considerations |
|---|---|
| Periodic | Common defaults are a four-hour interval and eight-hour retention, but both must be verified. Recovery depends on available snapshots and usually Azure Support. Do not promise an exact deadline without checking policy and snapshot timing. |
| Continuous 7-day | Point-in-time recovery within the available seven-day window. Backup storage has no extra charge at this tier; restores are charged. It cannot recover a period before continuous protection existed. |

For accidentally deleted **items**, restore a pre-deletion state into a separate account and carefully copy back only validated missing items; this is not an item-level undo. Eligible deleted databases/containers can have different restore workflows. Review migration constraints before changing backup modes; enabling protection afterward cannot manufacture a past snapshot. Do a restore drill in a separate lab before relying on it.

## References

- [Python, Gunicorn, Oryx and logs](https://learn.microsoft.com/en-us/azure/app-service/configure-language-python)
- [Key Vault references, identity and cache refresh](https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references)
- [App Service plan overview](https://learn.microsoft.com/en-us/azure/app-service/overview-hosting-plans)
- [Cosmos periodic backup](https://learn.microsoft.com/en-us/azure/cosmos-db/periodic-backup-restore-introduction)
- [Cosmos continuous backup](https://learn.microsoft.com/en-us/azure/cosmos-db/continuous-backup-restore-introduction)

Review current Azure documentation, regional availability, and pricing before executing changes.

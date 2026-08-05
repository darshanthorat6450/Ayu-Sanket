# 🔐 FHIR API Key Management Guide

> Secure configuration and key management for the **FHIR Terminology & Integration API**

</p>

<p align="center">
<img src="https://img.shields.io/badge/FHIR-R4-blue?style=for-the-badge">
<img src="https://img.shields.io/badge/OAuth-2.0-success?style=for-the-badge">
<img src="https://img.shields.io/badge/JWT-Secured-orange?style=for-the-badge">
<img src="https://img.shields.io/badge/API%20Keys-Managed-red?style=for-the-badge">
<img src="https://img.shields.io/badge/Security-Production%20Ready-brightgreen?style=for-the-badge">
</p>

# 📂 Directory Structure

```text
keys/
├── .env                          # Environment variables
├── hospital_system_config.json   # Hospital EMR client configuration
├── api_keys_registry.json        # API key registry (generated)
└── README.md                     # This guide
```

---

# 📄 Configuration Files

| File | Description | Usage | Security |
|------|-------------|--------|----------|
| **`.env`** | Stores all environment variables, API keys, secrets, and application configuration | Copy to deployment server | 🔒 Never commit to Git |
| **`hospital_system_config.json`** | Configuration file for Hospital EMR/EHR integration | Share only with authorized hospital developers | 🔒 Contains client credentials |
| **`api_keys_registry.json`** *(Generated)* | Stores hashed API keys, permissions, and expiration | Used for server-side authentication | 🔒 Keep private |

---

# 🔑 Authentication & Security Keys

## 1️⃣ JWT Secret

Used for signing and validating JWT access tokens.

```env
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-here-min-64-chars
```

### Best Practices

- Minimum **64 characters**
- Cryptographically random
- Rotate every **90 days**
- Never expose publicly

---

## 2️⃣ OAuth 2.0 Credentials

Used for secure client authentication.

```env
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
```

### Supported Grant Types

- `client_credentials`
- `authorization_code`

### Purpose

- Client authentication
- Token generation
- Permission management

---

## 3️⃣ ABHA Integration Credentials

Used for **Ayushman Bharat Health Account (ABHA)** integration.

```env
ABHA_CLIENT_ID=abha-your-client-id
ABHA_CLIENT_SECRET=abha-your-client-secret
ABHA_API_KEY=abha-your-api-key
```

### Purpose

- Patient consent management
- Health record access
- ABHA authentication

Obtain credentials from the **ABHA Developer Portal**.

---

## 4️⃣ ICD-11 API Credentials

WHO ICD-11 terminology access.

```env
ICD11_CLIENT_ID=icd11-your-client-id
ICD11_CLIENT_SECRET=icd11-your-client-secret
```

### Purpose

- ICD-11 terminology lookup
- Disease classification
- Concept mapping

Register via the **WHO ICD-11 API Portal**.

---

## 5️⃣ API Keys (System-to-System Authentication)

```json
{
  "api_key": "your-api-key",
  "permissions": [
    "read",
    "write"
  ],
  "expires_at": "2026-01-24T23:27:00+05:30"
}
```

### Purpose

- Hospital systems
- Third-party applications
- Backend integrations

Server validates every API key against the registry.

---

# 🚀 Getting Started

## Step 1 — Configure Environment

```bash
# Copy configuration
cp keys/.env .env

# Edit values
nano .env

# Load variables
source .env
```

---

## Step 2 — Generate Production Keys

Generate all keys

```bash
python key_generator.py
```

Generate using Python

```bash
python -c "from key_generator import KeyGenerator; g = KeyGenerator(); g.save_all_keys()"
```

---

## Step 3 — Hospital System Integration

```python
import json
import requests

with open("keys/hospital_system_config.json") as f:
    config = json.load(f)

headers = {
    "Authorization": f"Bearer {config['api_key']}",
    "Content-Type": "application/json"
}

response = requests.get(
    f"{config['base_url']}/fhir/metadata",
    headers=headers
)

print(response.json())
```

---

## Step 4 — OAuth 2.0 Authentication

```python
import requests

token_data = {
    "grant_type": "client_credentials",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "scope": "system/CodeSystem.read system/ConceptMap.read"
}

response = requests.post(
    "https://your-api.com/fhir/oauth/token",
    data=token_data
)

token = response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}"
}
```

---

# 🔄 Key Rotation

## Rotate JWT Secret

```bash
python -c "from key_generator import KeyGenerator; g = KeyGenerator(); print(g.generate_jwt_secret_key())"
```

Recommended rotation:

- Every **90 days**
- Immediately after suspected compromise

---

## Rotate API Keys

```bash
python -c "from key_generator import KeyGenerator; g = KeyGenerator(); print(g.generate_api_key('client_name'))"
```

Recommended rotation:

- Every **365 days**
- Immediately if leaked

---

# 📊 Monitoring & Auditing

## View Audit Logs

```bash
curl -X GET "https://your-api.com/fhir/AuditEvent" \
-H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Monitor Security Events

```bash
tail -f /var/log/fhir_api/app.log | grep "Security Event"
```

Monitor:

- Failed logins
- Invalid API keys
- Rate limit violations
- Unauthorized access
- Token misuse

---

# 🔒 Supported Authentication Methods

| Method | Purpose |
|---------|----------|
| 🔑 JWT | User authentication |
| 🔐 OAuth 2.0 | Third-party applications |
| 🏥 API Keys | Hospital systems |
| 🩺 ABHA Tokens | Patient data access |

---

# 🛡 Authorization Features

- ✅ Role-Based Access Control (RBAC)
- ✅ OAuth Scope Validation
- ✅ Endpoint-Level Authorization
- ✅ API Rate Limiting
- ✅ Audit Logging
- ✅ Security Event Monitoring

---

# 🌐 API Access Permissions

## 📖 Read Access

| Endpoint | Description |
|----------|-------------|
| `GET /fhir/metadata` | Capability Statement |
| `GET /fhir/CodeSystem/namaste` | NAMASTE Code System |
| `GET /fhir/ConceptMap/namaste-icd11` | Concept Mapping |
| `GET /fhir/ValueSet` | Value Sets |
| `GET /fhir/ValueSet/$expand` | Search & Auto Complete |
| `GET /fhir/ValueSet/$lookup` | Concept Details |

---

## ✍ Write Access

| Endpoint | Description |
|----------|-------------|
| `POST /fhir/Bundle` | Upload Clinical Encounters |
| `POST /fhir/ConceptMap/$translate` | Translate Medical Concepts |

---

## 👑 Administrator Access

| Endpoint | Description |
|----------|-------------|
| `GET /fhir/AuditEvent` | Audit Logs |
| `POST /fhir/oauth/token` | OAuth Token Management |

---

# 🚨 Security Best Practices

## ✅ Do

- Use HTTPS in production
- Rotate secrets regularly
- Store credentials securely
- Monitor audit logs
- Enable rate limiting
- Use least-privilege permissions
- Hash stored API keys

---

## ❌ Don't

- Commit `.env` files
- Hardcode credentials
- Share API keys over email
- Disable HTTPS
- Log sensitive tokens
- Reuse production secrets

---

# 🚑 Emergency Response

## Revoke All API Keys

```bash
python -c "
import json
with open('keys/api_keys_registry.json') as f:
    keys = json.load(f)

for client in keys:
    keys[client]['expires_at'] = '2025-01-01T00:00:00'

with open('keys/api_keys_registry.json', 'w') as f:
    json.dump(keys, f, indent=2)

print('All API Keys Revoked')
"
```

---

## Generate a New JWT Secret

```bash
python -c "
import secrets
import string

key = ''.join(
    secrets.choice(
        string.ascii_letters +
        string.digits +
        '!@#$%^&*'
    ) for _ in range(64)
)

print(key)
"
```

---

# 📞 Support Checklist

If you suspect a security issue:

- Review audit logs
- Rotate affected keys immediately
- Revoke compromised credentials
- Monitor unusual API usage
- Notify your security team
- Generate fresh secrets before restoring access

---

# ⚠️ Production Security Recommendations

For production deployments, use a dedicated secrets management service instead of storing credentials in files.

Recommended options include:

- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager
- HashiCorp Vault

---

## 🔐 Final Security Reminder

> **Never commit `.env`, API keys, client secrets, or private certificates to version control.**
>
> Always store sensitive credentials securely, rotate them periodically, and follow the principle of least privilege to protect your FHIR infrastructure.

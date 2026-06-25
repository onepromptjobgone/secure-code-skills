---
id: secure-python
title: Secure Python — Implementation
description: >-
  Python-specific implementation of the central Secure Development skill. Load
  this alongside `securedevelopment.md` whenever writing, completing,
  scaffolding, or reviewing any Python (.py) file — web apps (Django, Flask,
  FastAPI), scripts, CLIs, data pipelines, API clients, background jobs. It
  gives the exact Python syntax (do/don't) for each security category defined in
  the central skill.
extends: securedevelopment
languages:
  - python
globs: "**/*.py"
version: 0.1.0
---

# Secure Python — Implementation

This file is the **how** for Python. Read the central `securedevelopment.md`
first for the principles and the self-check; this file gives the concrete Python
syntax. Section numbers match the central skill exactly (§1–§11), so you can
move between the two without re-mapping.

Each rule shows the secure default ("Do") and the pattern to avoid ("Don't").
Prefer "Do" silently; never emit a "Don't" unless the user insists and
understands the risk.

---

## 1 · Injection

### 1.1 SQL injection — always parameterize

Do:
```python
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
# SQLAlchemy Core
stmt = select(User).where(User.email == email)
```

Don't:
```python
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")        # injectable
cursor.execute("SELECT * FROM users WHERE email = '%s'" % email)      # injectable
session.execute(text(f"SELECT * FROM users WHERE id = {user_id}"))    # injectable
```

If an identifier (table/column) must be dynamic, validate against an allowlist —
never interpolate raw:
```python
ALLOWED_SORT = {"created_at", "name", "email"}
if sort_col not in ALLOWED_SORT:
    raise ValueError("invalid sort column")
query = f"SELECT * FROM users ORDER BY {sort_col}"  # safe: value from allowlist
```

### 1.2 OS command injection — no shell, pass argument lists

Do:
```python
import subprocess
subprocess.run(["git", "clone", repo_url], check=True, timeout=60)
```

Don't:
```python
subprocess.run(f"git clone {repo_url}", shell=True)   # shell metacharacters → RCE
os.system(f"ping {host}")                              # same
```

Never use `shell=True` to "make it work." If you need a shell feature, build the
argument list explicitly and pass values, not concatenated strings.

### 1.3 Code execution — never `eval`/`exec` on input

Do:
```python
import ast
value = ast.literal_eval(raw)          # only literals: dict/list/str/num/bool/None
import json
config = json.loads(raw)               # for structured data
```

Don't:
```python
result = eval(user_expression)         # arbitrary code execution
exec(downloaded_code)                  # same
```

### 1.4 Template injection (SSTI) — autoescape on, no user templates

Do:
```python
from jinja2 import Environment, select_autoescape
env = Environment(autoescape=select_autoescape())
env.from_string(TRUSTED_TEMPLATE).render(name=user_name)  # data is escaped
```

Don't:
```python
Environment(autoescape=False)                 # XSS by default
env.from_string(user_supplied_template)       # server-side template injection
```

---

## 2 · Input validation & deserialization

### 2.1 Never deserialize untrusted data with `pickle` / `yaml.load` / `marshal`

Do:
```python
import json
data = json.loads(payload)             # data-only, no code execution
import yaml
config = yaml.safe_load(text)          # safe loader
```

Don't:
```python
import pickle
obj = pickle.loads(request.body)       # arbitrary code execution on load
yaml.load(text)                        # full loader can instantiate objects → RCE
```

### 2.2 Validate at the boundary with a schema

Do:
```python
from pydantic import BaseModel, EmailStr, conint

class SignupRequest(BaseModel):
    email: EmailStr
    age: conint(ge=13, le=120)

req = SignupRequest(**payload)         # raises on invalid input
```

Don't:
```python
email = payload["email"]               # no validation, no type guarantee
age = int(payload.get("age"))          # crashes / accepts absurd values
```

### 2.3 XML — disable external entities (XXE)

Do:
```python
from defusedxml.ElementTree import fromstring
root = fromstring(xml_bytes)
```

Don't:
```python
import xml.etree.ElementTree as ET
ET.fromstring(xml_bytes)               # entity expansion / XXE / billion laughs
```

---

## 3 · Secrets & credential management

Do:
```python
import os
API_KEY = os.environ["STRIPE_API_KEY"]          # injected at runtime
DB_PASSWORD = os.environ["DB_PASSWORD"]
```

Don't:
```python
API_KEY = "sk_live_4eC39Hq..."                   # hardcoded secret in source
DB_PASSWORD = "P@ssw0rd123"                       # same
client = boto3.client("s3", aws_access_key_id="AKIA...", aws_secret_access_key="...")
```

Python specifics:
- Read secrets from `os.environ` or a secrets manager (Vault, AWS Secrets
  Manager, etc.). Never default a secret to a literal.
- Never pass a secret into `logger.*`, an exception message, or `print`.
- When scaffolding config, generate a `.env.example` with empty placeholders and
  assume `.env` is git-ignored — never populate real values.

---

## 4 · Cryptography

### 4.1 Password hashing — slow, salted KDF

Do:
```python
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
bcrypt.checkpw(attempt.encode(), hashed)
# or argon2-cffi / hashlib.scrypt
```

Don't:
```python
import hashlib
hashlib.md5(password.encode()).hexdigest()    # fast + broken for passwords
hashlib.sha256(password.encode()).hexdigest() # fast, unsalted → crackable
```

### 4.2 Randomness — `secrets`, not `random`, for security

Do:
```python
import secrets
token = secrets.token_urlsafe(32)
otp = secrets.randbelow(1_000_000)
```

Don't:
```python
import random
token = str(random.randint(0, 10**9))   # predictable PRNG → guessable tokens
```

### 4.3 Symmetric encryption — vetted high-level API

Do:
```python
from cryptography.fernet import Fernet
f = Fernet(key)                          # authenticated encryption
ct = f.encrypt(plaintext)
```

Don't:
```python
from Crypto.Cipher import AES
AES.new(key, AES.MODE_ECB)               # ECB leaks patterns; no integrity
```

### 4.4 TLS — never disable certificate verification

Do:
```python
import requests
requests.get(url, timeout=10)            # verification on by default
```

Don't:
```python
requests.get(url, verify=False)          # accepts any cert → MITM
ssl._create_default_https_context = ssl._create_unverified_context
```

---

## 5 · Authentication & session

Do:
```python
import secrets
# Constant-time comparison for tokens / API keys
if secrets.compare_digest(provided_token, expected_token):
    ...
```

Don't:
```python
if provided_token == expected_token:     # timing side-channel
    ...
```

Python specifics:
- Compare secrets/tokens with `secrets.compare_digest`, never `==`.
- For JWTs, always specify and verify the algorithm; reject `alg: none`.
  ```python
  jwt.decode(token, key, algorithms=["RS256"])   # explicit allowlist
  ```
  Never call `jwt.decode(token, options={"verify_signature": False})` for auth.
- Set session cookies `Secure`, `HttpOnly`, and `SameSite`:
  ```python
  response.set_cookie("session", val, secure=True, httponly=True, samesite="Lax")
  ```

---

## 6 · Authorization & access control

Do:
```python
# Scope the query to the current user — ownership enforced in the DB query
order = Order.objects.get(id=order_id, owner=request.user)
```

Don't:
```python
order = Order.objects.get(id=order_id)   # any logged-in user can fetch any order
```

Python specifics:
- Enforce authorization on every state-changing and data-returning endpoint.
- Scope queries by the current principal (`owner=request.user`, `tenant_id=...`)
  rather than fetching by raw ID.
- Default to deny: an unrecognized role or missing permission means refuse.

---

## 7 · Server-Side Request Forgery (SSRF)

Do:
```python
from urllib.parse import urlparse
parsed = urlparse(user_url)
if parsed.scheme not in {"https"} or parsed.hostname not in ALLOWED_HOSTS:
    raise ValueError("URL not permitted")
requests.get(user_url, timeout=5, allow_redirects=False)
```

Don't:
```python
requests.get(user_url)                   # can hit 169.254.169.254, localhost, etc.
```

Validate scheme and host against an allowlist, block private/link-local ranges,
set timeouts, disable redirect-following for user-supplied URLs.

---

## 8 · Path traversal & file handling

Do:
```python
from pathlib import Path
base = Path("/srv/uploads").resolve()
target = (base / user_filename).resolve()
if not target.is_relative_to(base):      # Python 3.9+
    raise ValueError("path escapes base directory")
```

Don't:
```python
open(os.path.join("/srv/uploads", user_filename))   # ../ escapes the base dir
open(f"/srv/uploads/{user_filename}")                # same
```

Also: create temp files with `tempfile.mkstemp` / `NamedTemporaryFile` (never a
predictable path in `/tmp`), and set least-privilege file modes.

---

## 9 · Framework hardening (Django / Flask / FastAPI)

Apply these defaults when scaffolding web code:

- **Debug off in production.** Never ship `DEBUG = True` (Django) or
  `app.run(debug=True)` to anything reachable.
- **Keep built-in escaping/CSRF on.** Don't disable Django template autoescaping
  or `@csrf_exempt` without a documented reason. Don't mark untrusted strings
  `mark_safe` / `|safe`.
- **Flask:** render via `render_template` (autoescaped Jinja), not f-strings into
  HTML. Set a strong `SECRET_KEY` from the environment.
- **FastAPI:** declare request/response models with Pydantic so input is typed
  and validated; don't accept raw `dict` for request bodies.
- **CORS:** never reflect arbitrary origins or use `allow_origins=["*"]` with
  credentials.

Don't (Django):
```python
from django.utils.safestring import mark_safe
return mark_safe(f"<div>{user_bio}</div>")   # stored XSS
```

---

## 10 · Dependency & supply-chain safety

- Pin dependencies with hashes (`pip install --require-hashes`, lockfiles,
  `uv.lock` / `poetry.lock`). Don't generate `requirements.txt` with unpinned or
  `*` versions for anything beyond a throwaway script.
- Don't introduce obscure or typosquat-looking packages for problems the standard
  library already covers — reach for `secrets`, `hashlib`, `hmac`, `subprocess`
  first.
- When you add a dependency, note it explicitly so it can be reviewed.

---

## 11 · Logging, error handling & data exposure

Do:
```python
logger.info("auth failed for user_id=%s", user_id)     # no secret in the log
try:
    charge(card)
except PaymentError:
    logger.exception("payment failed")                 # full trace server-side
    return JSONResponse({"error": "payment failed"}, status_code=502)  # generic to client
```

Don't:
```python
logger.info("login with password=%s token=%s", password, token)   # secrets in logs
return JSONResponse({"error": str(exc)}, status_code=500)          # leaks stack/SQL
```

Never log passwords, tokens, full card/SSN, or session IDs. Return generic error
messages to clients; keep stack traces server-side only.

---

## Quick self-check (Python)

- [ ] No string-built SQL or `shell=True` → parameterize / use arg lists (§1)
- [ ] No `eval`/`exec`/`pickle.loads`/`yaml.load` on input → remove (§1, §2)
- [ ] No hardcoded secret or `verify=False` → env var / verify on (§3, §4)
- [ ] Passwords hashed with a slow salted KDF (bcrypt/argon2/scrypt) (§4)
- [ ] Tokens from `secrets`, compared with `compare_digest` (§4, §5)
- [ ] Resource access scoped to the current user/tenant (§6)
- [ ] User-supplied URLs/paths validated against allowlist/base dir (§7, §8)
- [ ] Secrets/PII kept out of logs and client-facing errors (§11)

If any box cannot be checked, fix it before returning the code.

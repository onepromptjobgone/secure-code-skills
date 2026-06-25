---
id: securedevelopment
title: Secure Development
description: >-
  Central, language-agnostic secure-by-default guidance for AI coding agents.
  Apply this whenever you write, complete, scaffold, or review ANY code, in any
  language, that touches user input, databases, the filesystem, subprocesses,
  network requests, authentication, authorization, secrets, serialization, or
  logging. It defines the security principles that hold across every language;
  for concrete syntax, load the matching language file in `languages/` (e.g.
  `languages/python.md` for .py files). Always consult this before generating
  code, even if the user did not explicitly ask for "secure" code.
version: 0.1.0
alwaysApply: true
---

# Secure Development

This is the central security skill. It states **what** to do — the principles
that are true in every language. Each language file under `languages/` states
**how** to do it — the concrete, idiomatic syntax for that language, mirroring
the same numbered categories.

Generate code that is secure **as it is written**, not code that gets patched
after a scanner flags it. AI-generated code reproduces the insecure patterns
common in public training data. Apply these principles silently as defaults;
only raise security explicitly when a choice has a real trade-off the user
should know about.

## How to use this skill

1. **Always read this central file first.** It applies to all code.
2. **Then load the language file that matches what you are writing.** For Python
   load `languages/python.md`; for Go `languages/go.md`; and so on. The language
   file gives the exact functions, libraries, and do/don't code for these same
   categories. If a language file does not yet exist, apply the principles here
   using that language's safe equivalents and note the gap.
3. **Identify the risk surface before writing.** Note which categories below the
   code touches — most non-trivial code touches several.
4. **Prefer the secure pattern by default.** Never emit an insecure pattern
   unless the user explicitly insists and understands the risk; if so, add a
   brief inline comment noting it.
5. **In review mode**, scan against these categories and report each finding as:
   location → category → why it's exploitable → the fixed version. Show the diff
   rather than rewriting silently.
6. **When unsure, choose the more conservative option** and state the assumption
   in one line rather than generating something exploitable.

The category numbers below are stable. Every language file uses the same
numbering, so "§4 Cryptography" means the same thing everywhere.

---

## 1 · Injection

**Principle:** Never let untrusted data be interpreted as code or a command.
Keep data and code separate — pass data as parameters/arguments, never by
building a command, query, or template string through concatenation. This is the
most common high-severity flaw in generated code and covers SQL, OS commands,
dynamic code evaluation, template expansion (SSTI), LDAP, and NoSQL.

- Use parameterized queries / prepared statements for all database access.
- Invoke subprocesses with an argument list, never through a shell string.
- Never evaluate or execute strings derived from input.
- When something dynamic is unavoidable (e.g. a sort column), validate it against
  an allowlist instead of interpolating raw input.

*Generic shape:* `query(template, params)` — never `query(template + input)`.

→ Language file: exact parameterization API, safe subprocess call, safe
literal-parsing, autoescaping template setup.

---

## 2 · Input validation & deserialization

**Principle:** Distrust the shape, type, and source of all incoming data, and
never reconstruct objects from untrusted bytes with a deserializer that can
instantiate arbitrary types — that is remote code execution.

- Validate input at the boundary against an explicit schema (types, ranges,
  formats); reject what doesn't conform.
- Use data-only formats (e.g. JSON) for untrusted input; use the *safe* loader
  variant of any serializer.
- Disable external-entity resolution when parsing XML (XXE).

→ Language file: which deserializers are dangerous, the safe loader names, the
schema-validation library, the hardened XML parser.

---

## 3 · Secrets & credential management

**Principle:** Secrets never live in source code, build artifacts, or logs.

- Read secrets from environment variables or a secrets manager; never default a
  secret to a literal value.
- Never write a secret, token, or password into a log line, error message, or
  stack trace.
- When scaffolding config, emit placeholder-only example files and assume real
  values are git-ignored.

→ Language file: idiomatic environment/secret-manager access; what a hardcoded
secret looks like in this language so it can be recognized and avoided.

---

## 4 · Cryptography

**Principle:** Use vetted, high-level primitives correctly; never invent crypto
and never reach for fast/broken algorithms.

- Hash passwords with a slow, salted KDF (e.g. bcrypt/argon2/scrypt) — never a
  plain fast hash.
- Generate tokens, keys, and nonces with a cryptographically secure RNG, never a
  general-purpose PRNG.
- Use authenticated encryption via a high-level library; avoid raw modes like
  ECB and unauthenticated constructions.
- Keep TLS certificate verification on — never disable it.

→ Language file: the recommended KDF and crypto libraries, the secure-RNG API,
the authenticated-encryption helper, how cert verification gets wrongly disabled.

---

## 5 · Authentication & session

**Principle:** Make authentication resistant to guessing, timing, and token
abuse.

- Compare secrets and tokens in constant time, never with ordinary equality.
- For signed tokens (e.g. JWT), pin and verify the algorithm; reject "none" and
  never skip signature verification for auth decisions.
- Mark session cookies Secure, HttpOnly, and with an appropriate SameSite value.

→ Language file: constant-time comparison API, token-library verification calls,
cookie-flag syntax.

---

## 6 · Authorization & access control

**Principle:** Authenticated is not authorized. Enforce ownership and permission
on every state-changing and data-returning operation.

- Scope data access to the current principal (user/tenant) inside the query
  itself, rather than fetching by raw ID and trusting it (prevents IDOR).
- Check authorization server-side on every endpoint — never rely on the UI
  hiding an action.
- Default to deny: an unknown role or missing permission means refuse.

→ Language file: how to scope queries by principal in this language's ORM/data
layer; the framework's authorization hook.

---

## 7 · Server-Side Request Forgery (SSRF)

**Principle:** Treat any user-influenced outbound request as a way to reach
internal services and cloud metadata endpoints.

- Validate the scheme and host of user-supplied URLs against an allowlist.
- Block private and link-local address ranges.
- Set timeouts and disable redirect-following for user-supplied URLs.

→ Language file: URL-parsing and HTTP-client APIs, how to set timeouts and
disable redirects.

---

## 8 · Path traversal & file handling

**Principle:** A user-controlled path must never escape its intended directory.

- Resolve the candidate path and confirm it stays within the intended base
  directory before opening it.
- Create temporary files with a secure API and unpredictable names; set
  least-privilege file modes.

→ Language file: the safe path-resolution/containment check and secure temp-file
API for this language.

---

## 9 · Framework hardening

**Principle:** Keep the framework's built-in protections on, and never ship
debug/diagnostic features to anything reachable.

- Disable debug/verbose-error modes in production.
- Keep built-in output escaping and CSRF protection enabled; don't bypass them
  without a documented reason.
- Validate request bodies through the framework's typed/model layer.
- Configure CORS narrowly — never reflect arbitrary origins or combine a
  wildcard origin with credentials.

→ Language file: the specific frameworks for this language (e.g. Django / Flask /
FastAPI) and their concrete hardening settings.

---

## 10 · Dependency & supply-chain safety

**Principle:** Pin what you depend on and don't expand the attack surface
needlessly.

- Pin dependencies with version locks and hashes; avoid unpinned/wildcard
  versions outside throwaway code.
- Prefer the standard library or well-established packages; don't pull in
  obscure or typosquat-looking packages for problems already solved.
- Call out every new dependency so it can be reviewed.

→ Language file: the lockfile/hash mechanism and the standard-library
equivalents to prefer.

---

## 11 · Logging, error handling & data exposure

**Principle:** Logs and error responses must not leak secrets, PII, or internals.

- Never log passwords, tokens, full card/SSN, or session identifiers.
- Return generic error messages to clients; keep stack traces and internal
  details server-side only.

→ Language file: the logging API, how to log a full trace server-side while
returning a generic client response.

---

## Quick self-check (all languages)

Before returning any code, verify:

- [ ] No data concatenated into a query, command, or template → §1
- [ ] No unsafe deserialization or unvalidated input → §2
- [ ] No hardcoded secret; nothing sensitive in logs → §3, §11
- [ ] Passwords use a slow salted KDF; tokens use a secure RNG; TLS verified → §4
- [ ] Tokens compared in constant time; token signatures verified → §5
- [ ] Every data access scoped to the current principal → §6
- [ ] User-supplied URLs and paths validated/contained → §7, §8
- [ ] Framework protections on; debug off → §9
- [ ] Dependencies pinned and reviewed → §10

If any box can't be checked, fix it before returning the code. For exact syntax,
the matching `languages/` file is authoritative.

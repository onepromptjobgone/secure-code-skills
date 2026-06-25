---
id: secure-LANG
title: Secure LANG — Implementation
description: >-
  LANG-specific implementation of the central Secure Development skill. Load
  this alongside `securedevelopment.md` whenever writing, completing,
  scaffolding, or reviewing any LANG file. It gives the exact LANG syntax
  (do/don't) for each security category defined in the central skill.
extends: securedevelopment
languages:
  - LANG
globs: "**/*.EXT"
version: 0.1.0
---

# Secure LANG — Implementation

This file is the **how** for LANG. Read the central `securedevelopment.md` first
for the principles and the self-check; this file gives the concrete LANG syntax.
Section numbers match the central skill exactly (§1–§11).

Each rule shows the secure default ("Do") and the pattern to avoid ("Don't").
Prefer "Do" silently; never emit a "Don't" unless the user insists and
understands the risk.

> HOW TO USE THIS TEMPLATE
> 1. Copy this file to `languages/<lang>.md` (e.g. `languages/go.md`).
> 2. Replace LANG / EXT and the frontmatter id/globs.
> 3. Keep ALL eleven sections below in the same order and numbering — do not
>    add or drop categories; the central skill and the self-check depend on the
>    numbering being stable across languages.
> 4. Fill each section with idiomatic Do/Don't code for this language. If a
>    category genuinely doesn't apply, keep the heading and write one line
>    explaining why rather than deleting it.
> 5. Delete this instruction block when done.

---

## 1 · Injection
<!-- SQL parameterization, safe subprocess invocation, no eval/exec on input,
     templating with autoescape. -->

Do:
```LANG
```

Don't:
```LANG
```

---

## 2 · Input validation & deserialization
<!-- Dangerous deserializers + their safe variants, schema validation at the
     boundary, hardened XML parsing (XXE). -->

---

## 3 · Secrets & credential management
<!-- Env / secrets-manager access; what a hardcoded secret looks like here. -->

---

## 4 · Cryptography
<!-- Password KDF, secure RNG, authenticated encryption, TLS verification on. -->

---

## 5 · Authentication & session
<!-- Constant-time comparison, signed-token verification, cookie flags. -->

---

## 6 · Authorization & access control
<!-- Scope data access to the current principal; deny by default; IDOR. -->

---

## 7 · Server-Side Request Forgery (SSRF)
<!-- URL allowlisting, block private ranges, timeouts, no redirect-following. -->

---

## 8 · Path traversal & file handling
<!-- Path containment check, secure temp files, least-privilege modes. -->

---

## 9 · Framework hardening
<!-- The main web frameworks for this language and their hardening settings. -->

---

## 10 · Dependency & supply-chain safety
<!-- Lockfile/hash pinning; prefer stdlib/well-known packages. -->

---

## 11 · Logging, error handling & data exposure
<!-- Keep secrets/PII out of logs; generic client errors, traces server-side. -->

---

## Quick self-check (LANG)
<!-- Mirror the central self-check, annotated with this language's specifics. -->

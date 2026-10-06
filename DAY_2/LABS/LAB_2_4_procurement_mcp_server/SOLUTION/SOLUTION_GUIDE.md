# Solution guide: Lab 2.4 - Procurement MCP server with authentication

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

An MCP server with real security hygiene: stdout is the protocol channel, constant-time key checks, identical 401s that never echo credentials, redacted logs, and authorization (403/422) kept separate from authentication (401).

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def known_secrets() (`security.py`)

Solution:

```python
def scrub(value):
    """Mask secrets in a string, or inside nested dicts/lists of strings."""
    if isinstance(value, str):
        for secret in known_secrets():
            value = value.replace(secret, MASK)
        return BEARER.sub("Bearer " + MASK, value)
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(v) for v in value]
    return value
```

### Block 2: def filter() (`security.py`)

What the TODO asks:

> TODO 3: mask (a) every value from known_secrets() and any "Bearer <token>" text in the message,
> and (b) the same inside record.fields (a dict of structured fields; values may be nested).
> Set record.msg to the scrubbed text and record.args to (). Always return True.

Solution:

```python
record.msg = scrub(record.getMessage())
record.args = ()
if isinstance(getattr(record, "fields", None), dict):
    record.fields = scrub(record.fields)
```

### Block 3: def authenticate() (`security.py`)

What the TODO asks:

> TODO 1: compare in constant time (hmac.compare_digest on bytes), check EVERY configured key without
> returning early, and return None for an empty token.

Solution:

```python
found = None
for role, key in load_keyring().items():
    if hmac.compare_digest(token.encode(), key.encode()) and token:
        found = Principal(USERS[role], role)
return found
```

### Block 4: def unauthorized_response() (`security.py`)

What the TODO asks:

> TODO 2: the body and headers must be IDENTICAL for every reason. Never echo the presented token or hint at the
> expected key. Log the failure with log_event("auth_failed", reason=reason) WITHOUT the credential.

Solution:

```python
log_event("auth_failed", reason=reason)
body = b'{"error": "unauthorized"}'
headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
           (b"www-authenticate", b"Bearer")]
return headers, body
```

### Block 5: def check_role() (`security.py`)

What the TODO asks:

> TODO 6a: only roles "approver" and "director" may approve -> (403, "forbidden", {}).

Solution:

```python
if principal.role not in ("approver", "director"):
    return 403, "forbidden", {}
```

### Block 6: def check_po_rules() (`security.py`)

What the TODO asks:

> TODO 6b: the supplier's status must be "active" -> (422, "supplier_not_active", {"supplier_id": ...})
> TODO 6c: the approver must not be the PO's requested_by -> (403, "self_approval", {})
> TODO 6d: po["amount_cents"] must be <= limits[principal.role] -> (403, "spend_limit_exceeded", {"limit_cents": ..., "amount_cents": ...})

Solution:

```python
if supplier is None or supplier["status"] != "active":
    return 422, "supplier_not_active", {"supplier_id": po["supplier_id"]}
if principal.user == po["requested_by"]:
    return 403, "self_approval", {}
if po["amount_cents"] > limits.get(principal.role, 0):
    return 403, "spend_limit_exceeded", {"limit_cents": limits.get(principal.role, 0), "amount_cents": po["amount_cents"]}
```

### Block 7: def spend_limit_policy() (`server.py`)

What the TODO asks:

> TODO 4: add the resource template  po://{po_id}  (application/json). Return the PO including its approvals
> (pdb.po_row); raise ValueError for an unknown id. Copy the supplier example's shape, minus the print.

Solution:

```python
@mcp.resource("po://{po_id}", mime_type="application/json")
def po_resource(po_id: str) -> str:
    """One purchase order with its approval history."""
    po = pdb.po_row(CON, po_id)
    if po is None:
        raise ValueError(f"unknown purchase order {po_id}")
    return json.dumps(po, sort_keys=True)
```

### Block 8: def find_supplier() (`server.py`)

What the TODO asks:

> TODO 5: add the tool  get_po(po_id: str, ctx: Context) -> POView.  Unknown id: fail(404, "po_not_found", po_id=po_id).
> The docstring becomes the tool description Claude reads: say what it returns. Call caller(ctx) first.

Solution:

```python
@mcp.tool()
def get_po(po_id: str, ctx: Context) -> POView:
    """Read one purchase order (amount, status, requester, approval history). Read-only; does not approve anything."""
    p = caller(ctx)
    po = pdb.po_row(CON, po_id)
    if po is None:
        fail(404, "po_not_found", po_id=po_id)
    log_event("tool_call", tool="get_po", user=p.user, role=p.role, po_id=po_id)
    return POView(**po)
```

### Block 9: def approve_po() (`server.py`)

What the TODO asks:

> TODO 6 (wire-up): call security.check_role(p) FIRST (before any PO lookup), then the 404 and 409 checks,
> then security.check_po_rules(p, po, supplier, limits). A denial is (status, code, detail): call
> log_event("tool_denied", ...) and fail(status, code, **detail). The rules are in security.py.

Solution:

```python
denial = security.check_role(p)
if denial:
    log_event("tool_denied", tool="approve_po", user=p.user, role=p.role, po_id=po_id, error=denial[1])
    fail(denial[0], denial[1], **denial[2])
```

### Block 10: def approve_po() (`server.py`)

Solution:

```python
denial = security.check_po_rules(p, po, pdb.supplier_row(CON, po["supplier_id"]), pdb.spend_limits())
if denial:
    log_event("tool_denied", tool="approve_po", user=p.user, role=p.role, po_id=po_id, error=denial[1])
    fail(denial[0], denial[1], **denial[2])
```

### Block 11: def main() (`server.py`)

What the TODO asks:

> TODO 7: wrap the app in BearerAuthMiddleware. The starter serves it WITHOUT authentication.

Solution:

```python
app = BearerAuthMiddleware(app)
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- authenticate: a valid key maps to its role
- authenticate: empty and wrong keys give None
- authenticate uses hmac.compare_digest (constant time)
- RedactingFilter masks keys and Bearer tokens in message and nested fields
- the mask text is visible, so a reader knows something was removed
- 401 is identical for no header, wrong scheme and wrong key
- 401 body never echoes the token or a key prefix
- analyst may not approve (403 forbidden); approver may
- approver within limit on an active supplier: allowed
- suspended supplier: 422 supplier_not_active
- approving your own request: 403 self_approval
- over the role's limit: 403 spend_limit_exceeded with limit_cents
- director may approve what an approver may not
- server.py has no print() to stdout (it would corrupt the stdio protocol)
- main() wraps the HTTP app in BearerAuthMiddleware
- no API key appears in the server log
- stdio approver: PO-2001 ok, PO-2003 self-approval 403, PO-2005 over limit 403
- server lists the get_po tool and the po://{po_id} resource template
- reading po://PO-2001 returns the purchase order
- supplier resource masks the bank account
- get_po tool returns PO-2002 with status APPROVED
- stdio director: PO-2005 ok, PO-2004 (suspended supplier) 422
- stdio analyst: approve is forbidden (403)
- HTTP: no header, wrong scheme and wrong key all get 401
- HTTP: the three 401 bodies are identical and do not echo the key
- HTTP with a valid approver key behaves like stdio
- stdio sessions ran (a print() to stdout or a crash breaks the handshake)

## 4. Common mistakes

- `print()` in server code: in stdio mode stdout carries the protocol, so a stray print breaks the handshake. Log to stderr.
- Comparing keys with `==` (timing leak) or returning early on the first match.
- Different 401 bodies for 'no header' and 'wrong key', or echoing the token or a key prefix.
- Checking the role AFTER looking up the PO: an analyst can learn which PO ids exist from the 404 vs 403 difference.
- Forgetting to wrap the HTTP app in the auth middleware (TODO 7): the server then runs unauthenticated.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. A stray `print` makes every stdio session fail to start (the handshake reads garbage from stdout).
2. Moving `check_role` after the 404 lookup: an analyst gets 404 for unknown ids and 403 for real ones, revealing which POs exist.
3. A distinguishing 401 ('missing header' vs 'wrong key') lets an attacker tell which part of a guess is right; keep all 401s identical.
4. Logging the header while redaction is off puts the key in the log file; `check.py` fails on any key in the log.
5. Trusting the stdio principal on HTTP means any request that bypasses the middleware acts as the process owner: authenticate per request (defence in depth).

## 6. Files in this folder

- `security_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `server_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file

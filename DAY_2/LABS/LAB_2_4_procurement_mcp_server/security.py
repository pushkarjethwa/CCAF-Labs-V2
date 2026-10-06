"""security.py - logging, authentication and authorization rules for the procurement server.

Everything here is plain Python (no MCP needed), so `python check.py` can test it directly.
You implement TODO 1, 2, 3 and 6. server.py (the MCP wiring) uses these functions.

Two different questions, kept apart on purpose:
  authentication  = WHO are you?        wrong or missing key -> HTTP 401   (section 2)
  authorization   = WHAT may you do?    known user, not allowed -> 403/422 (section 3)
"""
import hmac
import json
import logging
import os
import re
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------- 1. SAFE LOGGING
# Rules for an MCP server: logs go to STDERR (stdout is the protocol channel in stdio mode),
# and credentials must never appear in a log.
SECRET_ENV_VARS = ("PROC_KEY_ANALYST", "PROC_KEY_APPROVER", "PROC_KEY_DIRECTOR", "PROC_API_KEY")
MASK = "***REDACTED***"
BEARER = re.compile(r"(?i)bearer\s+\S+")


def known_secrets():
    """Credential values of THIS process, longest first so overlapping values are masked fully."""
    values = {os.environ[name] for name in SECRET_ENV_VARS if os.environ.get(name)}
    return sorted(values, key=len, reverse=True)




class RedactingFilter(logging.Filter):
    """Scrubs credentials out of every record before any handler formats it."""

    def filter(self, record):
        # TODO 3: mask (a) every value from known_secrets() and any "Bearer <token>" text in the message,
        #   and (b) the same inside record.fields (a dict of structured fields; values may be nested).
        #   Set record.msg to the scrubbed text and record.args to (). Always return True.
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"event": record.getMessage(), **(getattr(record, "fields", None) or {})}, sort_keys=True, default=str)


def get_logger():
    logger = logging.getLogger("procurement")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handlers = [logging.StreamHandler(sys.stderr)]  # NEVER stdout
    if os.environ.get("PROC_LOG_FILE"):  # lets check.py read the log afterwards
        handlers.append(logging.FileHandler(os.environ["PROC_LOG_FILE"], encoding="utf-8"))
    for handler in handlers:
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)
    return logger


def log_event(event, **fields):
    get_logger().info(event, extra={"fields": fields})


# ---------------------------------------------------------------- 2. AUTHENTICATION: who are you?
# Keys come from the SERVER process environment, one per role (any string of 16+ characters):
#   PROC_KEY_ANALYST, PROC_KEY_APPROVER, PROC_KEY_DIRECTOR
# stdio transport: the launcher puts the caller's key in PROC_API_KEY. HTTP: header "Authorization: Bearer <key>".
ROLE_ENV = {"analyst": "PROC_KEY_ANALYST", "approver": "PROC_KEY_APPROVER", "director": "PROC_KEY_DIRECTOR"}
USERS = {"analyst": "dev.analyst", "approver": "maya.approver", "director": "dir.director"}


@dataclass(frozen=True)
class Principal:
    user: str
    role: str


def load_keyring():
    """role -> key from the environment. Fails closed: no keys configured, refuse to run (given)."""
    ring = {role: os.environ[env] for role, env in ROLE_ENV.items() if os.environ.get(env)}
    if not ring:
        print("refusing to start: no PROC_KEY_* variables set", file=sys.stderr)
        raise SystemExit(2)
    return ring


def extract_bearer(header):
    """Token of an 'Authorization: Bearer <token>' header, else '' (given)."""
    parts = (header or "").split(" ", 1)
    return parts[1].strip() if len(parts) == 2 and parts[0].lower() == "bearer" else ""


def authenticate(token):
    """Map a presented key to a Principal, or None."""
    # TODO 1: compare in constant time (hmac.compare_digest on bytes), check EVERY configured key without
    #   returning early, and return None for an empty token.
    for role, key in load_keyring().items():
        if token == key:  # DEFECT: plain == leaks how many leading characters matched
            return Principal(USERS[role], role)
    return None


def unauthorized_response(token, reason):
    """Build the HTTP 401 answer. Returns (headers, body_bytes). reason: "no_header", "wrong_scheme" or "wrong_key"."""
    # TODO 2: the body and headers must be IDENTICAL for every reason. Never echo the presented token or hint at the
    #   expected key. Log the failure with log_event("auth_failed", reason=reason) WITHOUT the credential.
    body = f'{{"error": "invalid API key {token}", "expected_prefix": "{next(iter(load_keyring().values()))[:4]}"}}'.encode()  # DEFECT: leaks
    return [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())], body


def principal_from_header(header):
    return authenticate(extract_bearer(header))


# ---------------------------------------------------------------- 3. AUTHORIZATION: what may you do?
def check_role(principal):
    """Run BEFORE looking at the PO, so an analyst learns nothing about which POs exist.
    Return None if allowed, else (status, error_code, detail_dict)."""
    # TODO 6a: only roles "approver" and "director" may approve -> (403, "forbidden", {}).
    return None


def check_po_rules(principal, po, supplier, limits):
    """Rules that need the PO. Return None if allowed, else (status, error_code, detail_dict).
    limits = {role: max amount in cents}. Check in this order."""
    # TODO 6b: the supplier's status must be "active" -> (422, "supplier_not_active", {"supplier_id": ...})
    # TODO 6c: the approver must not be the PO's requested_by -> (403, "self_approval", {})
    # TODO 6d: po["amount_cents"] must be <= limits[principal.role] -> (403, "spend_limit_exceeded", {"limit_cents": ..., "amount_cents": ...})
    return None

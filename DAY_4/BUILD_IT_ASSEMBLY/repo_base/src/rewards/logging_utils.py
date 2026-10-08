"""Logging helper. Logs the customer id only, never personal data."""
import logging

logger = logging.getLogger("rewards")
PERSONAL_FIELDS = {"email", "phone", "address", "name"}


def log_event(event: str, customer_id: str, **fields) -> str:
    """Log one event line with the customer id and return the line."""
    blocked = PERSONAL_FIELDS & set(fields)
    if blocked:
        raise ValueError("personal data must not be logged: " + ", ".join(sorted(blocked)))
    extras = "".join(" %s=%s" % (key, fields[key]) for key in sorted(fields))
    line = "event=%s customer_id=%s%s" % (event, customer_id, extras)
    logger.info(line)
    return line

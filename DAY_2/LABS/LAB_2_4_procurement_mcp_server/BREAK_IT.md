# Break it - Lab 2.4
1. **A stray print.** Add `print("hello")` to `find_supplier`. Run `python check.py`: the stdio sessions fail to start. stdout is the protocol channel; logs belong on stderr.
2. **Check order.** Move `check_role` after the 404 lookup. As an analyst, ask for a PO id that does not exist and one that does: do the answers differ? What does that reveal?
3. **Leaky 401.** Make `unauthorized_response` say "wrong key" vs "missing header". Run check.py. Why does a distinguishing message help an attacker?
4. **Log the header.** In `BearerAuthMiddleware` log `header` yourself, then disable the redaction filter. Find the key in the log.
5. **Authenticate once only.** In `caller()`, trust the stdio principal even on HTTP. What goes wrong if the middleware is ever bypassed?

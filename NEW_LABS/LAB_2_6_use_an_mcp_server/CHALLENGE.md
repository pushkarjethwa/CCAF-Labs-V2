# Challenge - Lab 2.6
1. Allow-list: only pass tools named in a `ALLOWED` set, so a server that adds a dangerous tool later is not exposed automatically.
2. Connect to two servers at once and prefix tool names (`notes__get_note`) to avoid clashes.
3. Add a resource to `notes_server.py` (`note://{id}`) and read it from the client with `session.read_resource`. When would a resource be better than a tool?

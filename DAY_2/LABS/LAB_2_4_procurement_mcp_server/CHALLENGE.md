# Challenge - Lab 2.4
1. Add a `reject_po` tool with the same authorization rules and a required `reason` argument.
2. Add rate limiting: 5 failed authentications from one client per minute, then 429.
3. Add a resource `po://pending` listing pending POs, and decide: should it be a resource or a tool? Write two sentences on why.

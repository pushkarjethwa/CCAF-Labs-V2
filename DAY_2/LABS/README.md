# Day 2 Lab Exercises

These hands-on labs follow the Day 2 demos. Each lab keeps the scenario you work on, and repeats the steps of the demo before it, so you start every lab already knowing the method. Every stage runs on its own, and at a few marked points (**TODO n of N**) you paste a small piece of code that the guide gives line by line.

To complete these exercises you need Python 3.10 or later and an Anthropic API key (Lab 2.4 needs no key). Setup is in **DAY_0_SETUP_GUIDE.md**.

- [Fix the Tool Boundaries of the Facilities Assistant](LAB_2_1_facilities_tool_boundaries/README.md): follows Demo 2A, about 35 minutes. Rewrite descriptions, consolidate and prune the tools, scope them per desk, and pass a gate.
- [Run the Tool Calls of One Turn Safely](LAB_2_2_travel_disruption_tool_loop/README.md): follows Demo 2C, about 35 minutes. Overlap the reads, keep the dependent writes in order, make a retry safe, and bound the loop.
- [Make the Payroll Agent Fail Safely](LAB_2_3_payroll_typed_errors/README.md): follows Demo 2B, about 30 minutes. Typed errors, a bounded retry, an escalation, and a preflight check.
- [Build and Lock Down a Procurement MCP Server](LAB_2_4_procurement_mcp_server/README.md): follows Demo 2D, about 40 minutes. Stdio logging, resources, validated tools, a config linter, authentication and roles.
- [Build a Tool and a Loop](LAB_2_5_build_a_tool_and_loop/README.md): an optional extra after Demos 2B and 2C.
- [Use an MCP Server](LAB_2_6_use_an_mcp_server/README.md): an optional extra after Demo 2D.

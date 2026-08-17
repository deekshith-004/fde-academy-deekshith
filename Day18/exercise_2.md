Exercise 2 — Role-Play: Explain a Pipeline Failure to a Non-Technical CFO

Task 1 — Prepare Your Translation

Technical Fact

The overnight sales-data process failed before writing any information because an unexpected field was introduced by an upstream system.

Business Impact

No incorrect or incomplete financial data reached the dashboards. However, today's dashboards are missing yesterday's sales transactions and therefore are one day behind.

Recommended Action

A fix will be deployed within the next hour, followed by a reload of the missing transactions. No action is required from the CFO's team, but today's dashboard should be treated as incomplete until the reload finishes.

Task 2 — 90-Second Explanation

“The good news is that no incorrect financial data reached your reports. The overnight sales update did not complete because one of the systems sending us information introduced a new field that our process wasn't prepared for. The process stopped before saving anything, so there is no corrupted or partially loaded data in the dashboards.

The impact is that today's financial dashboard is missing yesterday's sales transactions, so the numbers are currently one day behind. We've already prepared the fix and expect to deploy it within the next hour. After that, we'll reload the missing transactions and verify the results.

There is nothing your team needs to do right now. Until we complete the reload, please treat today's dashboard as incomplete. We'll confirm once the data is fully updated.”

If the CFO asks: “Is any of our financial data wrong right now?”

“No. We stopped the update before any incorrect data was written. The issue is that yesterday's transactions are missing from today's dashboard, rather than the existing numbers being corrupted.”

If the CFO asks: “When exactly will this be fixed?”

“The fix is planned for deployment within the next hour, followed by the data reload and validation. I'll confirm once the dashboard is fully up to date.”

If the CFO asks: “Should I be worried about this happening again?”

“We're addressing the underlying compatibility issue so the new field is handled correctly. We'll also validate the reload before confirming the dashboard is current.”

Task 3 — Self-Audit Against the Forbidden List

Forbidden Pattern

Answer

Stack traces / error codes / jargon

No. I avoided technical terms and explained the issue in business language.

Minimizing language

No. I did not describe the incident as a minor issue or “small hiccup.”

Blame

No. I explained that an upstream system introduced a change without assigning blame.

Silence about fix/timeline

No. I clearly explained the planned fix, reload, and expected timeline
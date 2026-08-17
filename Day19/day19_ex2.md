Exercise 2 — Convert Workshop Outputs into 10 User Stories

Task 1 — Translate 3 Pain Points into Requirements

Pain Point 1

Pain Point: “We never know a shipment is late until the customer calls angry.”

Diagnosis: The operations team needs an early indication that a shipment is likely to become late so it can intervene before the customer is affected.

Requirement: Calculate a delay-risk score for each active shipment using relevant historical and operational data and trigger an alert when the risk exceeds a defined threshold.

Pain Point 2

Pain Point: “Checking status takes 10–15 minutes because I check 3 systems.”

Diagnosis: Dispatchers need a single source of current shipment information instead of manually gathering data from multiple systems.

Requirement: Create a unified shipment view combining relevant TMS, warehouse, and shipment-note information.

Pain Point 3

Pain Point: “There's no record of who approved rerouting a shipment.”

Diagnosis: The business needs traceability for important shipment decisions.

Requirement: Record rerouting decisions with the responsible user, timestamp, shipment, and action details in an auditable history.

Task 2 — 10 User Stories

As an operations dispatcher, I want to see a delay-risk score on every active shipment, so that I can proactively reroute or notify customers before they escalate to support.

As a dispatcher, I want to see the latest shipment status, location, and warehouse information on one screen, so that I can answer customer questions without checking multiple systems.

As an operations director, I want to receive alerts for shipments whose delay risk exceeds the agreed threshold, so that my team can intervene before the shipment becomes a customer issue.

As a dispatcher, I want to see the key factors contributing to a shipment's delay-risk score, so that I can understand why a shipment has been flagged.

As warehouse staff, I want shipment location and status updates to be available to dispatchers automatically, so that I do not have to respond manually to repeated status requests.

As a dispatcher, I want to record a rerouting decision against the shipment, so that there is a clear history of what action was taken.

As an operations director, I want to view recurring shipment-delay patterns by carrier and route, so that I can identify sources of operational risk.

As a dispatcher, I want to receive a notification when a shipment's risk status changes significantly, so that I can focus on shipments requiring immediate attention.

As an operations director, I want to view unresolved shipment exceptions in a prioritized list, so that my team can focus on the highest-impact issues first.

As a warehouse staff member, I want to update shipment exception information in a shared system, so that dispatchers can access the latest information without relying on email threads.

Task 3 — Acceptance Criteria for 5 Stories

Story 1

Given a shipment is in transit, when its delay-risk score exceeds 70%, then the shipment is visually flagged on the dispatcher's view.

Given a dispatcher opens a flagged shipment, when the shipment details are displayed, then the contributing risk factors are visible.

Story 2

Given a shipment exists, when the dispatcher opens its detail view, then the latest status, location, and warehouse information are shown together.

Given new shipment information is received, when the unified view is refreshed, then the latest available information is displayed without manual copying.

Story 3

Given a shipment's risk is below the alert threshold, when the risk rises above the threshold, then an alert is generated for the appropriate operations user.

Given an alert has been generated, when the operations user opens it, then the affected shipment and current risk level are shown.

Story 6

Given a dispatcher chooses to reroute a shipment, when the action is submitted, then the system records the shipment, user, timestamp, and action.

Given a rerouting decision has been recorded, when an authorized user views the shipment history, then the decision and audit information are displayed.

Story 7

Given historical shipment data is available, when the operations director selects a carrier or route, then the relevant historical delay pattern is displayed.

Given sufficient historical data exists, when the analysis is generated, then carriers or routes with recurring delays can be identified.

Reflection Questions

1. Which story would you build first?

I would build Story 1 first because proactive delay-risk visibility addresses the highest-impact pain point: discovering delays only after customers complain. This follows the same impact-and-frequency prioritization used in the workshop.

2. Which story was hardest to make testable?

Story 7 is the most difficult because “recurring patterns” depends on data quality and historical volume. The story needs clearer definitions for the time period, minimum data volume, and what qualifies as recurring.

3. What would a client asking about cost reveal?

It would show that the discovery workshop did not explore financial impact deeply enough. A follow-up should quantify dispatcher time, customer escalations, rerouting costs, and the financial impact of carrier or route delays.
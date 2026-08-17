Exercise 3 — Map Current-State Data Flows and Automation Opportunities

Task 1 — Data-Level Flow

[TMS: Transit Status] → Manual → [Dispatcher reads]

[Warehouse System: Physical Location] → Manual → [Dispatcher reads]

[Email Threads: Manual Warehouse Notes] → Manual → [Dispatcher reads]

[Dispatcher] → Manual → [Shared Spreadsheet: Shipment Summary] → Manual → [Phone Call to Customer]

Manual Hops

There are 5 main manual hops:

TMS → Dispatcher

Warehouse system → Dispatcher

Email → Dispatcher

Dispatcher → Shared spreadsheet

Shared spreadsheet → Customer communication

Task 2 — Classify Each Manual Step

Manual Step

Signal Category

Automation Opportunity

Dispatcher reads transit status from TMS

Pure data retrieval/copying

Integrate TMS data into a unified shipment view

Dispatcher reads physical location

Pure data retrieval/copying

Integrate warehouse location data

Dispatcher searches email for warehouse notes

Manual information gathering

Capture warehouse updates in a structured system

Dispatcher combines information from three systems

Pure data copying/reconciliation

Automatically combine data into one shipment record

Dispatcher types summary into spreadsheet

Pure data copying

Replace spreadsheet updates with an automated pipeline/unified object

Dispatcher communicates status to customer

Status communication

Automate standard notifications while keeping exceptions human-reviewed

Automation Priority

The strongest immediate opportunity is eliminating the repeated three-system lookup and manual summary creation. This is primarily an integration/data-movement problem rather than an ML problem.

Task 3 — What Should Stay Manual?

Step

Final customer communication for ambiguous or high-impact shipment exceptions.

Why

Some exceptions require genuine human judgment. A customer may need a customized explanation, a service commitment may be involved, or the data may not clearly indicate the correct response. Fully automating these cases could produce inappropriate communication.

What Could Still Be Improved

Provide the human decision-maker with a unified shipment view containing current status, location, delay-risk information, contributing factors, and history. Standard low-risk notifications can be automated while ambiguous or high-impact cases remain with a dispatcher.

Reflection Questions

1. Which Day 11 category appears most?

Most opportunities are rules-based/integration because the main problem is moving and combining information between systems. ML is relevant for delay-risk prediction, while GenAI is less central to this scenario.

2. If only ONE opportunity could be built first?

I would prioritize a unified shipment view that automatically combines TMS, warehouse, and relevant shipment information. It removes frequent manual work and gives dispatchers faster access to the data they need.

For cost reduction, this integration reduces repeated manual effort. For customer satisfaction, proactive delay-risk alerts would become the stronger priority because they enable intervention before the customer calls.

3. What did the data-level map reveal?

The process-level map showed that dispatchers check multiple systems, but the data-level map exposed exactly where information is manually read, copied, combined, and re-entered. It therefore made the integration opportunities and human-judgment steps much clearer.
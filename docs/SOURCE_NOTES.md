# Source inspection and decisions

The master prompt was recovered from the referenced conversation attachment. Its `/mnt/data/prompt_codex.txt` location is a cloud path, not a path on this Windows machine. A byte-for-byte copy is in `docs/master-specification.txt`. The registered project is `C:\Users\link4\OneDrive\Desktop\Use Case 3`; this was an uninitialized source folder, not an existing application or Git repository.

`Participant_Guide.md` and all five Markdown policies were read in full. Every row of all nine data CSVs was parsed and profiled before analytics was implemented. Both evaluation CSVs were read completely. `docs/source-profile.json` records the actual headers, row counts, types, nullability, and category values. `docs/source-integrity.json` records SHA-256 hashes of all 19 supplied files, including the original printable guides. No supplied files were moved or edited. Screenshots/workflow-diagram attachments were not available; the written screen descriptions drove the UI.

| Dataset | Rows | Key | Relevant details |
|---|---:|---|---|
| support_cases | 550 | case_id | created_ts minute precision; eight category labels; four priorities; Open/In Progress/Closed; sku missing in 73 rows, register_id in 475, root_cause_hint in 390 |
| product_master | 520 | sku | vendor_id, list_price, high_demand Yes/No, warranty_days; no supplier contract pricing |
| inventory | 1,250 | store_id + sku | on_hand, system_qty, reorder_point, last_count_date, shelf_capacity; no duplicate composite keys |
| store_master | 50 | store_id | Includes WH001 warehouse, region, nearby_store_id; not a permission mapping |
| employee_master | 100 | employee_id | Fictional employee names, persona and store IDs; never used to grant application roles or exposed in employee APIs |
| receipts | 310 | receipt_id | po_qty, received_qty, receipt_date, quality_check_ok, damage_notes |
| vendor_master | 15 | vendor_id | fill_rate/on_time_rate as fractions in [0,1], effective_from, Active/Watch |
| returns_quality | 160 | return_id | created_ts, sku, refund_amount_inr, receipt_present, reason, status, notes |
| escalation_matrix | 15 | category + trigger | team, channel, sla_minutes, human_approval_required, policy_source |

Relationships were checked across the full package: store_id/nearby_store_id → store_master; sku → product_master; vendor_id → vendor_master; employee_id → employee_master. No invalid foreign references were found. Optional empty support-case fields are preserved. Inventory and receipts do not supply a historical demand series; the app cannot claim a statistical causal model of stock-outs.

## Governing rules

- Exactly eight categories from the guide. Application identities have two product roles: Employee and Manager; source personas are business context, not authentication credentials.
- Anchor for analytics: `2026-10-10 12:00:00 IST`. Windows are inclusive of both bounds. Date-only receipt windows include the whole boundary calendar day.
- P1: immediate human escalation for store-wide payment outage, restricted credentials/payment requests, safety/recall/injury risk. A single failed card reader is ordinarily P3.
- Multiple **degraded** registers are P2 per guide. Multiple registers **unable to process payment** are P1 per POS runbook and escalation matrix. The distinction resolves the wording conflict without making every degraded service P1.
- Escalate for P1, estimate below .60, restricted requests, conflicting/insufficient evidence, or human approval. Confidence is uncalibrated. The API does not claim statistical confidence.
- No receipt always requires manager review. Refund ≥ INR 5,000 requires approval; the additional no-receipt ≥ INR 1,000 condition is therefore also covered. The matrix routes no-receipt/high-value refunds as P2.
- Safety instructions are recommendations for immediate human action, not completed quarantine/recall/refund/claim/transfer transactions.
- Inventory discrepancy compares absolute difference >10 or difference/system_qty >20%; denominator is one for a zero system quantity. The policy leaves the percentage denominator unspecified; this implementation decision is exposed in findings.
- Quality trends show support complaints and quality-related returns separately. There is no incident-to-return cross-reference, so their sum is **record count**, not deduplicated complaints or proof of vendor fault. The exact included reason labels are returned with the result.

## Deliberate boundaries

Employees see only their own application incidents; Managers see and update all application incidents. The guide supplies no authenticated store-assignment rule, so no store hierarchy was invented. Both roles can browse policies and read non-PII aggregate/product/inventory analytics across the fictional dataset. No raw employee export or raw support-case list is offered through analytics.

CSV update supports exactly the nine original filenames. Type/enum/nullability contracts are frozen from the inspected originals. New columns/category values require reviewed schema changes; uploads do not redefine contracts. Referential integrity is rechecked across the prospective full dataset set at activation, so removing referenced master rows is rejected. There is no multi-dataset transaction feature; add new master keys first, then dependent records.

The **original** escalation matrix and policy Markdown govern authorization/routing. Manager-uploaded escalation_matrix/employee_master versions are retained and validated, but never grant roles or rewrite policy. This is displayed in Data Management. Policy changes require source review and re-ingestion. Data updates never write to POS/ERP systems or automatically embed CSV data.

## Grounding approach

There are two distinct LLM calls: triage and answer selection. Retrieval, read-only tools, workflow and safety are explicit deterministic modules. The Answer Writer selects exact text excerpts from retrieved policy chunks. A final gate checks the chunk ID and literal membership, then reconstructs citation metadata from local source content. Numeric CSV results are rendered separately from pandas outputs. This deliberately limits free-form synthesis; it does not prove relevance, immunity to adversarial phrasing, or universal PII recognition.

Policy chunks normalize CRLF to LF for text processing, while hashes refer to original bytes. Index namespaces include corpus hash and embedding adapter/model/preprocessing signature. Querying a changed corpus/configuration requires successful re-ingestion. Earlier namespaces remain retained but inactive; operators may delete them in Pinecone after verifying backups/current namespace.

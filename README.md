# measurment-stations

## Purpose
This repository is the working foundation for a **bankable soiling-data program** that supports cleaning optimization and financial decision-making for utility-scale solar assets.

The goal is not just to visualize data, but to establish a robust, auditable, and contract-aligned framework so that data produced by the program can withstand review by:
- internal investment committees,
- lenders and technical advisors,
- operators and O&M teams,
- public-sector governance and audit entities.

---

## Program Context and Parties
There are **three core parties** in this program, with two contracts managed by the same project proponent.

### 1) Project Proponent (Renewables Department at the Ministry of Energy)
The project proponent is the owner-side authority and accountable sponsor for the full initiative. They are responsible for oversight of:

1. **Sensor Installation Contract** (field instrumentation delivery and operation), and
2. **Reporting/Data Handling Contract** (data processing, analytics, and reporting outputs).

The proponent also defines acceptance criteria, approves methodologies, and enforces quality and governance obligations across both contracts.

### 2) Contractor A: Sensor Installation & Field Operations Contractor
This contractor designs, installs, calibrates, and maintains field instrumentation and related telemetry for soiling and weather measurements.

### 3) Contractor B: Reporting & Data Handling Contractor
This contractor ingests, validates, transforms, analyzes, and reports data according to approved methods and agreed service levels.

### 4) Us: Data Analytics Assurance Team (Independent Support Function)
We support the renewables department as an independent technical analytics function to ensure outputs are **bankable, reproducible, and decision-grade**.

Our role is to:
- define and enforce data quality rules,
- validate methods and assumptions,
- audit traceability from raw sensor streams to report conclusions,
- identify contractual/technical gaps and drive remediation,
- build the analytics product roadmap and controls baseline.

---

## What “Bankable Data” Means in This Project
For this initiative, data is considered bankable only if it is:

1. **Accurate**: sensor measurements are calibrated and within tolerance.
2. **Complete**: no unexplained gaps beyond agreed thresholds.
3. **Consistent**: definitions and methods are stable and version-controlled.
4. **Traceable**: every KPI/report point can be tied back to source records.
5. **Auditable**: transformations, assumptions, and overrides are logged.
6. **Reproducible**: same inputs + same code version => same outputs.
7. **Timely**: data and reports are delivered within SLA windows.
8. **Governed**: clear ownership, sign-offs, and change management.

---

## Program Governance Model (Who Decides What)

### Governance Bodies
- **Executive Steering Committee (monthly):** strategic direction, escalations, contract performance.
- **Technical Assurance Committee (bi-weekly):** methods, quality metrics, exceptions, acceptance decisions.
- **Operational Working Group (weekly):** incident triage, backlog, deployment and data operations status.

### Decision Rights Matrix (RACI-style summary)
- **Methodology approval:** Proponent (A), Assurance Team (R/C), Reporting Contractor (C), Sensor Contractor (C).
- **Sensor spec changes:** Proponent (A), Sensor Contractor (R), Assurance Team (C), Reporting Contractor (I).
- **Data schema changes:** Proponent (A), Reporting Contractor (R), Assurance Team (C), Sensor Contractor (I).
- **Quality threshold changes:** Proponent (A), Assurance Team (R), both contractors (C).
- **Report release sign-off:** Proponent (A), Reporting Contractor (R), Assurance Team (C).
- **Incident closure:** Proponent (A), relevant contractor (R), Assurance Team (C).

Legend: **R = Responsible, A = Accountable, C = Consulted, I = Informed**.

---

## End-to-End Delivery Plan (Phased)

## Phase 0 — Mobilization and Contract Alignment
**Objective:** create a single, enforceable operating model across both contracts.

### Key activities
- Align definitions (station, sensor, SR, valid day, rain event, cleaning event, etc.).
- Create integrated responsibility matrix spanning both contractors.
- Define acceptance criteria for data, models, and reports.
- Establish issue/escalation workflow and SLA matrix.

### Deliverables
- Program Charter.
- Master RACI and Interface Control Document (ICD).
- Data Governance Standard and Glossary.
- Quality Threshold Register (v1).

### Ownership
- Proponent: approve governance and acceptance criteria.
- Assurance Team: draft standards and quality framework.
- Contractors: confirm execution feasibility and obligations.

---

## Phase 1 — Measurement Design and Field Deployment
**Objective:** ensure measurement system can produce technically valid primary data.

### Sensor contractor responsibilities
- Site survey and station layout design.
- Install sensors per approved engineering standard.
- Perform commissioning and initial calibration.
- Document serial numbers, firmware, calibration certs, geolocation, and wiring diagrams.
- Implement preventive maintenance schedule.

### Proponent responsibilities
- Approve site access and deployment plan.
- Approve instrumentation standard and tolerances.
- Verify contractual compliance and milestone completion.

### Assurance team responsibilities
- Witness FAT/SAT evidence where required.
- Define minimum metadata package required for each sensor/station.
- Validate commissioning completeness against checklist.

### Exit criteria
- 100% commissioned assets have complete metadata records.
- Calibration certificates available and within validity period.
- Telemetry stable for burn-in period (e.g., 14–30 days, agreed in contract).

---

## Phase 2 — Data Ingestion, Standardization, and Storage
**Objective:** establish trusted raw-to-curated data pipeline.

### Reporting contractor responsibilities
- Build ingestion pipeline with schema validation.
- Preserve immutable raw zone (append-only).
- Implement curated zone with validated/typed datasets.
- Record pipeline runs, failures, retries, and reconciliation reports.

### Assurance team responsibilities
- Define validation rules (required fields, ranges, timestamp integrity, duplicates, timezone handling).
- Define quality flags and exclusion logic.
- Audit that no destructive edits occur in raw layer.

### Proponent responsibilities
- Approve hosting/security model and data retention policy.
- Enforce SLA compliance for ingestion and data availability.

### Mandatory controls
- Time synchronization checks across all stations.
- Duplicate and gap detection.
- Outlier detection with reason codes.
- Daily ingestion completeness dashboard.

### Exit criteria
- Reconciliation between telemetry source and warehouse passes agreed thresholds.
- Data quality KPIs published daily.
- Data lineage from raw to curated is machine-traceable.

---

## Phase 3 — Data Quality Assurance and Bankability Controls
**Objective:** make quality measurable, enforceable, and auditable.

### Core quality dimensions and sample thresholds (to be contractually finalized)
- **Completeness:** e.g., >= 98% valid daylight records per station-month.
- **Timeliness:** e.g., T+1 daily availability before fixed cutoff.
- **Validity:** e.g., > 99% records pass schema and physics checks.
- **Consistency:** no unauthorized unit/definition drift.
- **Integrity:** no unexplained record mutation post-ingestion.

### Responsibilities
- Reporting contractor: produce quality scorecards and root-cause analyses.
- Sensor contractor: resolve field-driven quality failures (drift, fouling, outages).
- Assurance team: approve quality logic, run independent checks, classify data readiness.
- Proponent: accept/reject month-end data package based on quality gates.

### Required artifacts
- Station-level quality report.
- Exception log with closure evidence.
- Quality gate decision record (accepted / accepted with reservations / rejected).

---

## Phase 4 — Methodology, Modeling, and Validation
**Objective:** ensure analytical outputs are scientifically and financially defensible.

### Method controls
- Versioned methodology document.
- Fixed formula registry (with units and assumptions).
- Change control for model logic and parameters.

### Validation controls
- Backtesting (predicted vs observed behavior after rain/cleaning).
- Sensitivity analysis (tariff, yield, cleaning cost, rainfall assumptions).
- Uncertainty bands (P50/P75/P90 where applicable).
- Benchmarking across stations and periods.

### Responsibilities
- Reporting contractor: implement model and produce validation pack.
- Assurance team: independent review and challenge, approve/reject model release.
- Proponent: final sign-off for operational deployment.

### Exit criteria
- Model passes predefined validation thresholds.
- Assumptions are documented, justified, and approved.
- Release tagged with reproducible run manifest.

---

## Phase 5 — Reporting, Decision Support, and Operationalization
**Objective:** convert trusted analytics into action and governance-grade reporting.

### Report layers
1. **Executive:** portfolio-level value at risk, avoided loss, confidence summary.
2. **Operational:** station action queue, cleaning triggers, incident impacts.
3. **Technical appendix:** data quality, assumptions, version IDs, exceptions.

### Responsibilities
- Reporting contractor: produce scheduled and ad-hoc reports.
- Assurance team: certify analytical integrity of published reports.
- Proponent: consume and approve policy/operational decisions.

### Operational integrations
- Alerting for threshold breaches.
- Work-order handoff to operations/CMMS.
- Post-clean verification and closed-loop performance tracking.

---

## Phase 6 — Continuous Improvement and Scale-Out
**Objective:** increase reliability, automation, and investment confidence over time.

### Continuous improvement backlog themes
- Advanced rain effectiveness models.
- Partial cleaning optimization by block/zone.
- Portfolio optimization under crew constraints.
- Automated anomaly classification.
- Standardized lender/technical-advisor export packs.

### Governance of improvements
- All changes pass impact assessment (quality, cost, timeline, bankability risk).
- All accepted changes are versioned and communicated.
- Historical comparability preserved through versioned baselines.

---

## Detailed Responsibility Rules by Domain

## A) Sensor Hardware, Calibration, and Field Integrity
**Primary owner:** Sensor Contractor
- Maintain calibration schedule and records.
- Replace failed/drifting sensors within contractual MTTR.
- Keep maintenance logs with timestamped interventions.
- Ensure physical security and tamper reporting.

**Assurance checks:**
- Random audit of calibration evidence.
- Drift trend monitoring and out-of-tolerance alerts.

## B) Data Ingestion and Platform Reliability
**Primary owner:** Reporting Contractor
- Run pipeline monitoring with alert thresholds.
- Maintain replay/recovery process for failed loads.
- Preserve immutable raw data and signed hash/checksum where required.

**Assurance checks:**
- Re-run selected periods and compare checksums and aggregates.
- Validate idempotent ingestion behavior.

## C) Data Quality Rules and Exceptions
**Primary owner:** Assurance Team (rule ownership), Reporting Contractor (execution)
- Define rulebook and severity levels.
- Tag exceptions with standardized reason codes.
- Enforce closure deadlines by severity.

**Proponent role:**
- Enforce penalties/withholds if persistent non-compliance occurs.

## D) Methodology and Financial Assumptions
**Primary owner:** Assurance Team + Proponent
- Maintain approved assumption register (tariffs, yields, costs).
- Document source, owner, validity period for each assumption.
- Require dual sign-off for any assumption change affecting published outcomes.

## E) Reporting and Publication Control
**Primary owner:** Reporting Contractor
- Publish only approved report versions.
- Embed run IDs, data cutoffs, model version, and quality status in each report.

**Assurance + Proponent:**
- Final release gate and publication approval.

---

## Control Gates (Mandatory Stage Gates)
No phase is considered complete unless its gate criteria are met and signed.

1. **Gate G1 (Deployment Ready):** instrumentation and metadata complete.
2. **Gate G2 (Data Ready):** ingestion and lineage controls validated.
3. **Gate G3 (Quality Ready):** quality KPIs pass thresholds.
4. **Gate G4 (Model Ready):** methodology validated and approved.
5. **Gate G5 (Report Ready):** publishable outputs signed off.

If a gate fails:
- issue a corrective action plan,
- assign owner and due date,
- re-test and re-approve before progressing.

---

## SLA / KPI Framework (Illustrative, finalize contractually)

### Sensor Contractor KPIs
- Sensor uptime.
- Mean time to repair (MTTR).
- Calibration compliance rate.
- Recurrent failure rate.

### Reporting Contractor KPIs
- Ingestion timeliness.
- Pipeline success rate.
- Data quality pass rate.
- Report publication timeliness.

### Assurance Team KPIs
- Independent validation coverage.
- Time to close quality investigations.
- Number of unresolved high-severity findings.

### Program-level KPIs
- Percentage of station-months rated “bankable”.
- Estimated avoidable loss identified vs realized.
- Reduction in data-related report disputes.

---

## Risk Register (Initial)
- **R1:** sensor drift not detected early.
  - Mitigation: automated drift alarms + periodic cross-checks.
- **R2:** hidden data processing errors.
  - Mitigation: lineage logs, independent recomputation samples.
- **R3:** contract boundary ambiguity between two vendors.
  - Mitigation: explicit interface matrix and joint incident process.
- **R4:** methodology changes break historical comparability.
  - Mitigation: semantic versioning + restatement policy.
- **R5:** non-bankable reporting due to missing evidence.
  - Mitigation: mandatory evidence pack before publication.

---

## Minimum Evidence Pack for “Bankable” Monthly Release
Each monthly release should include at minimum:
- Data coverage and quality scorecards by station.
- Exception log with closure status.
- Sensor calibration/maintenance status summary.
- Methodology and model version identifiers.
- Assumption register snapshot.
- Reproducibility manifest (input snapshot + code/version references).
- Signed approvals (reporting contractor, assurance team, proponent).

---

## Implementation Notes for This Repository
This repo will be used to incrementally implement:
1. quality rule engines,
2. auditable transformations,
3. model validation workflows,
4. investor/operator reporting layers.

Near-term focus should prioritize:
- data quality instrumentation,
- assumption/version control,
- transparent audit trails,
- reproducible analytics pipelines.

---

## Next Actions (Execution Checklist)
1. Convert this plan into a tracked backlog (epics, owners, due dates).
2. Finalize contractual thresholds and acceptance criteria.
3. Build and approve data dictionary + quality rulebook v1.
4. Implement gate dashboards G1–G5.
5. Launch pilot month with full evidence pack and lessons learned.
6. Iterate before portfolio-wide rollout.

---

## Document Control
- **Owner:** Data Analytics Assurance Team
- **Approver:** Renewables Department (Project Proponent)
- **Contributors:** Sensor Contractor, Reporting Contractor
- **Version:** 1.0 (initial detailed planning baseline)

# CW1 Guide: Database Fundamentals (6CS546)

Plain-English summary of the assessment brief, the PRS scenario and the NHS FHIR sample, plus a step-by-step plan. Everything here comes from the three files your instructor uploaded; page references are to the 16-page Assessment Brief PDF.

---

## 1. CW1 at a glance

| Item | What the brief says |
|---|---|
| Name | CW1: Database Design and Development |
| Weight | **50% of the module** (CW2 is the other 50%) |
| Type | Individual. No collaboration with anyone. |
| Deliverable | One document: **Database Design Document (D-I)** |
| Deadline | **Friday 30 October 2026, 12:00 noon UK time** |
| Format | PDF (preferred) or Word |
| File name | `{studentID}_DDD.pdf` (or `{studentID}_DDD.docx`) |
| Where | Blackboard submission point only. Emailed work is not accepted. |
| Word limit | **None.** The brief says avoid unnecessary definitions and explanations. Diagrams are the main content. |
| Font | Size 12 for main text, clear section headers |
| Diagrams | Clear, readable, labelled with figure numbers (Figure 1, Figure 2…) |
| Checks | Plagiarism check on submission; random checks and end-of-term demonstrations |
| Feedback | 11:59 pm UK time, 15 working days after the deadline |
| Late work | University late policy applies. If you have a genuine reason, apply for a RAC (Request for Additional Considerations) or Support Plan. |

**What CW1 is NOT:** no code, no SQL scripts, no dashboard, no video. Those are all CW2. CW1 is purely analysis and design (diagrams + short explanations).

---

## 2. What you actually have to produce

Three models, all in one document:

1. **Conceptual ER model** (one diagram, technology-agnostic). Shows *all* entities, their attributes, and the relationships between them (with cardinality). No SQL types, no "table" talk yet.
2. **Relational logical model**: a schema diagram suitable for MS SQL Server (tables, columns, primary keys, foreign keys, data types if you like).
3. **Document logical model**: document structures or schema definitions suitable for MongoDB (collections, example JSON documents or JSON Schema, what is embedded vs referenced).

Both logical models must be **derived from your conceptual model**. You decide which parts of the data fit a relational schema and which fit a document store, and you explain why.

### Required sections of the document (in this order)

1. **Title Page**: your name and student ID. (Both are required; this module is not anonymously marked because you'll be assessed face to face.)
2. **Introduction**: summarise the PRS scenario and outline your design approach.
3. **Conceptual Design**: the complete conceptual ER model.
4. **Logical Design**
   - Relational model: database schema diagram.
   - Document model: document structures and/or schema definitions.
5. **Conclusion**: key insights and design choices.

Missing any of these sections costs you on the formatting criterion and probably on the modelling criteria too.

---

## 3. How it is marked (the rubric, p.13)

| Criterion | Weight | What gets top marks (90–100%) | What a typical "Good" (50–59%) looks like |
|---|---|---|---|
| **Conceptual Modelling** | **45%** | ER model complete, accurate, well-structured; all entities, attributes and relationships correctly modelled; consistent and professional | Covers main requirements, but some relationships wrongly modelled or attributes missing |
| **Logical Modelling** | **50%** | Relational and document models complete, fully integrated and consistent; structured *and* unstructured data handled; both align perfectly with the conceptual ERD | Only one model shown (e.g. relational) and document mapping missing or weak |
| **Submission Compliance & Formatting** | **5%** | Polished, well-labelled diagrams, consistent structure | Mostly well formatted with some clarity issues |

What this tells you:

- **95% of the mark is the diagrams.** Prose matters only to explain choices.
- **Coverage is everything for the conceptual mark.** Missing a part of the scenario (e.g. purchase schedules by DOB, family members, merchant locations, audit logs) drops you out of the top bands.
- **You need both logical models.** Only doing relational caps you at around 50–59% on the biggest criterion.
- **Consistency between models is explicitly marked.** The same thing should have the same name in the ERD, the SQL schema and the MongoDB collection. "Mismatched entities or duplicated data" is listed as a 60–69% flaw.
- **"Undefined keys or broken links"** is listed as a 40–49% flaw, so every table needs a primary key and every relationship a correct foreign key.
- **Unstructured data** (PDF vaccination certificates, images) must be visibly handled somewhere in your design to reach the top band.

---

## 4. The rules you must not break (AI use, p.15)

This is important, because it affects how you should use me.

**Allowed:** using AI to clarify concepts, explore alternatives, get feedback on your thinking, understand example data (like the JSON), and (for CW2) help with dashboard/API code.

**Not allowed:** using AI to generate your ER model, logical models, schemas or conversions; submitting AI-written text or diagrams; producing the final version without your own work.

The brief also says there will be **random checks and end-of-term demonstrations** where you must explain and defend your models. If you can't explain a design choice, it is treated as misconduct.

So: I can explain concepts, help you read the scenario, review a draft model you've made and point out gaps or errors, and quiz you on it. I won't draw the models for you, and you shouldn't ask any AI to.

---

## 5. Understanding the PRS scenario (the CW Scenario docx)

The Pandemic Resilience System is a government platform used during a pandemic by three kinds of user: **government officials**, **merchants** (pharmacies, grocery stores), and **the public**. The scenario is the source of your requirements. Here is what each part is really asking your data model to store. Use this as a checklist when you check your own ERD for coverage, not as a list of entities to copy: deciding the entities and how they relate is your job.

### 5.1 Privacy and identity
- Every person gets a unique **PRS-Id**.
- The PRS-Id maps to their **National Identifier**, which can be one of several types (Passport ID, Driving Licence Number, BRP).
- The system stores the National Identifier and **Date of Birth**, both **encrypted**.
- Only certain roles may decrypt them.

*Questions to ask yourself:* Can one person have more than one national identifier? How will you show the "type" of identifier? Which attributes are sensitive and how will you mark them in the diagram?

### 5.2 Government dashboard
- **Purchase limits** on critical items, e.g. one 4-litre milk pack per day, max 7 face masks per week. So a limit has an item, a quantity and a time period.
- **Purchase schedules by DOB**, e.g. birth years ending in 0 or 2 may buy masks on Monday, 1 or 3 on Tuesday.
- **Merchant enrolment**: business licence number, name, operational addresses.
- Merchants record **every purchase** and **stock levels** of critical items.
- **Vaccination tracking** for residents and visitors from abroad; officials **validate and verify** uploaded records; compliance with vaccination policy per dose and period.

### 5.3 Public dashboard
- People enrol **themselves and family members (children under 18)**, each getting their own PRS-Id. (There's a relationship hiding here.)
- **Critical item locator**: find nearest location with stock, and check whether *they* are allowed to buy today.
- **Upload vaccination records**: as **PDF** (unstructured) or **machine-readable FHIR JSON/XML** (semi-structured). Machine-readable reports are saved automatically.

### 5.4 Merchants
- A merchant (business) has **separate accounts for each operational location** (store). Note: one business, many stores.
- Before a sale, the store checks eligibility using the person's **DOB and purchase history**.
- Stores keep **stock levels** up to date so the public can find supplies.

### 5.5 Security and compliance
- Encryption of sensitive personal data.
- **RBAC**: users, roles and permissions.
- **Audit logs** of access to sensitive data.
- HTTPS/TLS (this is a CW2 implementation matter, but you can mention it).

### 5.6 Use cases (A–D)
- **Alerts** when individuals or businesses break limits.
- Notifications to individuals about nearby stock.
- Vaccination certificates verified for **border checks**.
- Real-time updates on pandemic news, vaccination schedules and stock.

### 5.7 Data types the brief insists you handle
| Kind | Examples from PRS |
|---|---|
| Structured | people, merchants, stores, items, stock, purchases, limits, users/roles |
| Semi-structured | FHIR JSON/XML immunisation reports |
| Unstructured | PDF vaccination certificates, images |

---

## 6. The NHS FHIR JSON sample, explained

The file `NHS-Immunization-FHIR-JSON.json` is an example of what a traveller might upload. It is a FHIR **Bundle** (a wrapper) with three entries:

- **Two `Immunization` resources**: one per vaccine dose. Each has:
  - `id`, `status` ("completed")
  - `vaccineCode`: the vaccine product (SNOMED code + display name, here AstraZeneca)
  - `patient`: reference to the patient, including their **NHS number** (a national identifier)
  - `occurrenceDateTime`: when the dose was given (10 Dec 2020 and 31 Dec 2020)
  - `manufacturer`, `lotNumber`, `expirationDate`
  - `site` (left upper arm) and `route` (intramuscular)
  - `doseQuantity`
  - `performer`: the organisation that gave it (ODS code RX809, "TEST-SITE")
  - `reasonCode` ("Disease outbreak")
  - `protocolApplied.doseNumberPositiveInt`: the dose number
  - `location`: country code (GB)
- **One `Patient` resource**: NHS number and `birthDate` (1965-02-28).

Things worth noticing (good material for your design rationale):

- Nested, repeating structures everywhere (`coding` arrays inside `vaccineCode`, `site`, `route`; arrays of `performer`, `identifier`). That's why the brief points you toward a **document model** for this kind of data.
- Other countries' reports may have **different fields**. A flexible schema handles this; a rigid table doesn't.
- It contains a **national identifier and DOB**, so it is sensitive data too.
- A small quirk: `"total": 2` counts only the Immunization entries, and **both doses say `doseNumberPositiveInt: 1`** even though the second has a later date and is described with the same "first dose" text. Real data is messy; you might mention how your design would deal with inconsistent imported data (e.g. keeping the original document and recording a verification status).

The NHS API documentation linked in the scenario is https://digital.nhs.uk/developer/api-catalogue/immunisation-history-fhir if you want field definitions.

---

## 7. Key design ideas to understand before you start

These are the concepts the marks hinge on. If any feels shaky, ask me to explain it.

- **Entity, attribute, relationship, cardinality** (1:1, 1:N, M:N) and **participation** (optional vs mandatory).
- **Weak entities** and **associative (bridge) entities** for M:N relationships.
- **Primary keys, foreign keys, composite keys, surrogate keys.**
- **Normalisation** to 3NF for the relational part (no repeating groups, no partial or transitive dependencies).
- **Conceptual vs logical**: conceptual = what data exists and how it relates, no technology. Logical = how it's laid out in a particular kind of database.
- **Mapping ERD → relational**: entities become tables, 1:N becomes a foreign key on the "many" side, M:N becomes a junction table.
- **Mapping ERD → document**: decide what to **embed** (data read together, owned by one parent) and what to **reference** (shared, large, or frequently updated separately). Also how you'll store a reference to a PDF/image file (e.g. GridFS or file storage + metadata document).
- **Polyglot persistence / hybrid design**: how the two stores link (e.g. a shared identifier) so the models are "integrated", which the rubric rewards.
- **Showing security in a design**: marking encrypted columns, modelling users/roles/permissions, and an audit log.
- **Scalability**: why document stores scale horizontally for high-volume or variable data (e.g. transactions, uploaded reports), and how you'd justify it.

---

## 8. Step-by-step plan

Today is 8 October 2026; the deadline is **Friday 30 October, 12:00 noon UK time**. That's just over three weeks. Aim to finish by 27–28 October so you have a buffer.

### Week 1 (8–14 Oct): Understand and analyse
1. **Read the scenario docx properly once**, with a highlighter. Underline every *noun* (candidate entity/attribute) and every *verb* linking two nouns (candidate relationship). Section 5 above is a checklist for this.
2. **Make a requirements list** in your own words: one line per thing the system must store or do. Number them (R1, R2…). You'll use these to prove coverage later.
3. **Study the FHIR JSON** (section 6) and decide which of its fields matter to PRS.
4. **Pick a diagramming tool** and stick to it: draw.io (diagrams.net), Lucidchart, or similar. Choose one notation (Crow's Foot is the most common) and use it consistently.
5. **Revise** cardinality, M:N resolution, and normalisation from your lecture notes.

### Week 2 (15–21 Oct): Conceptual model
6. **Draft the conceptual ERD** on paper first: entities, then relationships and cardinalities, then attributes. Keep it technology-free.
7. **Walk through every requirement** (R1, R2…) and check your ERD can store it. Trace a real story through it, e.g. "a parent enrols their child, the child is vaccinated abroad, the parent uploads the PDF, an official verifies it" or "a pharmacy sells 7 masks to someone on a Monday; are they allowed?" If a story can't be answered from your model, something is missing.
8. **Mark sensitive attributes** (national ID, DOB, etc.) clearly, e.g. with a legend.
9. **Draw it neatly** in your tool. Label it Figure 1.
10. Optional but useful: **send me your draft** (photo or export) and I'll review it for gaps and errors without redrawing it.

### Week 3 (22–28 Oct): Logical models and write-up
11. **Classify your data**: for each entity/domain, decide relational vs document and write one sentence why. (Typical reasoning: strict integrity, transactions and joins → relational; nested, variable, high-volume or file-based data → document.)
12. **Relational logical model**: convert relational entities to tables. Add PKs, FKs, junction tables, data types (SQL Server), and constraints. Check 3NF. Draw the schema diagram.
13. **Document logical model**: define each MongoDB collection with an example document or JSON Schema. Show embedding vs referencing, how FHIR reports and PDFs are stored, and how documents link back to the relational side (shared IDs).
14. **Consistency pass**: same names across all three models; every conceptual entity appears in at least one logical model; no unexplained duplication.
15. **Write the short text**: Introduction (scenario + approach), brief notes under each diagram explaining key choices, Conclusion (key insights and trade-offs). Keep it lean; no textbook definitions.
16. **Format**: title page with name + ID, font 12, headings, figure numbers on every diagram, diagrams large enough to read when printed (put big ones on landscape pages if needed).

### Final days (28–30 Oct): Check and submit
17. Run the checklist below.
18. Export to PDF, name it `{studentID}_DDD.pdf`, open it once to make sure the diagrams are readable.
19. Submit on Blackboard **well before noon on 30 October**. Check the confirmation/receipt.
20. **Prepare to explain it.** Be ready to say why every entity, relationship and relational-vs-document choice exists. This protects you in the random checks and demonstration.

---

## 9. Final submission checklist

- [ ] Title page with **name and student ID**
- [ ] Introduction, Conceptual Design, Logical Design (relational + document), Conclusion all present
- [ ] Conceptual ERD covers identity/PRS-Id, national identifiers, family members, merchants and their locations, items, stock, purchases, limits, DOB-based schedules, vaccination records (incl. PDF and FHIR uploads), verification, users/roles, audit logging, alerts/notifications
- [ ] Every relationship has cardinality shown
- [ ] Relational schema: every table has a PK, every FK points to a real table, M:N resolved, normalised
- [ ] Document model: collections defined with structures/schema; embed vs reference decisions shown; unstructured files handled
- [ ] Sensitive/encrypted data clearly identified
- [ ] Same names used across all three models
- [ ] Every diagram labelled (Figure 1, 2, …) and readable
- [ ] Font size 12, clear headings
- [ ] File named `{studentID}_DDD.pdf` (or `.docx`)
- [ ] Submitted on Blackboard before **12:00 noon UK, Fri 30 Oct 2026**
- [ ] You can explain every design decision out loud

---

## 10. How CW2 relates

CW2 (also 50%, due **Friday 4 December 2026, 12:00 noon UK**) builds directly on CW1:

- You **refine** your CW1 logical models (using the feedback on CW1) and **implement** them: relational in MS SQL Server, document in MongoDB.
- You build **APIs**, a **web dashboard** for the three user roles, and **RBAC/audit logging**.
- You submit a ZIP (`{studentID}_DII.zip`) with a report, SQL scripts (DDL + dummy-data inserts), source code, and a mandatory video demo (`{studentID}_videoDemo.{format}`). Video guidelines will be released two weeks before the CW2 deadline.

So the scenario docx and the FHIR JSON are shared by **both** courseworks. A thorough, consistent CW1 design makes CW2 much easier, because you'll be building exactly what you designed. A sloppy CW1 means redesigning under pressure in November.

(Minor inconsistency in the brief: the key-dates table says CW2 is due 4 December, but a footnote mentions "CW2: 5 December". Treat **4 December** as the deadline and confirm with the module leader if unsure.)

---

## 11. Who to ask

Module leader: **Maqbool Hussain**, M.hussain@derby.ac.uk, office MS312. The brief says to use the Blackboard discussion forums (and Teams if needed) for questions.

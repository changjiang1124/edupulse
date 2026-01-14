# ISSUES.md

> How coding agents should help generate and maintain work items (issues) from specs and plans.

Issues are the unit of work in Linear. They connect **product intent** (PRDs and specs) and **implementation detail** (ExecPlans and code).

This document explains how to structure issues so they are useful for humans and agents and how to derive them from specs and plans.

---

## 1. When to generate issues

Issues should be created or updated when:

- A new large feature spec and plan are ready.
- A set of tasks in an ExecPlan's **Progress** section needs to be turned into trackable units of work.
- A human asks for issues to be generated or updated based on changes in specs/plans.

Do **not** automatically create a large number of issues without a clear Plan. For small changes, a single issue with a mini-spec in its description is often enough.

---

## 2. Source of truth for issue content

When generating or updating issues, use these inputs in order of priority:

1. The spec in `docs/specs/EDUP-123-*.md`
2. The ExecPlan in `docs/plans/EDUP-123-*.plan.md`
3. The PRD in Linear / Notion (via `linked_prd` from the spec frontmatter)
4. Relevant architecture and process docs in `docs/architecture/` and `docs/process/`

You should **not** invent new feature requirements. Derive issue content from these sources.

---

## 3. Issue structure (conceptual)

A well-structured issue should include at least:

1. **Title**
   - Format: `[EDUP-123] Short, action-oriented description`
   - Example: `[EDUP-123] Implement tour insights API endpoint`

2. **Summary**
   - 1–3 sentences describing what this specific issue will deliver.
   - Should reference the overarching feature spec and plan where applicable.

3. **Context / Links**
   - Link to the spec (`docs/specs/...`)
   - Link to the plan (`docs/plans/...`) if the issue is part of a large feature
   - Link to the PRD (Linear / Notion) if useful

4. **Scope**
   - Bullet list describing what is in scope for this issue.
   - Explicitly mention surfaces (web, mobile, api, data) touched by this issue.

5. **Acceptance Criteria**
   - Clear checklist of behaviors that must be true for the issue to be considered done.
   - Directly derived from the spec's "Acceptance Criteria" and/or Plan's validation steps.

6. **Implementation Notes (optional)**
   - Any hints from the ExecPlan that are relevant for the assignee.
   - References to specific modules or files if important.

7. **Metadata (handled in Linear UI / MCP)**
   - Assignee
   - Labels / area (e.g. `web`, `mobile`, `api`, `data`)
   - Size estimate (e.g. `S | M | L`)
   - Type (e.g. `feature`, `bug`, `chore`)

Depending on the MCP integration, some of this may be captured as fields rather than markdown. The logical structure remains the same.

---

## 4. Mapping from ExecPlan to issues

ExecPlans in `docs/plans/` typically contain a **Progress** section that looks like a checklist of milestones or tasks.

When generating issues from a Plan:

1. **Identify milestones**
   - Each major checkbox item in the Progress section is a candidate issue.
   - Very small steps may be grouped into a single issue if they naturally belong together.

2. **Create one issue per milestone**
   - Use the milestone description as the base for the issue title.
   - In the issue body:
     - Reference the Plan and Spec at the top.
     - Copy or adapt the relevant Concrete Steps and Validation items into the Scope and Acceptance Criteria.

3. **Preserve ordering and dependencies**
   - If some tasks must happen before others, mention that in the issue description.
   - Example: “Depends on `[EDUP-123] Define tour insights schema in API`.”

4. **Keep issues focused**
   - Each issue should be completable in a few hours to a day.
   - Avoid creating issues that are so large they require their own Plan.

---

## 5. Issues for small changes

For small, localized changes (see `CONTEXT.md`), a single issue is usually enough.

When drafting such an issue, include:

1. **Title**
   - Example: `[EDUP-207] Fix misaligned CTA on tour details page`

2. **Current behavior**
   - Briefly describe what is happening today.

3. **Desired behavior**
   - Describe what should happen after the fix or change.

4. **Acceptance Criteria**
   - Checklist of observable conditions that define success.

5. **Surface / area**
   - Mention explicitly which app/package is affected (`web`, `mobile`, `api`, etc.).

Specs and Plans are typically **not** created for small issues like this unless they grow in scope.

---

## 6. Steps to generate issues from a spec + plan

When asked to “generate issues” for a feature with ID `EDUP-123`:

1. **Read the spec**
   - Open `docs/specs/EDUP-123-*.md`.
   - Understand the Summary, Scope, UX Contract, API Contract, and Acceptance Criteria.

2. **Read the plan**
   - Open `docs/plans/EDUP-123-*.plan.md`.
   - Identify the major tasks and milestones in the Progress and Concrete Steps sections.

3. **Draft issue set**
   - Create a list of issues such that:
     - Each critical part of the implementation is covered.
     - Issues can be executed somewhat independently.
     - Acceptance criteria across all issues together satisfy the spec’s Acceptance Criteria.

4. **For each issue, define**
   - Title
   - Short summary
   - Scope bullets
   - Acceptance Criteria
   - Links to spec and plan

5. **Check coverage and overlap**
   - Confirm that every acceptance criterion in the spec is owned by at least one issue.
   - Confirm that issues do not heavily overlap or duplicate each other.

6. **Output in the expected format**
   - Depending on the MCP integration, this might be a markdown list, a JSON payload, or another structure. Follow the caller’s instructions.

---

## 7. Updating issues when specs or plans change

When a spec or plan is changed:

1. Identify all issues linked to that spec/plan.
2. Update their descriptions if:
   - Scope has changed.
   - Acceptance criteria are no longer accurate.
   - Dependencies between issues have changed.

Avoid letting issues drift away from the underlying spec and plan. Issues should remain truthful representations of the work required to satisfy the feature’s intent.

---

## 8. Principles

When helping with issues, follow these principles:

- **Clarity over cleverness**  
  Write issues so that a new engineer can pick them up without reading the entire spec if needed.

- **Traceability**  
  Every issue for a large feature should clearly trace back to its spec and plan via IDs and links.

- **Right-sized work**  
  Issues should be small enough to execute in a short, focused block of time but not so granular that they create unnecessary overhead.

- **No hidden requirements**  
  Avoid burying important acceptance criteria in comments or implied text. Make them explicit in the issue body.

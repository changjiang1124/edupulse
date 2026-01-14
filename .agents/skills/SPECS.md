# SPECS.md

> How coding agents should create and maintain engineering-facing specs in `docs/specs/`.

Specs are **agent- and engineer-facing PRDs**. They translate human-facing product docs (PRDs in Linear / Notion) into clear technical contracts for implementation.

---

## 1. When to create or update a spec

Create or update a spec when:

- A feature is a **large feature** (see `CONTEXT.md`):
  - Touches multiple surfaces (web, mobile, API, data)
  - Introduces or changes APIs or shared contracts
  - Has non-trivial UX / product implications
- A human explicitly asks you to draft or revise a spec.

Do **not** create a spec when:

- The change is clearly small and localized (copy change, small bug fix, minor UI tweak).
- The Linear issue already contains adequate technical detail and is explicitly marked as a small change.

If you are unsure, prefer **not** to create a new spec automatically. Instead, you may suggest that a human promote the work to a full spec + plan.

---

## 2. Location and naming

- Specs live in: `docs/specs/`
- File naming convention: `ARGN-123-short-slug.md` where:
  - `ARGN-123` is the Linear issue ID or feature ID
  - `short-slug` is a kebab-case summary of the feature

Example:

- `docs/specs/ARGN-123-tour-insights-timeline.md`

Each spec corresponds to a **feature**, not necessarily a single Linear issue. Multiple issues may map to one spec.

---

## 3. Inputs for a spec

When drafting or updating a spec, use these inputs where available:

1. The canonical PRD (usually in Linear / Notion)
2. Any existing spec for the feature in `docs/specs/`
3. Relevant architecture docs in `docs/architecture/`
4. Related ExecPlan in `docs/plans/` if it already exists

You should not invent product strategy or requirements. Derive behavior from the PRD and surrounding docs, and be explicit about assumptions.

---

## 4. Spec structure (template)

Every spec must follow this structure:

```md
---
id: ARGN-123
title: Human-readable feature name
status: drafted    # one of: idea | drafted | in-progress | shipped | deprecated
area: web, api     # comma-separated list, e.g. web, mobile, api, data
size: M            # one of: XS | S | M | L | XL
owner: neo         # GitHub handle or name
linked_prd: https://linear.app/argn/issue/ARGN-123
---

# Summary

One short paragraph describing what this feature does and for whom.

# User Story

"As a [user type], I want [goal], so that [value]."

Optionally include multiple stories if needed, but keep each one crisp.

# Scope

## In scope

- Bullet list of behaviors and surfaces that **will be** implemented.

## Out of scope

- Bullet list of things that **will NOT** be implemented, even if they sound related.

# UX Contract

High-level UI expectations for each surface.

## Web

- Primary routes (e.g. `/properties/[id]/tours`)
- Key components and interactions
- Any important loading / empty / error states

## Mobile

- Screens / routes if applicable
- Key flows and offline / degraded behavior assumptions

If a surface is not affected, briefly state that (e.g. "Mobile is not affected by this feature.").

# API Contract

Describe the APIs that this feature depends on or introduces.

- New endpoints (method, path, request, response)
- Changes to existing endpoints
- Error cases and status codes
- Any relevant auth / permission rules

Where possible, include example payloads. This should align with the FastAPI implementation in `services/api` and the generated client in `packages/api-client`.

# Data & Domain Notes

Describe important domain concepts and data fields:

- New or changed entities or fields
- How this interacts with core domain entities (property, unit, tour, agent, lease, pricing, etc.)
- Any performance or scale considerations

# Acceptance Criteria

Clear, testable bullets. Each one should be verifiable via UI, API, or tests.

- [ ] When X happens, Y is displayed or persisted
- [ ] Errors are handled as Z
- [ ] Metrics / events A, B, C are captured (if applicable)

# Open Questions

List any unresolved questions or assumptions that require human input.

- Q: ...
- Assumption: ...
```

When updating an existing spec, keep this structure and modify the relevant sections while maintaining clarity and consistency.

---

## 5. How to draft a new spec (step-by-step)

1. **Gather context**
   - Read the PRD in Linear / Notion.
   - Scan related docs in `docs/product/` and `docs/architecture/`.
   - Check `docs/features/overview.md` for any existing feature references.
   - Check if a spec already exists for the same `id` in `docs/specs/`.

2. **Create the file**
   - Determine the Linear ID and slug.
   - Create `docs/specs/ARGN-123-short-slug.md` using the template above.

3. **Fill in frontmatter**
   - Set `id`, `title`, `status` (usually `drafted`), `area`, `size`, `owner`, `linked_prd`.
   - Do not fabricate `linked_prd` URLs; use the provided ones or leave blank if not known.

4. **Write the content**
   - Keep each section concise and focused on **what** should happen, not how to implement it.
   - Reflect domain language used in product docs (e.g., leasing, tours, objections, concessions).
   - Explicitly document non-goals and assumptions.

5. **Check for completeness**
   - Confirm there is at least one clear user story.
   - Confirm scope, UX, API, and acceptance criteria are all present.
   - Confirm the spec is understandable without reading the PRD, for an engineer familiar with the codebase.

6. **Save and link**
   - Ensure the file is placed in `docs/specs/` with the correct name.
   - (External automation) may link the spec back into Linear.

---

## 6. Updating an existing spec

When requirements change or behavior diverges from the spec:

1. Locate the spec in `docs/specs/` by Linear ID.
2. Update:
   - `status` (for example, from `drafted` → `in-progress` → `shipped`).
   - Any sections that no longer match reality (UX, API, acceptance criteria).
3. Prefer small edits that make the spec accurate over rewriting everything.
4. If changes are large, consider adding a short "Changelog" section at the bottom summarizing major shifts.

Do not silently let specs drift far from actual behavior. Specs should remain **close enough to reality** to guide future work and provide context to agents and humans.

---

## 7. Interaction with ExecPlans and issues

- Specs define **what** should be built.
- ExecPlans in `docs/plans/` define **how** to build it.
- Linear issues track **units of work** derived from the ExecPlan's progress checklist and spec's acceptance criteria.

As a coding agent:

- Read the spec first to understand intent and constraints.
- Then read the ExecPlan for concrete steps when implementing.
- When asked to modify issues, refer to `.agent/skills/ISSUES.md` for how to map from spec/plan to issue content.

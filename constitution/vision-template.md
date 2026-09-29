<!-- WHO READS ME: the AI running the Phase-0 vision interview with the owner, before the
     constitution exists; afterwards, any agent that needs to know who the product is for.
     I POINT TO (kit paths; factory/... once adopted): model/PHASE-0.md (the interview and
     the order of Phase 0) · constitution/constitution-template.md (the invariants this vision
     justifies; its Vision line points here) · model/ARCHETYPES.md (the archetype choice).
     Save the filled copy as .specify/memory/vision.md, beside the constitution; `specify init
     --here --force` leaves that directory's files in place (checked with specify-cli 1.0.12).
     A small project may instead answer the first three sections in three lines on the
     constitution's Vision line and skip this file. This file holds no relative link, so the
     saved copy has none to break. -->

# [PROJECT_NAME] — Vision

> Why this product exists and for whom. The constitution says what must never break; this file
> says what the work is for, so an agent optimizing a feature can tell whether it serves the
> right person. Write the owner's words, not a pitch: every sentence should survive the
> question "how do we know?". Mark a guess as `(assumption — check by <date or signal>)`.
> Amend it like the constitution: the owner approves, and the date below moves.

## Problem
[WHO has WHAT problem today, and what they do about it now. EXAMPLE: "Freelancers reconcile
three bank exports by hand in a spreadsheet each month; it takes an evening and misses
duplicates."]

## Users
[The primary user, and anyone else who touches the product (payer, admin, operator). Name
the one whose needs win when they conflict.]

## Value
[What changes for the primary user when the product works — the outcome, not the feature
list.]

## Business model
[Who pays, for what, and roughly how much — or "none: internal tool / open source / personal
use". This decides what the product must never cost to run per user.]

## Non-goals
[What the product deliberately will not do or be, as far as the owner can say today. These
seed the constitution's Non-goals.]

## Success signals
[Two or three observable signals, each with how and when it is checked. EXAMPLE: "the monthly
reconciliation takes under 10 minutes — the owner times the first three months". A signal
nobody measures is a wish.]

## Archetype
[The kind of product — multi-tenant SaaS · backend/API service · mobile + backend ·
frontend-only/static · CLI · library/SDK · data/ML pipeline · embedded/firmware · game ·
IaC/DevOps · LLM/agent app · monorepo, or another — and the one-line reason.
It picks the adopt.py profile and the constitution's slot choices (the kit's
`model/ARCHETYPES.md`).]

## Data and risk
[What the product stores or touches that would hurt someone if it leaked, was lost or was
wrong — personal data, money, credentials, a device that can be bricked. This seeds Article II
of the constitution. "Nothing" is an answer; say why.]

**Owner**: [NAME] | **Written**: [YYYY-MM-DD] | **Last revised**: [YYYY-MM-DD]

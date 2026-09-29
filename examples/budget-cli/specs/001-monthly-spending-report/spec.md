---
feature: 001-monthly-spending-report
status: accepted
epic: core
owner: Lan
approved_by: Lan
approved_on: 2026-09-28
---
<!-- WHO READS ME: anyone building, reviewing or accepting budget-cli's feature 001 — the
     WHAT/WHY, and the feature's technical document (one source). Generated from the kit's
     spec-template override (../../../../speckit/overrides/spec-template.md), so the
     frontmatter above opens at line 1 and holds the only status. I POINT TO: plan.md (HOW) ·
     tasks.md · quickstart.md · acceptance.md · ../../constitution.md (Articles I, II, V, VI) ·
     ../../../../model/PHASE-0.md §7 (why feature 001 is a walking skeleton). -->

# Feature Specification: Monthly spending report from one statement CSV

**Feature Branch**: `001-monthly-spending-report` (no git branch: the project is main-only)

**Created**: 2026-09-28

**Input**: User description: "A Python command-line tool that reads a bank-statement CSV file
and prints a spending report by month." (the owner's words, translated from Vietnamese) —
first slice: one file in the generic three-column layout, totals per month. As feature 001 it
is also the walking skeleton that wires the gate chain.

## User Scenarios & Testing *(mandatory)*

**Tests**: required. This project works test-first (constitution Article VI): every user
story below gets test tasks, written and seen to fail before the code that makes them pass.

### User Story 1 - See how much I spent each month (Priority: P1)

As the account holder, I point the tool at one exported statement file and see, per calendar
month, how much money went out, so I know my monthly spending without a spreadsheet.

**Why this priority**: It is the whole idea in its smallest useful form.

**Independent Test**: Run the installed command on a fixture statement with known rows; the
printed monthly totals equal the hand-computed ones.

**Acceptance Scenarios**:

1. **Given** a statement with debits in January and February 2026, **When** I run the report
   on it, **Then** I see one line per month, oldest first, each with the sum of that month's
   debits, then a grand total and the row counts.
2. **Given** a statement containing credits (money in), **When** I run the report, **Then**
   credits are not counted as spending.

---

### User Story 2 - The gate chain guards every commit (Priority: P1)

As the owner, I run one command and see every gate slot green, or N/A with its reason, and a
commit with a red slot is refused — locally and in CI — so that "done" means the same thing
for every later feature.

**Why this priority**: Feature 001 is the walking skeleton
([PHASE-0 §7](../../../../model/PHASE-0.md)): nothing after it can rely on the chain unless
this feature wires it.

**Independent Test**: `./gates/run-chain.sh` exits 0 with no `not wired` slot; a deliberately
unformatted file makes the `format` slot red and the commit is refused.

**Acceptance Scenarios**:

1. **Given** the finished feature, **When** the owner runs `./gates/run-chain.sh --list`,
   **Then** every slot shows a command or N/A with a reason, none `not wired`.
2. **Given** an unformatted source file, **When** anyone commits, **Then** the pre-commit hook
   refuses the commit and names the red slot.

---

### User Story 3 - Trust the numbers (Priority: P2)

As the account holder, if some rows cannot be read I am told which ones, so I never act on a
silently incomplete total.

**Why this priority**: A wrong total the user trusts is worse than no total (constitution
Article I).

**Independent Test**: Run on a fixture with one malformed date and one malformed amount; the
report lists both rows by line number, and accepted + rejected = rows read.

**Acceptance Scenarios**:

1. **Given** a row whose amount is not a number, **When** I run the report, **Then** that row
   is listed as rejected with its line number and reason, and the other rows are still
   reported.
2. **Given** any input, **When** the report prints, **Then** it states rows read, accepted and
   rejected, and accepted + rejected = read.

### Edge Cases

- An empty file, or a header with no rows → 0 rows read, no months, a total of 0, exit status
  success.
- The file does not exist → a clear error, a non-zero exit status, nothing on stdout.
- Amounts with thousands separators ("1,250,000") → parsed exactly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST read one statement file with a header row and the columns date,
  description, amount.
- **FR-002**: The tool MUST treat negative amounts as spending and ignore non-negative amounts
  for spending totals.
- **FR-003**: The tool MUST print one line per calendar month that has spending, oldest first,
  with the month's total spending, followed by a grand total.
- **FR-004**: The tool MUST report every unreadable row with its line number and reason, and
  MUST print the rows read, accepted and rejected.
- **FR-005**: Amounts MUST be summed exactly, with no rounding drift.
- **FR-006**: The tool MUST NOT make any network connection.
- **FR-007**: Every commit MUST pass the project's gate chain, and a commit on a red chain MUST
  be refused locally and in CI.

### Key Entities

- **Transaction**: one statement row — date, description, signed amount, line number.
- **Rejected row**: a line number and the reason it could not be read.
- **Monthly total**: a calendar month and the total spending in it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the reference fixture, every monthly total matches the hand-computed value to
  the last unit of currency — 100% of months.
- **SC-002**: For every fixture, accepted + rejected = rows read.
- **SC-003**: A first-time user gets a report from an exported file with a single command and
  no configuration.
- **SC-004**: A commit with a red gate is refused every time it is tried, with the red slot
  named.

## Assumptions

- Dates are DD/MM/YYYY, the common layout of Vietnamese bank exports. Other layouts are a
  later spec.
- One currency per file; no conversion.
- Bank-specific layouts are later specs; this slice reads the generic three-column layout.

## Clarifications

### Session 2026-09-28

- Q: Which sign means spending? → A: A negative amount is money out. (Lan)
- Q: Which date format? → A: DD/MM/YYYY. (Lan)
- Q: What should the output look like? → A: A plain-text table in the terminal. (Lan)

<!-- WHO READS ME: the implementer of budget-cli feature 001 — the records that flow through
     parse → report → render. Nothing is stored: these exist for one run. I POINT TO: plan.md ·
     contracts/cli.md (how they are printed) · ../../constitution.md (Articles I and II). -->

# Data Model: Monthly spending report

Nothing is persisted. Each run reads one file and builds these in memory.

## Transaction (src/budget/parse.py)

| Field | Type | Rule |
|---|---|---|
| `date` | `datetime.date` | parsed from DD/MM/YYYY; anything else rejects the row |
| `description` | `str` | copied as read; never printed or logged (Article II) |
| `amount` | `decimal.Decimal` | signed; negative = money out; thousands separator `,` removed before parsing |
| `line` | `int` | the CSV line number, header = line 1 |

## Rejected (src/budget/parse.py)

| Field | Type | Rule |
|---|---|---|
| `line` | `int` | as above |
| `reason` | `str` | `unreadable date` or `unreadable amount` |

## ParseResult (src/budget/parse.py)

`read: int`, `accepted: list[Transaction]`, `rejected: list[Rejected]`.
**Invariant (Article I)**: `len(accepted) + len(rejected) == read`, asserted in `cli` before
anything is printed.

## Report (src/budget/report.py)

`months: list[tuple[str, Decimal]]` — `("YYYY-MM", total spending)`, oldest first, only months
with spending · `total: Decimal` — the sum of `months`. Built by a pure function from the
accepted transactions: no I/O (Article III).

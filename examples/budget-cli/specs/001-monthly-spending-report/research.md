<!-- WHO READS ME: the implementer and reviewer of budget-cli feature 001 — the decisions behind
     plan.md, one per line of reasoning. I POINT TO: plan.md · spec.md (Clarifications) ·
     ../../constitution.md (Articles II and VII decide most of these). -->

# Research: Monthly spending report from one statement CSV

## Amounts: `decimal.Decimal` from the string

- **Decision**: parse each amount with `Decimal(text)` after removing the thousands separator
  `,`; an amount that does not parse rejects the row.
- **Rationale**: constitution Article II — exact money, never a guess.
- **Alternatives considered**: `float` (rejected: binary rounding drift); integer minor units
  (rejected: VND has no minor unit, other currencies do, so the unit would be a per-bank guess).

## Dates: `datetime.strptime(text, "%d/%m/%Y")`

- **Decision**: DD/MM/YYYY only, per the 2026-09-28 clarification; any other shape rejects the
  row with the reason `unreadable date`.
- **Rationale**: one layout, stated, beats a guessing parser that reads 03/02 as March for one
  bank and February for another.
- **Alternatives considered**: `dateutil.parser` (rejected: a runtime dependency, and it
  guesses).

## Reading the file: `csv.DictReader`, UTF-8

- **Decision**: open with `newline=""` and `csv.DictReader`, keyed on the header names
  `date`, `description`, `amount`; `reader.line_num` is the reported line number.
- **Rationale**: standard library (Article VII); the header names make column order
  irrelevant.
- **Correction found by converge (T019)**: the first implementation opened the file as
  `utf-8`. A file saved with a byte-order mark then has a first column named `\ufeffdate`, so
  every row was rejected as `unreadable date`. The fix opens it as `utf-8-sig`, which strips a
  leading mark and reads a file without one unchanged.

## Command shape: `argparse` with one subcommand, `report`

- **Decision**: `budget report FILE`.
- **Rationale**: standard library; the subcommand leaves room for later ones (an adapter per
  bank, a category report) without breaking the first.

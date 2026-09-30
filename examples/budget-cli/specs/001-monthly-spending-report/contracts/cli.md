<!-- WHO READS ME: whoever tests or accepts budget-cli feature 001 — the command's contract. Exit
     codes and output format are part of it and are asserted by tests/e2e and quickstart.md.
     I POINT TO: ../spec.md (FR-001–FR-006) · ../quickstart.md · ../data-model.md. -->

# CLI contract: `budget report FILE`

**Invocation**: `budget report <path>` — one file, the generic three-column layout
(`date,description,amount`, header row first, DD/MM/YYYY dates). `budget --help` lists the
`report` subcommand.

**stdout**, in this order:

```text
YYYY-MM  <total spending that month>     one line per month with spending, oldest first
TOTAL  <total spending>                  always printed; 0 when nothing was spent
rows: read=<N> accepted=<A> rejected=<R> always printed; A + R = N
```

Totals are positive amounts, printed exactly as summed (`Decimal`), never rounded:
`1350000.50` stays `1350000.50`.

**stderr**: one line per rejected row, `line <L>: <reason>`, in file order; a usage error or a
missing file prints one `budget: …` line.

**Exit status**

| Status | When |
|---|---|
| 0 | a report was printed — including when some rows were rejected |
| 2 | usage error (argparse), or the file does not exist; nothing on stdout |

**Never**: a network connection, a written file, a raw row on stdout or stderr.

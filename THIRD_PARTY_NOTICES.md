<!-- WHO READS ME: anyone redistributing this kit or a project that vendors it, and whoever adds
     material adapted from another project. I POINT TO: LICENSE (the kit's own licence) · the
     kit files that carry adapted material, listed per upstream below. -->

# Third-party notices

The kit's own licence is MIT ([LICENSE](LICENSE)). Parts of it are adapted from the five MIT
projects below. The MIT licence asks that each project's copyright notice and permission notice
travel with substantial portions of its work, so they are reproduced here.

The copyright lines were copied from each project's `LICENSE` file on 2026-09-29, at the
upstream commit named in the table. The five permission notices are byte-identical, so the
text is given once, after the table.

| Upstream | Copyright line, as its LICENSE states it | Checked at | Adapted into this kit |
|---|---|---|---|
| [github/spec-kit](https://github.com/github/spec-kit) | Copyright GitHub, Inc. | tag `v1.0.12` (`e77daa9`) — same text at `8d3f64c` | [`speckit/overrides/spec-template.md`](speckit/overrides/spec-template.md) and [`speckit/overrides/tasks-template.md`](speckit/overrides/tasks-template.md), adapted from the specify-cli 1.0.12 templates of the same names; the structure of [`constitution/constitution-template.md`](constitution/constitution-template.md) (the `[PROJECT_NAME]` placeholder convention, Core Principles, Governance and the Version / Ratified / Last Amended line) |
| [obra/superpowers](https://github.com/obra/superpowers) | Copyright (c) 2025 Jesse Vincent | `8ca22db` | [`harness/skills/spec-first/SKILL.md`](harness/skills/spec-first/SKILL.md) (from its brainstorming skill); [`harness/skills/plan-and-tdd/SKILL.md`](harness/skills/plan-and-tdd/SKILL.md) (from writing-plans and test-driven-development) |
| [juliusbrussee/caveman](https://github.com/juliusbrussee/caveman) | Copyright (c) 2026 Julius Brussee | `2fd153c` | [`harness/skills/caveman/SKILL.md`](harness/skills/caveman/SKILL.md), from its `skills/` directory |
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | Copyright (c) 2026 DietrichGebert | `e3ba2aa` | [`harness/skills/ponytail/SKILL.md`](harness/skills/ponytail/SKILL.md) |
| [garrytan/gstack](https://github.com/garrytan/gstack) | Copyright (c) 2026 Garry Tan | `65bfb0c` | the careful guard's matcher logic and its two-tier (deny / ask) design, in [`harness/skills/careful/hooks/`](harness/skills/careful/hooks/) (`check-careful.py`, `check-careful.sh`) and [`harness/skills/careful/SKILL.md`](harness/skills/careful/SKILL.md); gstack's telemetry was not carried over |

**caveman's scope note.** caveman's `LICENSE` opens with a note that the MIT licence covers the
repository except its engine-linked directories (`engine/`, `proxy/`, `rewriter/`, `browse/`,
`mcp/`, `shrink/`, the cavemem Go core, `shared/platform/`), which are under the Business Source
License 1.1. Its `LICENSING.md` lists `skills/` as MIT. This kit adapted only the skill; nothing
here comes from a BSL directory.

**Not code, not listed above.** The kit writes its skills in the
[agentskills.io](https://agentskills.io) format and documents Spec Kit's commands in
[`model/SPEC-FLOW.md`](model/SPEC-FLOW.md). Neither copies text from those projects. The Spec
Kit CLI itself is installed by the adopter (`uv tool install specify-cli==1.0.12`) and is not
redistributed here.

When you adapt something new: add its row here in the same commit, with the copyright line
copied from its `LICENSE` (not retyped from a README), the commit you read it at, and the
kit files it went into.

## The permission notice (identical in all five)

```text
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

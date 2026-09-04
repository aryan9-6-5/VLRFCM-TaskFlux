# LaTeX source

`main.tex` is the review paper in IEEE conference format (`IEEEtran`, `conference` option). The bibliography is embedded as a `thebibliography` environment, so there is no `.bib` file and no BibTeX pass to run.

## Compiling

```bash
pdflatex main && pdflatex main
```

Two passes, because the cross-references to Table I, Table II and the section labels resolve on the second one. A third pass changes nothing.

If you would rather not install a TeX distribution, upload `main.tex` to Overleaf and it will compile as-is. `IEEEtran` is preinstalled there.

## What has and has not been checked

There is no LaTeX toolchain on the machine this was written on, so **the file has not been compiled**. It was checked statically instead: brace balance, environment nesting, every `\cite` key resolving to a `\bibitem`, every `\ref` resolving to a `\label`, no unescaped `%` or `_`, and consistent column counts in both tabulars. All of those pass. The document is pure ASCII with no em dashes and no curly quotes.

What static checking cannot catch is overfull horizontal boxes. Table I is the risk. Its six column widths sum to about 15.35 cm, plus roughly 2.1 cm of inter-column padding, which lands near 17.45 cm against the 18.1 cm IEEE double-column text width. That should fit, but the first thing to do after your first compile is search the log:

```bash
grep -n "Overfull" main.log
```

If Table I overflows, shave the two 3.85 cm columns rather than the last one. The comment above the tabular preamble in `main.tex` records what the six numbers sum to, so keep it accurate if you change them.

## Structure

Sections map onto the markdown drafts in `../docs/`:

| LaTeX section | Source |
|---|---|
| Introduction, Background | `01-idea-and-novelty.md`, `00-source-audit.md` |
| Review Method, Thematic Review | `02-review-paper-draft.md` |
| Table I | `03-literature-review-table.md` |
| Gap Analysis, Proposed Architecture | `01-idea-and-novelty.md` |
| Evaluation Protocol | `04-evaluation-protocol.md` |

Edit the markdown when you are working out what to say, and edit the `.tex` when you are working out how it should look on the page. Keeping both in sync by hand is tedious, so once the argument settles, treat `main.tex` as the source of truth and let the markdown go stale.

## Before submission

The verification checklist in `../docs/03-literature-review-table.md` lists which figures in Table I were read directly from the source PDFs and which still need confirming. The Fan and Zheng success rate is the main one outstanding.

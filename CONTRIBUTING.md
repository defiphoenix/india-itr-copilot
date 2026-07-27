# Contributing

The most valuable contributions, in order:

1. **Field reports** — you ran the skill on a real return. Open an issue with the profile shape
   ("salary + RSUs, ITR-2"), what the documents-first inference got right or missed, and where a
   module's guidance was thin or wrong. Redact everything personal; use synthetic figures.
2. **Annual registry refresh** (each April–June) — a new `rules/AY<year>.json` with that year's
   verified rates, each row carrying an official source URL. This is what keeps the skill alive.
3. **Parser coverage** — extraction quirks of brokers, banks, and exchanges beyond the ones
   handled (new password conventions, workbook layouts, statement formats). Include a synthetic
   sample of the format, never a real document.
4. **Tax-content corrections** — must cite incometaxindia.gov.in (Act/circular/notification) or
   the e-filing portal. Blog posts alone don't qualify.

Ground rules: no real PII anywhere (PANs, names, account numbers, actual return figures); registry
values must carry sources; nothing that encourages over-claiming or omission — such PRs are closed
regardless of technical quality; the skill's output boundary is the data pack, so portal-automation
code belongs in a downstream project, not here.

Mechanics: fork → branch → PR, one topic per PR, official source cited in the description.

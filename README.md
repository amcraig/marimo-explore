# marimo-explore

A playground for kicking the tires on [marimo](https://marimo.io) — reactive
Python notebooks — built around a small **cheminformatics** dataset and
**DuckDB**. It doubles as a set of worked examples for the patterns this repo
leans on: PEP 723 self-contained notebooks, `uv`-sandboxed execution,
DuckDB-over-Parquet, Altair charts, and live `mo.ui` widgets.

Every notebook is a standalone marimo app with its dependencies declared inline
(PEP 723), so there is **no shared virtualenv to manage** — `uv` builds an
isolated environment per notebook on demand.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (provides `uvx`) — the only hard
  requirement; each notebook's Python and dependencies are provisioned from its
  inline header.
- Node.js — only if you want GitHub Copilot inline completion inside the marimo
  editor.

> **Always run from the project root.** The notebooks reference `data/` and
> `ketcher_standalone/` by relative path.
>
> The commands below have no sandbox flag: marimo detects the inline PEP 723
> script metadata and **asks in the terminal** whether to run in a sandboxed
> environment — answer yes and it provisions the inline dependencies. If you'd
> rather skip the prompt (e.g. non-interactive runs), add `--sandbox` to any
> command.

## Notebooks

| Notebook | What it shows | Run |
|---|---|---|
| `explore_marimo.py` | marimo 101 — reactivity (dataflow DAG), `mo.ui` sliders/dropdowns, live-updating Altair charts and tables. Default notebook view. | `uvx marimo run explore_marimo.py` |
| `slideshow.py` | A four-step slide deck: DuckDB globbing many Parquet files as one table (with a `by_family` ↔ `shuffled` source toggle), interactive data exploration, static charts, and the same chart driven by live widgets. Slides layout. | `uvx marimo run slideshow.py` |
| `similarity_search.py` | Molecular **similarity-search dashboard**: sketch a molecule in embedded **Ketcher** → SMILES → ECFP4 **Tanimoto** ranking over Parquet (via the `ducksmiles` DuckDB extension) → interactive scatter (cLogP vs MW) with RDKit structure images on hover. Grid layout. | `uvx marimo run similarity_search.py` |

Swap `run` for `edit` to open any notebook in the editor:

```bash
uvx marimo edit similarity_search.py
```

## Data

A toy library of **223 molecules across 20 chemical families**, stored as typed,
fingerprinted **Parquet** in two layouts:

```
data/parquet/
├── by_family/   # 20 files, one per family
└── shuffled/    # 4 files, all 223 molecules spread evenly across them
```

Each row carries `id, family, name, smiles` plus precomputed `canonical_smiles`,
`is_valid`, `formula`, `mol_weight`, `logp`, `n_rotatable_bonds`,
`n_heteroatoms`, and two fingerprint BLOBs (`morgan_fp` ECFP4, `maccs_fp`) —
generated once with the `ducksmiles` DuckDB extension. Because descriptors are
precomputed, the chart/aggregation notebooks need neither RDKit nor `ducksmiles`
at runtime.

The `by_family` and `shuffled` layouts hold the *same* data — querying either
returns identical aggregates, which is the point `slideshow.py` demonstrates:
physical file layout is invisible to SQL.

## DuckDB + `ducksmiles`

The similarity search (`similarity_search.py`) uses the community
[`ducksmiles`](https://duckdb.org/community_extensions/extensions/ducksmiles)
extension for SMILES parsing, descriptors, fingerprints, and `tanimoto_bit`
(the same extension pre-generated the fingerprint columns in `data/parquet/`).
It self-installs on first run (`INSTALL ducksmiles FROM community; LOAD
ducksmiles;`, cached in `~/.duckdb`). **`ducksmiles` only ships builds for
DuckDB 1.5.1–1.5.4**, so those notebooks pin `duckdb==1.5.4` in their headers.

## The Ketcher sketcher (`similarity_search.py`)

`similarity_search.py` serves a bundled, self-contained **Ketcher** build from
`ketcher_standalone/` over a tiny in-kernel HTTP server on **port 2799** and
embeds it in an iframe (running it in its own document sidesteps shadow-DOM
issues). The server runs in a daemon thread inside the marimo kernel, so it is
torn down automatically when the kernel exits — nothing to clean up. Port 2799
must be free when you start the notebook.

> **Heads up: the embedded Ketcher widget can be finicky.** The iframe/postMessage
> bridge and the vendored Ketcher build occasionally misbehave — the editor may be
> slow to appear, fail to seed the default structure, or drop a sketched SMILES on
> the way back to Python. **This is a quirk of Ketcher (and browser iframe
> embedding), not marimo.** If it acts up, first reload the browser tab; if that
> doesn't help, re-run the sketcher cell (it's port-guarded, so it reuses the
> running server), and as a last resort restart the kernel. A hard kill of the
> process can also leave an orphaned server on port 2799 (see Troubleshooting).

## Pairing an AI agent with a live notebook

[`marimo pair`](https://marimo.io/blog/marimo-pair) lets an AI coding agent
(e.g. Claude Code) collaborate inside a *running* notebook — execute code in an
ephemeral scratchpad with your live notebook variables, and add/edit/delete
cells through marimo's `code mode` API — instead of editing the `.py` file
blind.

It's a separate tool, not bundled in this repo. Install it once (requires
Node.js):

```bash
npx skills add marimo-team/marimo-pair
```

Then start a notebook so it registers for discovery, keep it open in a browser,
and ask your agent to pair:

```bash
uvx marimo edit --no-token similarity_search.py -p 2719
```

```
/marimo-pair pair with me on similarity_search.py
```

The live runtime is the source of truth during a session. See the
[announcement post](https://marimo.io/blog/marimo-pair) for details.

## Layouts

marimo layout files live in `layouts/` (`*.grid.json`, `*.slides.json`) and are
referenced from a notebook's `marimo.App(layout_file=...)`. They control the
run-mode presentation (dashboard grid vs. slide deck) without changing the code.
`slideshow.py` uses a slides layout and `similarity_search.py` a grid layout;
`explore_marimo.py` has none and renders as the default scrolling notebook.

## Troubleshooting

- **`ModuleNotFoundError` for duckdb/altair/etc.** — the notebook ran without a
  sandbox, so the inline dependencies weren't provisioned. Either pass
  `--sandbox`, or answer **yes** to marimo's terminal prompt about running in a
  sandboxed environment.
- **Ketcher doesn't load in `similarity_search.py`** — port 2799 is already in use,
  or you didn't launch from the project root (`ketcher_standalone/` must
  resolve). If a previous run was **hard-killed** (`kill -9`, not Ctrl-C), the
  kernel subprocess can be orphaned and keep port 2799 bound; find and kill it
  with `lsof -nP -iTCP:2799 -sTCP:LISTEN` then `kill <pid>`.
- **Ketcher is blank, sluggish, or "loses" a sketched structure** — the embedded
  Ketcher widget (iframe + postMessage bridge) is inherently finicky; **this is a
  Ketcher/browser-embedding quirk, not a marimo bug.** Reload the browser tab,
  re-run the sketcher cell, or restart the kernel.
- **DuckDB "closed pending query result" / `MarimoSQLError` in `marimo run`** —
  reactive `mo.sql` cells sharing one DuckDB connection can collide under
  concurrent execution; opening the notebook in `edit` mode (sequential runs)
  avoids it.

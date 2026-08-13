# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb==1.5.4",
#     "polars",
#     "pyarrow",
#     "sqlglot==30.16.0",
#     "altair==6.2.2",
# ]
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", layout_file="layouts/slideshow.slides.json")


@app.cell(hide_code=True)
def title():
    import marimo as mo

    import altair as alt
    import polars as pl

    # Same 223 molecules, two physical layouts on disk: 20 by-family files or 4
    # evenly-shuffled files. Defined here so the Step 1 slides can read its value
    # reactively (a widget's value can't be used in the cell that defines it).
    source = mo.ui.dropdown(
        options={
            "By family — 20 files (one per family)": "by_family",
            "Shuffled — 4 files (all families mixed)": "shuffled",
        },
        value="By family — 20 files (one per family)",
        label="Parquet source",
    )

    mo.md(
        """
        # From 20 Parquet files to a live chart

        ### A tour of **DuckDB + marimo** in four steps

        Using a small library of **223 molecules** split across **20 Parquet
        files** (one per chemical family), each with precomputed properties
        (`mol_weight`, `logp`, rotatable bonds, heteroatoms).

        1. **DuckDB** — query many files at once, no ETL
        2. **Explore** the data interactively in marimo
        3. **Chart** the data
        4. The **same chart**, now driven by live widgets

        *Advance with the arrow keys.*
        """
    )
    return alt, mo, source


@app.cell(hide_code=True)
def duckdb_total(mo, source):
    # One glob pattern reads a whole directory of Parquet files as a single table --
    # DuckDB streams straight from the files, no load step, no database to manage.
    # Flip `source` between the 20 by-family files and the 4 shuffled files: the
    # query is byte-for-byte identical and so are `molecules` and `families` --
    # only `parquet_files` changes. The physical layout is invisible to SQL.
    totals = mo.sql(
        f"""
        SELECT
            COUNT(*)                       AS molecules,
            COUNT(DISTINCT family)         AS families,
            COUNT(DISTINCT filename)       AS parquet_files
        FROM read_parquet('data/parquet/{source.value}/*.parquet', filename = true)
        """,
        output=False,
    )

    mo.vstack(
        [
            mo.md(
                """
                ## Step 1 — The power of DuckDB

                A single `read_parquet('.../*.parquet')` glob treats **an entire
                directory as one table**. No import, no schema wrangling, no
                server. Switch the source below — same 223 molecules and 20
                families whether they live in **20 files or 4**.
                """
            ),
            source,
            mo.md(
                f"""
                ```sql
                SELECT
                    COUNT(*)                 AS molecules,
                    COUNT(DISTINCT family)   AS families,
                    COUNT(DISTINCT filename) AS parquet_files
                FROM read_parquet('data/parquet/{source.value}/*.parquet',
                                  filename = true);
                ```
                """
            ),
            mo.ui.table(totals, selection=None, pagination=False),
        ]
    )
    return


@app.cell(hide_code=True)
def duckdb_agg(mo, source):
    # Aggregate across every file at once: DuckDB does the group-by over the
    # whole glob, returning one row per family -- identical results no matter
    # which physical layout `source` points at.
    per_family = mo.sql(
        f"""
        SELECT
            family,
            COUNT(*)                      AS n,
            round(avg(mol_weight), 1)     AS avg_mw,
            round(avg(logp), 2)           AS avg_logp,
            round(avg(n_rotatable_bonds), 1) AS avg_rot_bonds,
            round(avg(n_heteroatoms), 1)  AS avg_heteroatoms
        FROM read_parquet('data/parquet/{source.value}/*.parquet')
        GROUP BY family
        ORDER BY n DESC, family
        """,
        output=False,
    )

    mo.vstack(
        [
            mo.md(
                f"""
                ## Aggregating across all files

                One `GROUP BY` over the glob summarises every family — counts and
                mean physicochemical properties — in milliseconds. These numbers
                are **identical** whether you read `by_family/` or `shuffled/`;
                right now: **`{source.value}`**.
                """
            ),
            mo.ui.table(per_family, selection=None, pagination=True, page_size=8),
        ]
    )
    return


@app.cell(hide_code=True)
def explore(mo):
    # Pull the full dataset into a marimo DataFrame so it can be browsed live.
    molecules = mo.sql(
        """
        SELECT id, family, name, formula, smiles,
               mol_weight, logp, n_rotatable_bonds, n_heteroatoms
        FROM read_parquet('data/parquet/by_family/*.parquet')
        ORDER BY family, name
        """,
        output=False,
    )

    mo.vstack(
        [
            mo.md(
                """
                ## Step 2 — Explore the data in marimo

                The whole dataset in an interactive table: **sort** any column,
                **search**, and **filter** — no code required.
                """
            ),
            mo.ui.table(molecules, selection=None, page_size=10),
        ]
    )
    return (molecules,)


@app.cell(hide_code=True)
def chart_bar(alt, mo, molecules):
    # A plain (static) Altair bar chart: molecules per family.
    _bar = (
        alt.Chart(molecules)
        .mark_bar(cornerRadiusEnd=3, color="#4c78a8")
        .encode(
            x=alt.X("count():Q", title="Molecules"),
            y=alt.Y("family:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("family:N"), alt.Tooltip("count():Q", title="Count")],
        )
        .properties(height=380, width=560, title="Molecules per family")
    )

    mo.vstack(
        [
            mo.md("## Step 3 — Chart the data"),
            mo.ui.altair_chart(_bar),
        ]
    )
    return


@app.cell(hide_code=True)
def chart_scatter(alt, mo, molecules):
    # A static scatter: molecular weight vs cLogP, coloured by family.
    _scatter = (
        alt.Chart(molecules)
        .mark_circle(size=90, opacity=0.8, stroke="white", strokeWidth=0.5)
        .encode(
            x=alt.X("mol_weight:Q", title="Molecular weight (Da)",
                    scale=alt.Scale(zero=False, nice=True)),
            y=alt.Y("logp:Q", title="cLogP",
                    scale=alt.Scale(zero=False, nice=True)),
            color=alt.Color("family:N", title="Family",
                            legend=alt.Legend(columns=2)),
            tooltip=["name:N", "family:N",
                     alt.Tooltip("mol_weight:Q", title="MW", format=".1f"),
                     alt.Tooltip("logp:Q", title="cLogP", format=".2f")],
        )
        .properties(height=400, width=560,
                    title="Property space: cLogP vs molecular weight")
    )

    mo.vstack(
        [
            mo.md("## Property space, at a glance"),
            mo.ui.altair_chart(_scatter),
        ]
    )
    return


@app.cell(hide_code=True)
def controls(mo, molecules):
    # Numeric columns offered on the axis pickers (label -> column name).
    _numeric = {
        "Molecular weight": "mol_weight",
        "cLogP": "logp",
        "Rotatable bonds": "n_rotatable_bonds",
        "Heteroatoms": "n_heteroatoms",
    }
    _families = ["All families"] + sorted(molecules["family"].unique().to_list())

    family = mo.ui.dropdown(options=_families, value="All families", label="Family")
    x_axis = mo.ui.dropdown(options=_numeric, value="Molecular weight", label="X axis")
    y_axis = mo.ui.dropdown(options=_numeric, value="cLogP", label="Y axis")
    chart_type = mo.ui.radio(
        options=["Scatter", "Histogram", "Bar (mean by family)"],
        value="Scatter",
        label="Chart type",
        inline=True,
    )

    mo.md(
        """
        ## Step 4 — The same chart, now interactive

        marimo is **reactive**: change a widget on the next slide and the chart
        below it rebuilds instantly — no callbacks, no re-run button.
        """
    )
    return chart_type, family, x_axis, y_axis


@app.cell(hide_code=True)
def live_chart(alt, chart_type, family, mo, molecules, x_axis, y_axis):
    # Filter to the chosen family, then build whichever chart the toggle selects.
    _df = molecules
    if family.value != "All families":
        _df = _df.filter(molecules["family"] == family.value)

    _x, _y = x_axis.value, y_axis.value
    _base = alt.Chart(_df)

    if chart_type.value == "Histogram":
        _chart = _base.mark_bar(color="#4c78a8").encode(
            x=alt.X(f"{_x}:Q", bin=alt.Bin(maxbins=25), title=x_axis.selected_key),
            y=alt.Y("count():Q", title="Count"),
            tooltip=[alt.Tooltip("count():Q", title="Count")],
        )
    elif chart_type.value == "Bar (mean by family)":
        _chart = _base.mark_bar(cornerRadiusEnd=3).encode(
            x=alt.X(f"mean({_y}):Q", title=f"Mean {y_axis.selected_key}"),
            y=alt.Y("family:N", sort="-x", title=None),
            color=alt.Color("family:N", legend=None),
            tooltip=["family:N", alt.Tooltip(f"mean({_y}):Q",
                                             title=f"Mean {y_axis.selected_key}",
                                             format=".2f")],
        )
    else:  # Scatter
        _chart = _base.mark_circle(
            size=110, opacity=0.8, stroke="white", strokeWidth=0.5
        ).encode(
            x=alt.X(f"{_x}:Q", title=x_axis.selected_key,
                    scale=alt.Scale(zero=False, nice=True)),
            y=alt.Y(f"{_y}:Q", title=y_axis.selected_key,
                    scale=alt.Scale(zero=False, nice=True)),
            color=alt.Color("family:N", title="Family", legend=alt.Legend(columns=2)),
            tooltip=["name:N", "family:N",
                     alt.Tooltip(f"{_x}:Q", title=x_axis.selected_key, format=".2f"),
                     alt.Tooltip(f"{_y}:Q", title=y_axis.selected_key, format=".2f")],
        )

    _chart = _chart.properties(
        height=380, width=560,
        title=f"{chart_type.value} — {family.value}",
    )

    mo.vstack(
        [
            mo.hstack(
                [family, x_axis, y_axis, chart_type],
                justify="start",
                gap=1.5,
                wrap=True,
            ),
            mo.ui.altair_chart(_chart),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

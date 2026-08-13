# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair==6.2.2",
#     "marimo",
#     "numpy==2.5.2",
#     "pandas==3.0.5",
#     "pyarrow==25.0.1",
# ]
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def imports():
    import marimo as mo
    import numpy as np
    import pandas as pd
    import altair as alt

    return alt, mo, np, pd


@app.cell
def intro(mo):
    mo.md("""
    # 🧪 Kicking the tires with marimo

    A quick tour of the three things that make marimo different:
    **reactivity** (a dataflow DAG), **`mo.ui` widgets**, and **live data**.

    Try dragging the sliders below — every cell that depends on them
    re-runs automatically. No "Run All", no stale state.
    """)
    return


@app.cell
def controls(mo):
    n_points = mo.ui.slider(
        10, 500, value=120, step=10, label="Number of points"
    )
    noise = mo.ui.slider(
        0.0, 2.0, value=0.4, step=0.1, label="Noise level (σ)"
    )
    mo.vstack(
        [
            mo.md("## 🎛️ Controls"),
            n_points,
            noise,
        ]
    )
    return n_points, noise


@app.cell
def data(n_points, noise, np, pd):
    rng = np.random.default_rng(0)
    x = np.linspace(0, 4 * np.pi, n_points.value)
    y = np.sin(x) + rng.normal(0, noise.value, size=n_points.value)
    df = pd.DataFrame({"x": x, "y": y})
    df
    return (df,)


@app.cell
def chart(alt, df, mo, n_points, noise):
    _base = (
        alt.Chart(df)
        .mark_circle(size=55, opacity=0.6)
        .encode(
            x="x",
            y="y",
            color=alt.Color(
                "y", scale=alt.Scale(scheme="viridis"), legend=None
            ),
        )
        .properties(
            height=320,
            title=f"sin(x) + noise  (n={n_points.value}, σ={noise.value})",
        )
    )
    mo.ui.altair_chart(_base)
    return


@app.cell
def section2(mo):
    mo.md("""
    ## 🎛️ Widgets driving a dataframe
    """)
    return


@app.cell
def dataset(np, pd):
    regions = ["North", "South", "East", "West"]
    _rng2 = np.random.default_rng(42)
    sales = pd.DataFrame(
        {
            "region": _rng2.choice(regions, 200),
            "product": _rng2.choice(
                ["Widget", "Gadget", "Gizmo", "Doohickey"], 200
            ),
            "units": _rng2.integers(1, 50, 200),
            "revenue": (_rng2.random(200) * 1000).round(2),
        }
    )
    sales
    return regions, sales


@app.cell
def picker(mo, regions):
    region_pick = mo.ui.dropdown(
        options=["All"] + regions, value="All", label="Filter by region"
    )
    region_pick
    return (region_pick,)


@app.cell
def table(mo, region_pick, sales):
    filtered = (
        sales
        if region_pick.value == "All"
        else sales[sales.region == region_pick.value]
    )
    mo.ui.table(filtered, selection="multi", page_size=8)
    return (filtered,)


@app.cell
def summary(filtered, mo):
    mo.md(f"""
    **{len(filtered)} rows** · total revenue **${filtered.revenue.sum():,.2f}** · avg units **{filtered.units.mean():.1f}**
    """)
    return


if __name__ == "__main__":
    app.run()

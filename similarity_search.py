# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb==1.5.4",
#     "polars",
#     "pyarrow",
#     "sqlglot==30.16.0",
#     "ipyketcher==0.1.0",
#     "anywidget==0.11.0",
#     "traitlets==5.16.1",
#     "altair==6.2.2",
#     "rdkit==2026.3.5",
#     "pandas==3.0.5",
# ]
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App(
    width="medium",
    layout_file="layouts/similarity_search.grid.json",
)


@app.cell
def _():
    import marimo as mo

    import duckdb
    import polars as pl
    from pathlib import Path

    import altair as alt
    import anywidget
    import base64
    import traitlets
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D

    return Chem, Path, alt, anywidget, base64, mo, pl, rdMolDraw2D, traitlets


@app.cell
def intro(mo):
    mo.md("""
    # Similarity search: sketch a query

    Draw a molecule in the **Ketcher** sketcher (defaults to **benzoic acid**);
    its SMILES is mirrored to Python as `query_smiles` and used to rank every
    molecule in the chosen Parquet subdir by **ECFP4 Tanimoto similarity**
    (precomputed `morgan_fp` + `ducksmiles.tanimoto_bit`). The slider sets the
    minimum similarity.
    """)
    return


@app.cell
def connect(mo):
    _df = mo.sql(
        f"""
        /*
        Self-installing so the notebook needs no manual setup. INSTALL caches the
        community build to ~/.duckdb -- a no-op once cached, persists across sandbox
        runs, and hits the network only on the first run. LOAD activates it on this
        (shared) connection.
        */
        INSTALL ducksmiles FROM community;
        LOAD ducksmiles;
        SELECT extension_name, loaded FROM duckdb_extensions() WHERE extension_name = 'ducksmiles';
        """
    )
    return


@app.cell
def subdir_select(mo):
    subdir = mo.ui.dropdown(
        options=["by_family", "shuffled"],
        value="by_family",
        label="Parquet subdir",
    )
    subdir
    return (subdir,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ### Sketcher setup

    The cell below serves the bundled **Ketcher** molecular editor
    (`./ketcher_standalone/`) over a tiny local static server on
    `http://127.0.0.1:2799` and embeds it in an iframe. Running Ketcher in its
    own top-level document avoids the shadow-DOM issues that break it when
    mounted as a native anywidget.

    The server runs in a **daemon thread inside this kernel** (not a
    subprocess), so it is torn down automatically when the kernel exits — there
    is nothing to clean up and no process can be orphaned. Re-running the cell
    reuses the already-running server (port-guarded). Launch marimo from the
    project root so `./ketcher_standalone/` resolves.

    Whatever you draw is mirrored to `query_smiles` and drives the similarity
    search below.
    """)
    return


@app.cell(hide_code=True)
def sketcher(Path, anywidget, mo, traitlets):
    import socket
    import threading
    import functools
    import http.server
    import socketserver

    # Serve the self-contained Ketcher standalone build and embed it in an iframe.
    # Ketcher runs in its own top-level document, which sidesteps the shadow-DOM
    # problems (CSS/MUI/ResizeObserver, dead canvas events) that broke mounting it
    # as a native anywidget. The build hardcodes the /KetcherDemoSA/ public path, so
    # it is served from ./ketcher_standalone/.
    #
    # The static file server runs in a DAEMON THREAD inside the marimo kernel (not a
    # subprocess). Daemon threads are torn down automatically when the kernel
    # process exits, so there is nothing to clean up and no server can be orphaned.
    _KETCHER_PORT = 2799
    _site_dir = Path("ketcher_standalone").resolve()

    def _port_is_open(_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _s:
            _s.settimeout(0.2)
            return _s.connect_ex(("127.0.0.1", _port)) == 0

    def _serve_ketcher():
        class _QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_args):  # keep the kernel console clean
                pass

        class _Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        _handler = functools.partial(_QuietHandler, directory=str(_site_dir))
        with _Server(("127.0.0.1", _KETCHER_PORT), _handler) as _httpd:
            _httpd.serve_forever()

    # Start once; the port guard keeps notebook re-runs from spawning duplicates.
    if not _port_is_open(_KETCHER_PORT):
        threading.Thread(target=_serve_ketcher, daemon=True).start()

    ketcher_url = f"http://127.0.0.1:{_KETCHER_PORT}/KetcherDemoSA/index.html"

    class KetcherEditor(anywidget.AnyWidget):
        """Ketcher molecular editor embedded via a same-machine iframe.

        The iframe posts the drawn structure's SMILES back to the page; we mirror it
        into the synced ``smiles`` trait so marimo reacts to whatever you sketch.
        """

        smiles = traitlets.Unicode("").tag(sync=True)
        initial = traitlets.Unicode("").tag(sync=True)
        src = traitlets.Unicode("").tag(sync=True)
        height = traitlets.Int(560).tag(sync=True)

        _esm = """
        function render({ model, el }) {
          const frame = document.createElement("iframe");
          frame.src = model.get("src");
          frame.style.width = "100%";
          frame.style.height = model.get("height") + "px";
          frame.style.border = "1px solid #ddd";
          frame.style.borderRadius = "6px";
          el.appendChild(frame);

          let seeded = false;
          function onMessage(ev) {
            if (ev.source !== frame.contentWindow) return;  // ignore other widgets
            const d = ev.data || {};
            if (d.type === "ketcher-ready") {
              const init = model.get("initial");
              if (init && !seeded) {
                seeded = true;
                frame.contentWindow.postMessage({ type: "ketcher-set", smiles: init }, "*");
              }
            } else if (d.type === "ketcher-smiles") {
              model.set("smiles", d.smiles || "");
              model.save_changes();
            }
          }
          window.addEventListener("message", onMessage);
          return () => window.removeEventListener("message", onMessage);
        }
        export default { render };
        """

    sketcher = mo.ui.anywidget(
        KetcherEditor(src=ketcher_url, initial="O=C(O)c1ccccc1", height=560)
    )
    sketcher
    return (sketcher,)


@app.cell
def _(sketcher):
    sketcher.value
    return


@app.cell
def load(mo, subdir):
    molecules = mo.sql(
        f"""
        SELECT id, family, name, smiles
        FROM read_parquet('data/parquet/{subdir.value}/*.parquet')
        ORDER BY family, name
        """
    )
    return (molecules,)


@app.cell
def pattern(mo, molecules, sketcher, subdir):
    # The sketched structure (defaults to benzoic acid) is the similarity query.
    query_smiles = sketcher.value.get("smiles") or "O=C(O)c1ccccc1"
    mo.md(
        f"Query (SMILES from sketcher): `{query_smiles}`  \n"
        f"Ranking **{len(molecules)}** molecules from **{subdir.value}** by ECFP4 Tanimoto."
    )
    return (query_smiles,)


@app.cell
def threshold(mo):
    threshold = mo.ui.slider(
        start=0.0,
        stop=1.0,
        step=0.05,
        value=0.4,
        label="Min Tanimoto",
        show_value=True,
    )
    threshold
    return (threshold,)


@app.cell
def search(mo, query_smiles, subdir, threshold):
    # Rank by ECFP4 Tanimoto vs the sketched query using the precached `morgan_fp` BLOB.
    hits = mo.sql(
        f"""
        WITH q AS (SELECT morgan_fp_bits('{query_smiles}') AS fp),
        scored AS (
            SELECT id, family, name, smiles,
                   round(tanimoto_bit(morgan_fp, q.fp), 3) AS tanimoto
            FROM read_parquet('data/parquet/{subdir.value}/*.parquet'), q
        )
        SELECT * FROM scored
        WHERE tanimoto >= {threshold.value}
        ORDER BY tanimoto DESC, family, name
        """
    )
    return (hits,)


@app.cell
def _(hits, mo):
    annotated_hits = mo.sql(
        f"""
        SELECT
            id,
            family,
            name,
            smiles,
            tanimoto,
            logp_crippen (smiles) as logp,
            mol_weight (smiles) as mw
        FROM
            hits;
        """
    )
    return (annotated_hits,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # App Components Below
    """)
    return


@app.cell
def _(annotated_hits, mo, molecules):
    mo.ui.tabs(
        tabs={"Source": molecules, "Hits": annotated_hits},
        value="Hits",
    )
    return


@app.cell(hide_code=True)
def _(Chem, alt, annotated_hits, base64, mo, pl, rdMolDraw2D):
    # Render each hit's SMILES to a crisp SVG and inline it as a base64 data URI.
    # vega-tooltip drops the value into an <img src>, which renders SVG data URIs.
    def _mol_svg_uri(_smiles, _size=210):
        _m = Chem.MolFromSmiles(_smiles)
        if _m is None:
            return ""
        _d = rdMolDraw2D.MolDraw2DSVG(_size, _size)
        rdMolDraw2D.PrepareAndDrawMolecule(_d, _m)
        _d.FinishDrawing()
        return (
            "data:image/svg+xml;base64,"
            + base64.b64encode(_d.GetDrawingText().encode()).decode()
        )

    # The tooltip column MUST be named "image" -- vega-tooltip only renders a data URI
    # as an <img> for that reserved field name (Altair tooltip-images case study).
    _plot_df = annotated_hits.with_columns(
        pl.Series(
            "image",
            [_mol_svg_uri(_s) for _s in annotated_hits["smiles"].to_list()],
        )
    )

    logp_mw_scatter = mo.ui.altair_chart(
        alt.Chart(_plot_df)
        .mark_circle(size=170, opacity=0.85, stroke="white", strokeWidth=0.6)
        .encode(
            x=alt.X(
                "mw:Q",
                title="Molecular weight (Da)",
                scale=alt.Scale(zero=False, nice=True),
            ),
            y=alt.Y(
                "logp:Q",
                title="cLogP (Crippen)",
                scale=alt.Scale(zero=False, nice=True),
            ),
            color=alt.Color(
                "tanimoto:Q",
                scale=alt.Scale(scheme="viridis"),
                title="Tanimoto",
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Name"),
                alt.Tooltip("family:N", title="Family"),
                alt.Tooltip("mw:Q", title="MW", format=".1f"),
                alt.Tooltip("logp:Q", title="cLogP", format=".2f"),
                alt.Tooltip("tanimoto:Q", title="Tanimoto", format=".3f"),
                "image:N",
            ],
        )
        .properties(
            height=400,
            width=500,
            title="Similarity hits: cLogP vs molecular weight",
        )
    )
    logp_mw_scatter
    return


@app.cell(hide_code=True)
def _(mo):
    mo.Html(
        """
        <div style="
            width:100%; height:100%;
            min-height:2px; min-width:2px;
            background:linear-gradient(90deg,#e6e6e6,#c9c9c9,#e6e6e6);
            border-radius:2px;
        "></div>
        """
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()

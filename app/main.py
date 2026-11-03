"""FastAPI application: dashboard, investigation lifecycle, JSON API."""

from __future__ import annotations

import os
import sys

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import filesearch
from .db import Store
from .models import confidence_label
from .scanner import run_investigation

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    """Writable directory: next to the executable when frozen (so data
    stays on the USB stick), otherwise a ./data folder in the project."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "data")
    return os.environ.get("OSINT_DATA_DIR",
                          os.path.join(os.path.dirname(BASE_DIR), "data"))


app = FastAPI(title="OSINT Verification Workbench", docs_url=None, redoc_url=None)
store = Store(data_dir())
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["confidence_label"] = confidence_label


def _fmt_ts(ts: float) -> str:
    import time
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(ts)))


templates.env.filters["ts"] = _fmt_ts
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")),
          name="static")

VALID_TYPES = {"email", "username", "name", "domain"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "investigations": store.list_investigations(),
    })


@app.post("/investigations")
async def start_investigation(background: BackgroundTasks,
                              input_type: str = Form(...),
                              input_value: str = Form(...)):
    input_type = input_type.strip().lower()
    input_value = input_value.strip()
    if input_type not in VALID_TYPES or not input_value:
        return RedirectResponse("/", status_code=303)
    inv_id = store.create_investigation(input_type, input_value)
    background.add_task(run_investigation, store, inv_id,
                        input_type, input_value)
    return RedirectResponse(f"/investigations/{inv_id}", status_code=303)


@app.get("/investigations/{inv_id}", response_class=HTMLResponse)
async def report(request: Request, inv_id: int):
    inv = store.get_investigation(inv_id)
    if not inv:
        return RedirectResponse("/", status_code=303)
    findings = store.get_findings(inv_id)
    links = store.get_links(inv_id)
    by_id = {f["id"]: f for f in findings}
    return templates.TemplateResponse("report.html", {
        "request": request,
        "inv": inv,
        "findings": findings,
        "links": links,
        "by_id": by_id,
    })


@app.get("/api/investigations/{inv_id}")
async def api_investigation(inv_id: int):
    inv = store.get_investigation(inv_id)
    if not inv:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "investigation": inv,
        "findings": store.get_findings(inv_id),
        "links": store.get_links(inv_id),
    }


@app.post("/investigations/{inv_id}/delete")
async def delete_investigation(inv_id: int):
    store.delete_investigation(inv_id)
    return RedirectResponse("/", status_code=303)


# ---------------- File Search tool ----------------

@app.get("/files", response_class=HTMLResponse)
async def file_search_page(request: Request, q: str = ""):
    results = filesearch.search(store.path, q) if q.strip() else None
    return templates.TemplateResponse("files.html", {
        "request": request,
        "q": q,
        "results": results,
        "indexed": filesearch.indexed_count(store.path),
        "status": filesearch.status(),
    })


@app.post("/files/index")
async def start_file_index(background: BackgroundTasks,
                           roots: str = Form(...),
                           with_content: str = Form("")):
    root_list = [r for r in roots.replace(";", "\n").splitlines() if r.strip()]
    if root_list and not filesearch.status()["running"]:
        background.add_task(filesearch.index_roots, store.path,
                            root_list, bool(with_content))
    return RedirectResponse("/files", status_code=303)


@app.get("/api/files/status")
async def file_index_status():
    st = filesearch.status()
    st["indexed_total"] = filesearch.indexed_count(store.path)
    return st


@app.post("/files/clear")
async def clear_file_index():
    filesearch.clear_index(store.path)
    return RedirectResponse("/files", status_code=303)

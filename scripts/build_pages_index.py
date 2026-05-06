#!/usr/bin/env python3
"""
Build a static GitHub Pages site that publishes both the framework
documentation (markdown files in docs/) and historical HTML reports
(in docs/reports/).

Output layout:
  _site/
    index.html        -- landing page: docs grid + report manifest
    latest.html       -- copy of the newest report
    .nojekyll         -- disable Jekyll so dot/underscore paths serve verbatim
    docs/
      <name>.html     -- rendered markdown docs (one per docs/*.md)
    reports/
      <run>.html      -- mirror of every HTML report

Usage:
    python scripts/build_pages_index.py
    python scripts/build_pages_index.py --reports-dir docs/reports --docs-dir docs --out _site
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    import markdown as markdown_lib  # type: ignore
except ImportError:  # pragma: no cover
    markdown_lib = None


REPO_ROOT = Path(__file__).resolve().parent.parent
TIMESTAMP_RE = re.compile(r"(\d{8}_\d{6})")


@dataclass
class ReportEntry:
    html_path: Path
    rel_path: Path
    folder: str
    filename: str
    timestamp: str
    mtime: float
    module: str
    total: int
    successful: int
    failed: int
    canary_leaks: int
    severity: str
    size_kb: int

    @property
    def href(self) -> str:
        return f"reports/{self.rel_path.as_posix()}"


@dataclass
class DocEntry:
    md_path: Path
    out_rel: Path     # path relative to _site, e.g. docs/prompt-injection.html
    title: str
    summary: str

    @property
    def href(self) -> str:
        return self.out_rel.as_posix()


def parse_timestamp(name: str, mtime: float) -> str:
    m = TIMESTAMP_RE.search(name)
    if m:
        raw = m.group(1)
        try:
            return dt.datetime.strptime(raw, "%Y%m%d_%H%M%S").strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            pass
    return dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")


def load_companion_json(html_path: Path) -> Optional[dict]:
    candidates = [
        html_path.with_suffix(".json"),
        html_path.parent / (html_path.stem + ".json"),
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            try:
                with cand.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
    return None


def summarize(data: Optional[dict]) -> tuple[str, int, int, int, int, str]:
    if not data:
        return "unknown", 0, 0, 0, 0, "unknown"

    module = "all"
    if isinstance(data.get("metadata"), dict):
        module = data["metadata"].get("module") or module

    total = 0
    successful = 0
    failed = 0
    canary_leaks = 0
    severities: List[str] = []

    results = data.get("results") or data.get("attacks") or []
    if isinstance(results, list):
        for entry in results:
            if not isinstance(entry, dict):
                continue
            mod_data = entry.get("data") if isinstance(entry.get("data"), dict) else entry
            summary = mod_data.get("summary") if isinstance(mod_data.get("summary"), dict) else None
            if summary:
                total += int(summary.get("total", 0) or 0)
                successful += int(summary.get("successful", 0) or 0)
                failed += int(summary.get("failed", 0) or 0)
            attacks = mod_data.get("attacks") if isinstance(mod_data.get("attacks"), list) else []
            for atk in attacks:
                if isinstance(atk, dict):
                    if atk.get("canary_leaked"):
                        canary_leaks += 1
                    sev = atk.get("severity")
                    if isinstance(atk.get("evaluation"), dict) and not sev:
                        sev = atk["evaluation"].get("severity")
                    if isinstance(sev, str):
                        severities.append(sev.lower())

    summary_top = data.get("summary") if isinstance(data.get("summary"), dict) else None
    if summary_top and total == 0:
        total = int(summary_top.get("total", 0) or 0)
        successful = int(summary_top.get("successful", 0) or 0)
        failed = int(summary_top.get("failed", 0) or 0)
    if summary_top and not canary_leaks:
        canary_leaks = int(summary_top.get("canary_leaks", 0) or 0)

    severity = "info"
    rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    if severities:
        severity = max(severities, key=lambda s: rank.get(s, 0))
    elif successful > 0:
        severity = "high"
    elif total > 0:
        severity = "low"

    return module, total, successful, failed, canary_leaks, severity


def collect_reports(reports_dir: Path) -> List[ReportEntry]:
    entries: List[ReportEntry] = []
    if not reports_dir.exists():
        return entries

    for path in sorted(reports_dir.rglob("*.html")):
        if not path.is_file():
            continue
        rel = path.relative_to(reports_dir)
        stat = path.stat()
        mtime = stat.st_mtime
        ts = parse_timestamp(path.name, mtime)
        data = load_companion_json(path)
        module, total, successful, failed, canary_leaks, severity = summarize(data)
        entries.append(
            ReportEntry(
                html_path=path,
                rel_path=rel,
                folder=str(rel.parent) if str(rel.parent) != "." else "(root)",
                filename=path.name,
                timestamp=ts,
                mtime=mtime,
                module=module,
                total=total,
                successful=successful,
                failed=failed,
                canary_leaks=canary_leaks,
                severity=severity,
                size_kb=max(1, stat.st_size // 1024),
            )
        )

    entries.sort(key=lambda e: e.mtime, reverse=True)
    return entries


def mirror_reports(entries: List[ReportEntry], out_dir: Path) -> None:
    dest_root = out_dir / "reports"
    dest_root.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        dst = dest_root / entry.rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.html_path, dst)


# ---------------------------------------------------------------------------
# Markdown docs rendering
# ---------------------------------------------------------------------------

DOC_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} -- LLM Red Team Docs</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background: #0d1117; color: #e6edf3; }}
  header {{ padding: 24px 40px 12px; border-bottom: 1px solid #30363d; }}
  header a {{ color: #58a6ff; text-decoration: none; font-size: 13px; }}
  header a:hover {{ text-decoration: underline; }}
  main {{ max-width: 880px; margin: 0 auto; padding: 32px 24px 80px; line-height: 1.6; }}
  main h1 {{ font-size: 28px; margin: 0 0 16px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
  main h2 {{ font-size: 22px; margin: 32px 0 12px; }}
  main h3 {{ font-size: 17px; margin: 24px 0 8px; color: #c9d1d9; }}
  main p, main li {{ font-size: 15px; }}
  main code {{ background: #161b22; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #f0883e; }}
  main pre {{ background: #161b22; padding: 14px 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; }}
  main pre code {{ background: transparent; padding: 0; color: #c9d1d9; }}
  main a {{ color: #58a6ff; }}
  main blockquote {{ border-left: 4px solid #30363d; margin: 12px 0; padding: 4px 16px; color: #8b949e; }}
  main table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  main th, main td {{ padding: 8px 12px; border: 1px solid #30363d; text-align: left; }}
  main th {{ background: #161b22; }}
</style>
</head>
<body>
<header>
  <a href="../index.html">&larr; Back to index</a>
</header>
<main>
{body}
</main>
</body>
</html>
"""


def render_markdown(md_text: str) -> str:
    """Render markdown -> HTML. Uses python-markdown if available, else a
    minimal fallback so the build never fails outright."""
    if markdown_lib is not None:
        return markdown_lib.markdown(
            md_text,
            extensions=["fenced_code", "tables", "toc", "sane_lists"],
            output_format="html5",
        )
    # Minimal fallback: wrap raw text in <pre> so it's still readable.
    return "<pre>" + html.escape(md_text) + "</pre>"


def extract_title_and_summary(md_text: str, fallback_title: str) -> tuple[str, str]:
    title = fallback_title
    summary = ""
    in_code = False
    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not title or title == fallback_title:
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                continue
        if stripped and not stripped.startswith("#") and not summary:
            summary = stripped
            if len(summary) > 200:
                summary = summary[:197] + "..."
        if title != fallback_title and summary:
            break
    return title, summary


def collect_and_render_docs(docs_dir: Path, reports_subdir: Path,
                            out_dir: Path) -> List[DocEntry]:
    entries: List[DocEntry] = []
    if not docs_dir.exists():
        return entries

    docs_out = out_dir / "docs"
    docs_out.mkdir(parents=True, exist_ok=True)

    for md_path in sorted(docs_dir.glob("*.md")):
        if not md_path.is_file():
            continue
        # Skip anything under the reports subdir
        try:
            md_path.relative_to(reports_subdir)
            continue
        except ValueError:
            pass

        text = md_path.read_text(encoding="utf-8")
        fallback = md_path.stem.replace("-", " ").replace("_", " ").title()
        title, summary = extract_title_and_summary(text, fallback)
        body = render_markdown(text)
        rendered = DOC_PAGE_TEMPLATE.format(title=html.escape(title), body=body)

        out_rel = Path("docs") / (md_path.stem + ".html")
        (out_dir / out_rel).write_text(rendered, encoding="utf-8")
        entries.append(DocEntry(
            md_path=md_path,
            out_rel=out_rel,
            title=title,
            summary=summary,
        ))

    # Also surface any image assets referenced by docs (e.g. docs/assets/*.png)
    assets_src = docs_dir / "assets"
    if assets_src.exists():
        assets_dst = out_dir / "docs" / "assets"
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)

    entries.sort(key=lambda d: d.title.lower())
    return entries


# ---------------------------------------------------------------------------
# Index rendering
# ---------------------------------------------------------------------------

SEVERITY_COLORS = {
    "critical": "#7e1d1d",
    "high": "#c0392b",
    "medium": "#d68910",
    "low": "#1e8449",
    "info": "#2874a6",
    "unknown": "#566573",
}


def render_index(reports: List[ReportEntry], docs: List[DocEntry],
                 out_dir: Path) -> None:
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    rows = []
    for e in reports:
        sev = html.escape(e.severity)
        color = SEVERITY_COLORS.get(e.severity, "#566573")
        canary_cell = (
            f"<td class='num canary'>{e.canary_leaks}</td>"
            if e.canary_leaks else
            "<td class='num'>0</td>"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(e.timestamp)}</td>"
            f"<td><code>{html.escape(e.folder)}</code></td>"
            f"<td>{html.escape(e.module)}</td>"
            f"<td class='num'>{e.total}</td>"
            f"<td class='num success'>{e.successful}</td>"
            f"<td class='num fail'>{e.failed}</td>"
            f"{canary_cell}"
            f"<td><span class='sev' style='background:{color}'>{sev}</span></td>"
            f"<td class='num'>{e.size_kb} KB</td>"
            f"<td><a href='{html.escape(e.href)}'>open &rarr;</a></td>"
            "</tr>"
        )

    if not rows:
        rows.append(
            "<tr><td colspan='10' style='text-align:center;color:#888;padding:32px'>"
            "No reports yet. Run a sweep with <code>python main.py --module all</code> "
            "to generate one.</td></tr>"
        )

    latest_link = ""
    if reports:
        latest_link = (
            "<a class='cta latest-btn' href='latest.html'>View latest report &rarr;</a>"
        )

    doc_cards = []
    for d in docs:
        doc_cards.append(
            "<a class='doc-card' href='" + html.escape(d.href) + "'>"
            f"<div class='doc-title'>{html.escape(d.title)}</div>"
            f"<div class='doc-summary'>{html.escape(d.summary or 'Open the page for details.')}</div>"
            "</a>"
        )

    docs_section = ""
    if doc_cards:
        docs_section = (
            "<section><h2>Documentation</h2>"
            "<p class='subtitle'>Module-by-module guides covering attack families, "
            "configuration, and interpretation of results.</p>"
            "<div class='doc-grid'>" + "".join(doc_cards) + "</div></section>"
        )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM Red Team Framework</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background: #0d1117; color: #e6edf3; }}
  header {{ padding: 32px 40px 16px; border-bottom: 1px solid #30363d; }}
  header h1 {{ margin: 0 0 8px; font-size: 28px; }}
  header p {{ margin: 4px 0; color: #8b949e; }}
  .container {{ padding: 24px 40px 64px; max-width: 1200px; margin: 0 auto; }}
  section {{ margin-top: 32px; }}
  section h2 {{ margin: 0 0 8px; font-size: 22px; border-bottom: 1px solid #30363d; padding-bottom: 6px; }}
  .subtitle {{ color: #8b949e; font-size: 13px; margin: 8px 0 16px; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 10px 14px; border-bottom: 1px solid #21262d; text-align: left; font-size: 14px; }}
  th {{ background: #21262d; color: #c9d1d9; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: .5px; }}
  tr:hover td {{ background: #1c2128; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.success {{ color: #f85149; font-weight: 600; }}
  td.fail {{ color: #3fb950; }}
  td.canary {{ color: #f85149; font-weight: 700; }}
  code {{ background: #21262d; padding: 2px 6px; border-radius: 4px; font-size: 12.5px; }}
  a {{ color: #58a6ff; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .sev {{ display: inline-block; padding: 2px 10px; border-radius: 12px; color: #fff; font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }}
  .cta {{ display: inline-block; margin-top: 12px; padding: 10px 18px; background: #238636; color: #fff !important; border-radius: 6px; font-weight: 600; }}
  .cta:hover {{ background: #2ea043; text-decoration: none; }}
  .doc-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }}
  .doc-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px 16px; color: #e6edf3 !important; }}
  .doc-card:hover {{ border-color: #58a6ff; text-decoration: none; }}
  .doc-title {{ font-size: 15px; font-weight: 600; margin-bottom: 4px; color: #58a6ff; }}
  .doc-summary {{ font-size: 12.5px; color: #8b949e; line-height: 1.4; }}
  footer {{ margin-top: 40px; color: #8b949e; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<header>
  <h1>LLM Red Team Framework</h1>
  <p>Adversarial LLM Red Teaming Framework -- documentation and historical reports.</p>
  <p>Index built: {html.escape(generated_at)} &middot; {len(reports)} report(s) &middot; {len(docs)} doc page(s)</p>
  {latest_link}
</header>
<div class="container">
{docs_section}
<section>
  <h2>Reports</h2>
  <p class='subtitle'>Every HTML report generated by the framework, newest first.
  The <strong>Canary</strong> column counts ground-truth system-prompt leaks.</p>
  <table>
    <thead>
      <tr>
        <th>Timestamp</th>
        <th>Run Folder</th>
        <th>Module</th>
        <th>Total</th>
        <th>Successful</th>
        <th>Failed</th>
        <th>Canary</th>
        <th>Severity</th>
        <th>Size</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</section>
  <footer>
    Generated by <code>scripts/build_pages_index.py</code>.
    For sweep instructions see the project README.
  </footer>
</div>
</body>
</html>
"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def write_latest(entries: List[ReportEntry], out_dir: Path) -> None:
    if not entries:
        return
    newest = entries[0]
    src = out_dir / "reports" / newest.rel_path
    dst = out_dir / "latest.html"
    if src.exists():
        shutil.copy2(src, dst)


def write_nojekyll(out_dir: Path) -> None:
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", default=str(REPO_ROOT / "docs" / "reports"))
    parser.add_argument("--docs-dir", default=str(REPO_ROOT / "docs"))
    parser.add_argument("--out", default=str(REPO_ROOT / "_site"))
    args = parser.parse_args(argv)

    reports_dir = Path(args.reports_dir).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    out_dir = Path(args.out).resolve()

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = collect_reports(reports_dir)
    mirror_reports(reports, out_dir)
    docs = collect_and_render_docs(docs_dir, reports_dir, out_dir)
    render_index(reports, docs, out_dir)
    write_latest(reports, out_dir)
    write_nojekyll(out_dir)

    print(f"[+] Built {out_dir}")
    print(f"    reports: {len(reports)}  docs: {len(docs)}")
    if reports:
        print(f"    latest:  {reports[0].rel_path} ({reports[0].timestamp})")
    if markdown_lib is None:
        print("[!] python-markdown not installed -- docs rendered in fallback <pre> mode.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

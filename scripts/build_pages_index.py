#!/usr/bin/env python3
"""
Build a static GitHub Pages site from the reports/ directory.

Walks reports/ for every *.html file, mirrors them into _site/reports/,
generates _site/index.html (manifest of all runs, newest first), copies
the most recent report to _site/latest.html, and drops a .nojekyll
marker so dot/underscore-prefixed files are served verbatim.

Usage:
    python scripts/build_pages_index.py [--reports-dir reports] [--out _site]
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
    severity: str
    size_kb: int

    @property
    def href(self) -> str:
        return f"reports/{self.rel_path.as_posix()}"


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


def summarize(data: Optional[dict]) -> tuple[str, int, int, int, str]:
    if not data:
        return "unknown", 0, 0, 0, "unknown"

    module = "all"
    if isinstance(data.get("metadata"), dict):
        module = data["metadata"].get("module") or module

    total = 0
    successful = 0
    failed = 0
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
                    sev = atk.get("severity") or atk.get("evaluation", {}).get("severity") if isinstance(atk.get("evaluation"), dict) else atk.get("severity")
                    if isinstance(sev, str):
                        severities.append(sev.lower())

    summary_top = data.get("summary") if isinstance(data.get("summary"), dict) else None
    if summary_top and total == 0:
        total = int(summary_top.get("total", 0) or 0)
        successful = int(summary_top.get("successful", 0) or 0)
        failed = int(summary_top.get("failed", 0) or 0)

    severity = "info"
    rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    if severities:
        severity = max(severities, key=lambda s: rank.get(s, 0))
    elif successful > 0:
        severity = "high"
    elif total > 0:
        severity = "low"

    return module, total, successful, failed, severity


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
        module, total, successful, failed, severity = summarize(data)
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
                severity=severity,
                size_kb=max(1, stat.st_size // 1024),
            )
        )

    entries.sort(key=lambda e: e.mtime, reverse=True)
    return entries


def mirror_reports(entries: List[ReportEntry], reports_dir: Path, out_dir: Path) -> None:
    dest_root = out_dir / "reports"
    dest_root.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        dst = dest_root / entry.rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.html_path, dst)


SEVERITY_COLORS = {
    "critical": "#7e1d1d",
    "high": "#c0392b",
    "medium": "#d68910",
    "low": "#1e8449",
    "info": "#2874a6",
    "unknown": "#566573",
}


def render_index(entries: List[ReportEntry], out_dir: Path) -> None:
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rows = []
    for e in entries:
        sev = html.escape(e.severity)
        color = SEVERITY_COLORS.get(e.severity, "#566573")
        rows.append(
            "<tr>"
            f"<td>{html.escape(e.timestamp)}</td>"
            f"<td><code>{html.escape(e.folder)}</code></td>"
            f"<td>{html.escape(e.module)}</td>"
            f"<td class='num'>{e.total}</td>"
            f"<td class='num success'>{e.successful}</td>"
            f"<td class='num fail'>{e.failed}</td>"
            f"<td><span class='sev' style='background:{color}'>{sev}</span></td>"
            f"<td class='num'>{e.size_kb} KB</td>"
            f"<td><a href='{html.escape(e.href)}'>open &rarr;</a></td>"
            "</tr>"
        )

    if not rows:
        rows.append(
            "<tr><td colspan='9' style='text-align:center;color:#888;padding:32px'>"
            "No reports yet. Run a sweep with <code>python main.py --module all</code> "
            "to generate one.</td></tr>"
        )

    latest_link = ""
    if entries:
        latest_link = (
            "<a class='latest-btn' href='latest.html'>View latest report &rarr;</a>"
        )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM Red Team Reports</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background: #0d1117; color: #e6edf3; }}
  header {{ padding: 32px 40px 16px; border-bottom: 1px solid #30363d; }}
  header h1 {{ margin: 0 0 8px; font-size: 28px; }}
  header p {{ margin: 4px 0; color: #8b949e; }}
  .container {{ padding: 24px 40px 64px; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 10px 14px; border-bottom: 1px solid #21262d; text-align: left; font-size: 14px; }}
  th {{ background: #21262d; color: #c9d1d9; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: .5px; }}
  tr:hover td {{ background: #1c2128; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.success {{ color: #f85149; font-weight: 600; }}
  td.fail {{ color: #3fb950; }}
  code {{ background: #21262d; padding: 2px 6px; border-radius: 4px; font-size: 12.5px; }}
  a {{ color: #58a6ff; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .sev {{ display: inline-block; padding: 2px 10px; border-radius: 12px; color: #fff; font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }}
  .latest-btn {{ display: inline-block; margin-top: 12px; padding: 10px 18px; background: #238636; color: #fff !important; border-radius: 6px; font-weight: 600; }}
  .latest-btn:hover {{ background: #2ea043; text-decoration: none; }}
  footer {{ margin-top: 40px; color: #8b949e; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<header>
  <h1>LLM Red Team Reports</h1>
  <p>Adversarial LLM Red Teaming Framework -- published via GitHub Pages.</p>
  <p>Index built: {html.escape(generated_at)} &middot; {len(entries)} report(s)</p>
  {latest_link}
</header>
<div class="container">
  <table>
    <thead>
      <tr>
        <th>Timestamp</th>
        <th>Run Folder</th>
        <th>Module</th>
        <th>Total</th>
        <th>Successful</th>
        <th>Failed</th>
        <th>Severity</th>
        <th>Size</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
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
    parser.add_argument("--reports-dir", default=str(REPO_ROOT / "reports"))
    parser.add_argument("--out", default=str(REPO_ROOT / "_site"))
    args = parser.parse_args(argv)

    reports_dir = Path(args.reports_dir).resolve()
    out_dir = Path(args.out).resolve()

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = collect_reports(reports_dir)
    mirror_reports(entries, reports_dir, out_dir)
    render_index(entries, out_dir)
    write_latest(entries, out_dir)
    write_nojekyll(out_dir)

    print(f"[+] Built {out_dir} with {len(entries)} report(s)")
    if entries:
        print(f"[+] Latest: {entries[0].rel_path} ({entries[0].timestamp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import html
import json
import logging
import os
import platform
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytest

from api_client.base_client import start_capture, stop_capture
from api_client.customers import CustomersAPI
from api_client.payment_intents import PaymentIntentsAPI
from api_client.refunds import RefundsAPI

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)

# ── Custom Report Data Collection ────────────────────────────────────
_test_results = []
_session_start_time = None

# Directory for xdist workers to write result files
_XDIST_DATA_DIR = Path("reports/.xdist_data")

MODULE_LABELS = {
    "test_customers": "Customers API",
    "test_payment_intents": "Payment Intents API",
    "test_negative_validation": "Negative Validation",
    "test_auth_headers": "Auth & Headers",
    "test_security": "Security",
    "test_cross_resource": "Cross-Resource Integration",
    "test_data_integrity": "Data Integrity & Contracts",
    "test_refunds": "Refunds API",
    "test_rate_limit_resilience": "Rate Limit & Resilience",
}


def _is_xdist_worker(config):
    """Check if running as an xdist worker."""
    return hasattr(config, "workerinput")


def _is_xdist_controller(config):
    """Check if running as xdist controller (not a worker but xdist is active)."""
    return config.pluginmanager.hasplugin("xdist") and not _is_xdist_worker(config)


def pytest_sessionstart(session):
    global _session_start_time
    _session_start_time = time.time()
    # Clean up previous xdist data
    if not _is_xdist_worker(session.config):
        if _XDIST_DATA_DIR.exists():
            for f in _XDIST_DATA_DIR.glob("*.json"):
                f.unlink()


def pytest_runtest_setup(item):
    """Start capturing API calls before each test."""
    start_capture()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        api_calls = stop_capture()
        module_file = item.module.__name__.split(".")[-1]
        class_name = item.cls.__name__ if item.cls else ""
        result = {
            "nodeid": item.nodeid,
            "module": module_file,
            "module_label": MODULE_LABELS.get(module_file, module_file),
            "class": class_name,
            "name": item.name,
            "status": report.outcome,
            "duration": round(report.duration, 3),
            "longrepr": str(report.longrepr) if report.longrepr else "",
            "api_calls": api_calls,
        }
        _test_results.append(result)

        # If running under xdist, also write to a file for aggregation
        if _is_xdist_worker(item.config):
            _XDIST_DATA_DIR.mkdir(parents=True, exist_ok=True)
            worker_id = item.config.workerinput["workerid"]
            # Use a unique filename per test
            safe_nodeid = item.nodeid.replace("/", "_").replace("::", "__")
            fpath = _XDIST_DATA_DIR / f"{worker_id}_{safe_nodeid}.json"
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(result, f)


# ── Reports directory (fresh-clone fix) ────────────────────────────
@pytest.fixture(autouse=True, scope="session")
def _ensure_reports_dir():
    os.makedirs("reports", exist_ok=True)


# ── API client fixtures ─────────────────────────────────────────────
@pytest.fixture(scope="session")
def customers_api():
    return CustomersAPI()


@pytest.fixture(scope="session")
def payments_api():
    return PaymentIntentsAPI()


@pytest.fixture(scope="session")
def refunds_api():
    return RefundsAPI()


# ── Cleanup registries ──────────────────────────────────────────────
@pytest.fixture(scope="session")
def created_customer_ids():
    """Collect customer IDs for teardown."""
    return []


@pytest.fixture(scope="session")
def created_payment_intent_ids():
    """Collect payment-intent IDs for teardown."""
    return []


@pytest.fixture(autouse=True, scope="session")
def cleanup_customers(customers_api, created_customer_ids):
    yield
    logger = logging.getLogger("cleanup")
    for cid in created_customer_ids:
        try:
            customers_api.delete_customer(cid)
        except Exception as exc:
            logger.warning("Failed to delete customer %s: %s", cid, exc)


@pytest.fixture(autouse=True, scope="session")
def cleanup_payment_intents(payments_api, created_payment_intent_ids):
    yield
    logger = logging.getLogger("cleanup")
    for pid in created_payment_intent_ids:
        try:
            pi = payments_api.retrieve(pid).json()
            if pi.get("status") in ("requires_payment_method", "requires_capture", "requires_confirmation"):
                payments_api.cancel(pid)
        except Exception as exc:
            logger.warning("Failed to cancel payment intent %s: %s", pid, exc)


# ── Custom HTML Report Generation & Auto-open ────────────────────
def _generate_custom_report(results=None):
    """Generate a module-wise HTML report with summary dashboard."""
    global _session_start_time
    total_duration = round(time.time() - (_session_start_time or time.time()), 2)
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    if results is None:
        results = _test_results

    # Aggregate stats
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errored = sum(1 for r in results if r["status"] not in ("passed", "failed", "skipped"))
    pass_rate = round((passed / total * 100), 1) if total else 0

    # Module-wise grouping
    modules = defaultdict(list)
    for r in results:
        modules[r["module_label"]].append(r)

    # Compute module stats
    module_stats = {}
    for label, tests in modules.items():
        module_stats[label] = {
            "total": len(tests),
            "passed": sum(1 for t in tests if t["status"] == "passed"),
            "failed": sum(1 for t in tests if t["status"] == "failed"),
            "skipped": sum(1 for t in tests if t["status"] == "skipped"),
            "duration": round(sum(t["duration"] for t in tests), 2),
        }

    # Module order
    module_order = [
        "Customers API", "Payment Intents API", "Refunds API",
        "Security", "Cross-Resource Integration", "Data Integrity & Contracts",
        "Rate Limit & Resilience", "Negative Validation", "Auth & Headers",
    ]
    ordered_modules = [m for m in module_order if m in modules]
    ordered_modules += [m for m in modules if m not in module_order]

    # Format duration
    mins, secs = divmod(int(total_duration), 60)
    duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"

    # CSS conic-gradient for donut
    pass_deg = round(passed / total * 360) if total else 0
    fail_deg = round(failed / total * 360) if total else 0
    skip_deg = round(skipped / total * 360) if total else 0
    err_deg = 360 - pass_deg - fail_deg - skip_deg

    # Build module summary cards
    cards_html = ""
    for label in ordered_modules:
        s = module_stats[label]
        rate = round(s["passed"] / s["total"] * 100, 1) if s["total"] else 0
        bar_pass_pct = round(s["passed"] / s["total"] * 100) if s["total"] else 0
        bar_fail_pct = round(s["failed"] / s["total"] * 100) if s["total"] else 0
        bar_skip_pct = 100 - bar_pass_pct - bar_fail_pct

        status_class = "card-pass" if s["failed"] == 0 else "card-fail"

        cards_html += f"""
        <div class="module-card {status_class}">
          <div class="card-header">
            <h3>{html.escape(label)}</h3>
            <span class="card-badge {'badge-pass' if s['failed'] == 0 else 'badge-fail'}">{rate}%</span>
          </div>
          <div class="card-stats">
            <span class="stat-item passed-text"><span class="stat-dot" style="background:var(--green)"></span> {s['passed']} passed</span>
            <span class="stat-item failed-text"><span class="stat-dot" style="background:var(--red)"></span> {s['failed']} failed</span>
            <span class="stat-item skipped-text"><span class="stat-dot" style="background:var(--orange)"></span> {s['skipped']} skipped</span>
            <span class="stat-item"><span class="stat-dot" style="background:var(--blue)"></span> {s['duration']}s</span>
          </div>
          <div class="progress-bar">
            <div class="bar-pass" style="width:{bar_pass_pct}%"></div>
            <div class="bar-fail" style="width:{bar_fail_pct}%"></div>
            <div class="bar-skip" style="width:{bar_skip_pct}%"></div>
          </div>
        </div>"""

    # Build detailed test tables per module
    test_counter = 0
    details_html = ""
    for label in ordered_modules:
        tests = modules[label]
        s = module_stats[label]

        # Group tests by class
        classes = defaultdict(list)
        for t in tests:
            classes[t["class"] or "Standalone"].append(t)

        rows_html = ""
        for cls_name, cls_tests in classes.items():
            rows_html += f"""
            <tr class="class-header-row">
              <td colspan="4" class="class-header">{html.escape(cls_name)}</td>
            </tr>"""
            for t in cls_tests:
                test_counter += 1
                tid = f"test-detail-{test_counter}"
                status_cls = t["status"]
                api_calls = t.get("api_calls", [])
                has_details = bool(api_calls or t["longrepr"])

                # Build API calls + error detail panel
                detail_content = ""
                if api_calls:
                    for idx, call in enumerate(api_calls, 1):
                        status_class = "api-status-ok" if call["status_code"] < 400 else "api-status-err"
                        req_payload = ""
                        if call["request_payload"]:
                            try:
                                req_payload = json.dumps(call["request_payload"], indent=2)
                            except Exception:
                                req_payload = str(call["request_payload"])
                        resp_body = call["response_body"] or ""
                        # Truncate very long responses for readability
                        if len(resp_body) > 3000:
                            resp_body = resp_body[:3000] + "\n... (truncated)"
                        detail_content += f"""
                        <div class="api-call">
                          <div class="api-call-header">
                            <span class="api-method api-method-{call['method'].lower()}">{call['method']}</span>
                            <span class="api-url">{html.escape(call['url'])}</span>
                            <span class="api-status {status_class}">{call['status_code']}</span>
                            <span class="api-time">{call['response_time']}s</span>
                          </div>
                          <div class="api-panels">
                            <div class="api-panel">
                              <div class="api-panel-label">Request{' Payload' if req_payload else ''}</div>
                              <pre class="api-code">{html.escape(req_payload) if req_payload else '<span class="api-empty">No request body</span>'}</pre>
                            </div>
                            <div class="api-panel">
                              <div class="api-panel-label">Response</div>
                              <pre class="api-code">{html.escape(resp_body)}</pre>
                            </div>
                          </div>
                        </div>"""
                if t["longrepr"]:
                    detail_content += f"""
                        <div class="error-section">
                          <div class="api-panel-label error-label">Error Traceback</div>
                          <pre class="error-detail">{html.escape(t['longrepr'])}</pre>
                        </div>"""

                toggle_btn = f'<button class="toggle-btn" onclick="toggleDetail(\'{tid}\', this)">Details</button>' if has_details else ''

                api_count_badge = f'<span class="api-count-badge">{len(api_calls)} call{"s" if len(api_calls) != 1 else ""}</span>' if api_calls else ''

                rows_html += f"""
            <tr class="test-row {status_cls}">
              <td class="test-name">{html.escape(t['name'])} {api_count_badge}</td>
              <td class="test-status"><span class="status-badge status-{status_cls}">{status_cls.upper()}</span></td>
              <td class="test-duration">{t['duration']}s</td>
              <td class="test-toggle">{toggle_btn}</td>
            </tr>"""
                if has_details:
                    rows_html += f"""
            <tr class="detail-row hidden" id="{tid}">
              <td colspan="4" class="detail-cell">
                {detail_content}
              </td>
            </tr>"""

        details_html += f"""
      <div class="module-section collapsed">
        <div class="section-header" onclick="this.parentElement.classList.toggle('collapsed')">
          <h2>{html.escape(label)}</h2>
          <div class="section-summary">
            <span class="summary-pill pill-pass">{s['passed']} passed</span>
            <span class="summary-pill pill-fail">{s['failed']} failed</span>
            <span class="summary-pill pill-skip">{s['skipped']} skipped</span>
            <span class="summary-pill pill-time">{s['duration']}s</span>
            <span class="chevron">&#9660;</span>
          </div>
        </div>
        <div class="section-body">
          <table class="results-table">
            <thead>
              <tr>
                <th style="width:50%">Test Name</th>
                <th style="width:15%">Status</th>
                <th style="width:15%">Duration</th>
                <th style="width:20%"></th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
      </div>"""

    # Overall status
    overall_status = "ALL PASSED" if failed == 0 and errored == 0 else "FAILURES DETECTED"
    overall_class = "overall-pass" if failed == 0 and errored == 0 else "overall-fail"

    # Determine donut color
    donut_pct_color = "var(--green)" if failed == 0 else "var(--red)"

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QA Test Report | PrudentAI Assessment</title>
  <style>
    :root {{
      --bg: #f0f2f5;
      --card-bg: #ffffff;
      --text: #1a1a2e;
      --text-secondary: #4a5568;
      --text-muted: #718096;
      --border: #e2e8f0;
      --green: #059669;
      --green-light: #d1fae5;
      --red: #dc2626;
      --red-light: #fee2e2;
      --orange: #d97706;
      --orange-light: #fef3c7;
      --blue: #2563eb;
      --blue-light: #dbeafe;
      --purple: #7c3aed;
      --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
      --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
      --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
      --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
      --radius: 16px;
      --radius-sm: 10px;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }}

    .report-header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #334155 100%);
      color: white;
      padding: 48px 0;
      position: relative;
      overflow: hidden;
    }}
    .report-header::before {{
      content: '';
      position: absolute;
      top: -50%;
      right: -10%;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
      border-radius: 50%;
    }}
    .header-inner {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 32px;
      position: relative;
      z-index: 1;
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .report-header h1 {{
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.5px;
      margin-bottom: 6px;
    }}
    .report-header .subtitle {{
      color: rgba(255,255,255,0.6);
      font-size: 15px;
      font-weight: 400;
    }}
    .header-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 20px;
      border-radius: 50px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.5px;
      margin-top: 8px;
    }}
    .header-badge.pass {{
      background: rgba(16,185,129,0.2);
      color: #6ee7b7;
      border: 1px solid rgba(16,185,129,0.3);
    }}
    .header-badge.fail {{
      background: rgba(239,68,68,0.2);
      color: #fca5a5;
      border: 1px solid rgba(239,68,68,0.3);
    }}
    .header-badge .dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
    }}
    .header-meta {{
      display: flex;
      gap: 32px;
      margin-top: 24px;
      padding-top: 20px;
      border-top: 1px solid rgba(255,255,255,0.1);
    }}
    .meta-item {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .meta-item .meta-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: rgba(255,255,255,0.4);
      font-weight: 600;
    }}
    .meta-item .meta-value {{
      font-size: 14px;
      color: rgba(255,255,255,0.85);
      font-weight: 500;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px;
    }}

    .summary-section {{
      display: flex;
      gap: 24px;
      margin-bottom: 36px;
      margin-top: -40px;
      position: relative;
      z-index: 2;
    }}
    .donut-card {{
      flex: 0 0 240px;
      background: var(--card-bg);
      border-radius: var(--radius);
      box-shadow: var(--shadow-md);
      padding: 32px 28px 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }}
    .donut-wrapper {{
      width: 170px;
      height: 170px;
      position: relative;
    }}
    .donut {{
      width: 170px;
      height: 170px;
      border-radius: 50%;
      background: conic-gradient(
        var(--green) 0deg {pass_deg}deg,
        var(--red) {pass_deg}deg {pass_deg + fail_deg}deg,
        var(--orange) {pass_deg + fail_deg}deg {pass_deg + fail_deg + skip_deg}deg,
        #cbd5e1 {pass_deg + fail_deg + skip_deg}deg 360deg
      );
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .donut-hole {{
      width: 130px;
      height: 130px;
      background: var(--card-bg);
      border-radius: 50%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 0 8px rgba(0,0,0,0.04);
    }}
    .donut-hole .pct {{
      font-size: 26px;
      font-weight: 800;
      color: {donut_pct_color};
      line-height: 1;
    }}
    .donut-hole .pct-label {{
      font-size: 9px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-top: 4px;
      font-weight: 600;
    }}
    .donut-legend {{
      display: flex;
      gap: 16px;
      margin-top: 20px;
      font-size: 11px;
      color: var(--text-muted);
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 4px;
    }}
    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }}
    .legend-dot.green {{ background: var(--green); }}
    .legend-dot.red {{ background: var(--red); }}
    .legend-dot.orange {{ background: var(--orange); }}

    .stats-grid {{
      flex: 1;
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 16px;
    }}
    .stat-card {{
      background: var(--card-bg);
      border-radius: var(--radius);
      box-shadow: var(--shadow-md);
      padding: 24px 16px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}
    .stat-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
    }}
    .stat-card.total::before {{ background: var(--blue); }}
    .stat-card.pass::before {{ background: var(--green); }}
    .stat-card.fail::before {{ background: var(--red); }}
    .stat-card.skip::before {{ background: var(--orange); }}
    .stat-card.time::before {{ background: var(--purple); }}
    .stat-card .stat-icon {{
      font-size: 24px;
      margin-bottom: 8px;
      display: block;
    }}
    .stat-card .stat-number {{
      font-size: 32px;
      font-weight: 800;
      line-height: 1;
    }}
    .stat-card .stat-label {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-top: 6px;
      font-weight: 600;
    }}
    .stat-card.total .stat-number {{ color: var(--blue); }}
    .stat-card.pass .stat-number {{ color: var(--green); }}
    .stat-card.fail .stat-number {{ color: var(--red); }}
    .stat-card.skip .stat-number {{ color: var(--orange); }}
    .stat-card.time .stat-number {{ color: var(--purple); font-size: 24px; }}

    .section-title {{
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 16px;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .section-title::before {{
      content: '';
      width: 4px;
      height: 20px;
      background: var(--blue);
      border-radius: 2px;
    }}

    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 40px;
    }}
    .module-card {{
      background: var(--card-bg);
      border-radius: var(--radius);
      padding: 24px;
      box-shadow: var(--shadow);
      border-top: 4px solid var(--green);
      transition: all 0.2s ease;
      position: relative;
    }}
    .module-card:hover {{
      box-shadow: var(--shadow-lg);
      transform: translateY(-2px);
    }}
    .module-card.card-fail {{ border-top-color: var(--red); }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }}
    .card-header h3 {{
      font-size: 14px;
      font-weight: 700;
      color: var(--text);
      line-height: 1.3;
    }}
    .card-badge {{
      font-size: 12px;
      font-weight: 800;
      padding: 4px 12px;
      border-radius: 50px;
      white-space: nowrap;
    }}
    .badge-pass {{ background: var(--green-light); color: var(--green); }}
    .badge-fail {{ background: var(--red-light); color: var(--red); }}
    .card-stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 12px;
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 14px;
    }}
    .stat-item {{
      display: flex;
      align-items: center;
      gap: 4px;
    }}
    .stat-item .stat-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .passed-text {{ color: var(--green); font-weight: 600; }}
    .failed-text {{ color: var(--red); font-weight: 600; }}
    .skipped-text {{ color: var(--orange); font-weight: 600; }}
    .progress-bar {{
      height: 8px;
      border-radius: 4px;
      background: var(--bg);
      display: flex;
      overflow: hidden;
    }}
    .bar-pass {{ background: var(--green); border-radius: 4px 0 0 4px; }}
    .bar-fail {{ background: var(--red); }}
    .bar-skip {{ background: var(--orange); border-radius: 0 4px 4px 0; }}

    .module-section {{
      background: var(--card-bg);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      margin-bottom: 16px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 18px 28px;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s;
    }}
    .section-header:hover {{ background: #f8fafc; }}
    .section-header h2 {{
      font-size: 16px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .section-summary {{
      display: flex;
      gap: 16px;
      font-size: 13px;
      color: var(--text-muted);
      align-items: center;
    }}
    .summary-pill {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 10px;
      border-radius: 50px;
      font-size: 12px;
      font-weight: 600;
    }}
    .pill-pass {{ background: var(--green-light); color: var(--green); }}
    .pill-fail {{ background: var(--red-light); color: var(--red); }}
    .pill-skip {{ background: var(--orange-light); color: var(--orange); }}
    .pill-time {{ background: var(--blue-light); color: var(--blue); }}
    .chevron {{
      transition: transform 0.25s ease;
      font-size: 14px;
      color: var(--text-muted);
      margin-left: 8px;
    }}
    .module-section.collapsed .section-body {{ display: none; }}
    .module-section.collapsed .chevron {{ transform: rotate(-90deg); }}

    .section-body {{ padding: 0; }}
    .results-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .results-table th {{
      text-align: left;
      padding: 12px 28px;
      background: #f8fafc;
      color: var(--text-muted);
      font-weight: 700;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      border-bottom: 2px solid var(--border);
    }}
    .results-table td {{
      padding: 12px 28px;
      border-bottom: 1px solid #f1f5f9;
    }}
    .class-header-row td {{
      background: linear-gradient(90deg, #f0f4ff 0%, #f8fafc 100%);
      font-weight: 700;
      font-size: 13px;
      color: var(--blue);
      padding: 10px 28px;
      border-bottom: 1px solid var(--border);
    }}
    .class-header {{
      border-left: 3px solid var(--blue);
      padding-left: 25px !important;
    }}
    .test-row {{ transition: background 0.1s; }}
    .test-row:hover {{ background: #f8fafc; }}
    .test-name {{
      font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Monaco, monospace;
      font-size: 12.5px;
      color: var(--text-secondary);
    }}
    .test-duration {{
      color: var(--text-muted);
      font-size: 12px;
      font-family: 'SF Mono', 'Fira Code', monospace;
    }}
    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 12px;
      border-radius: 50px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }}
    .status-passed {{ background: var(--green-light); color: var(--green); }}
    .status-failed {{ background: var(--red-light); color: var(--red); }}
    .status-skipped {{ background: var(--orange-light); color: var(--orange); }}
    .toggle-btn {{
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 4px 12px;
      font-size: 11px;
      cursor: pointer;
      color: var(--text-muted);
      font-weight: 600;
      transition: all 0.15s;
    }}
    .toggle-btn:hover {{
      background: var(--blue-light);
      color: var(--blue);
      border-color: var(--blue);
    }}
    .error-detail {{
      background: #0f172a;
      color: #e2e8f0;
      padding: 20px;
      border-radius: var(--radius-sm);
      font-size: 12px;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: 'SF Mono', 'Fira Code', Monaco, monospace;
      max-height: 400px;
      overflow-y: auto;
      line-height: 1.7;
      border: 1px solid #1e293b;
    }}
    .hidden {{ display: none !important; }}

    .detail-row td {{ padding: 0; }}
    .detail-cell {{
      padding: 12px 28px 20px !important;
      background: #f8fafc;
      border-top: none !important;
    }}
    .api-call {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      margin-bottom: 10px;
      overflow: hidden;
    }}
    .api-call:last-child {{ margin-bottom: 0; }}
    .api-call-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 16px;
      background: #f1f5f9;
      border-bottom: 1px solid var(--border);
      font-size: 12px;
    }}
    .api-method {{
      display: inline-block;
      padding: 2px 10px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.5px;
      color: white;
      font-family: 'SF Mono', 'Fira Code', monospace;
    }}
    .api-method-get {{ background: var(--blue); }}
    .api-method-post {{ background: var(--green); }}
    .api-method-delete {{ background: var(--red); }}
    .api-method-put {{ background: var(--orange); }}
    .api-method-patch {{ background: var(--purple); }}
    .api-url {{
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 12px;
      color: var(--text-secondary);
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .api-status {{
      font-weight: 800;
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 4px;
    }}
    .api-status-ok {{ background: var(--green-light); color: var(--green); }}
    .api-status-err {{ background: var(--red-light); color: var(--red); }}
    .api-time {{
      color: var(--text-muted);
      font-size: 11px;
      font-family: 'SF Mono', 'Fira Code', monospace;
    }}
    .api-panels {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0;
    }}
    .api-panel {{
      padding: 0;
      border-right: 1px solid var(--border);
    }}
    .api-panel:last-child {{ border-right: none; }}
    .api-panel-label {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-muted);
      padding: 8px 14px 4px;
      background: #fafbfc;
    }}
    .api-code {{
      font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Monaco, monospace;
      font-size: 11px;
      line-height: 1.6;
      padding: 8px 14px 12px;
      margin: 0;
      color: var(--text-secondary);
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 280px;
      overflow-y: auto;
      background: var(--card-bg);
    }}
    .api-empty {{ color: var(--text-muted); font-style: italic; }}
    .api-count-badge {{
      display: inline-block;
      background: var(--blue-light);
      color: var(--blue);
      font-size: 10px;
      font-weight: 700;
      padding: 1px 8px;
      border-radius: 50px;
      margin-left: 8px;
      vertical-align: middle;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .error-section {{
      margin-top: 10px;
    }}
    .error-label {{
      color: var(--red) !important;
      padding: 8px 14px 4px;
    }}

    .toggle-btn.active {{
      background: var(--blue-light);
      color: var(--blue);
      border-color: var(--blue);
    }}

    .report-footer {{
      text-align: center;
      padding: 32px;
      color: var(--text-muted);
      font-size: 12px;
      margin-top: 16px;
    }}
    .report-footer .footer-line {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }}
    .footer-divider {{
      width: 60px;
      height: 1px;
      background: var(--border);
    }}

    @media (max-width: 1024px) {{
      .cards-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .stats-grid {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    @media (max-width: 768px) {{
      .summary-section {{ flex-direction: column; margin-top: -24px; }}
      .donut-card {{ flex: none; }}
      .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .cards-grid {{ grid-template-columns: 1fr; }}
      .report-header {{ padding: 32px 0; }}
      .container {{ padding: 16px; }}
      .header-meta {{ flex-wrap: wrap; gap: 16px; }}
    }}
  </style>
</head>
<body>

  <div class="report-header">
    <div class="header-inner">
      <div class="header-top">
        <div>
          <h1>QA Test Report</h1>
          <p class="subtitle">Stripe API Integration Tests &mdash; PrudentAI Assessment</p>
        </div>
        <div class="header-badge {'pass' if failed == 0 else 'fail'}">
          <span class="dot"></span>
          {overall_status}
        </div>
      </div>
      <div class="header-meta">
        <div class="meta-item">
          <span class="meta-label">Generated</span>
          <span class="meta-value">{now}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Duration</span>
          <span class="meta-value">{duration_str}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Platform</span>
          <span class="meta-value">{platform.system()} / Python {platform.python_version()}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Tests</span>
          <span class="meta-value">{total} total across {len(ordered_modules)} modules</span>
        </div>
      </div>
    </div>
  </div>

  <div class="container">

    <div class="summary-section">
      <div class="donut-card">
        <div class="donut-wrapper">
          <div class="donut">
            <div class="donut-hole">
              <span class="pct">{pass_rate}%</span>
              <span class="pct-label">Pass Rate</span>
            </div>
          </div>
        </div>
        <div class="donut-legend">
          <span class="legend-item"><span class="legend-dot green"></span> Pass</span>
          <span class="legend-item"><span class="legend-dot red"></span> Fail</span>
          <span class="legend-item"><span class="legend-dot orange"></span> Skip</span>
        </div>
      </div>
      <div class="stats-grid">
        <div class="stat-card total">
          <span class="stat-icon">&#128202;</span>
          <div class="stat-number">{total}</div>
          <div class="stat-label">Total Tests</div>
        </div>
        <div class="stat-card pass">
          <span class="stat-icon">&#9989;</span>
          <div class="stat-number">{passed}</div>
          <div class="stat-label">Passed</div>
        </div>
        <div class="stat-card fail">
          <span class="stat-icon">&#10060;</span>
          <div class="stat-number">{failed}</div>
          <div class="stat-label">Failed</div>
        </div>
        <div class="stat-card skip">
          <span class="stat-icon">&#9888;&#65039;</span>
          <div class="stat-number">{skipped}</div>
          <div class="stat-label">Skipped</div>
        </div>
        <div class="stat-card time">
          <span class="stat-icon">&#9201;</span>
          <div class="stat-number">{duration_str}</div>
          <div class="stat-label">Duration</div>
        </div>
      </div>
    </div>

    <h2 class="section-title">Module Summary</h2>
    <div class="cards-grid">
      {cards_html}
    </div>

    <h2 class="section-title">Detailed Results</h2>
    {details_html}

    <div class="report-footer">
      <div class="footer-line">
        <span class="footer-divider"></span>
        <span>Generated by Custom Pytest Reporter</span>
        <span>&middot;</span>
        <span>PrudentAI QA Assessment</span>
        <span class="footer-divider"></span>
      </div>
    </div>
  </div>

  <script>
    function toggleDetail(id, btn) {{
      var row = document.getElementById(id);
      if (!row) return;
      var isHidden = row.classList.contains('hidden');
      row.classList.toggle('hidden');
      if (btn) {{
        btn.classList.toggle('active', isHidden);
        btn.textContent = isHidden ? 'Hide' : 'Details';
      }}
    }}
  </script>

</body>
</html>"""

    os.makedirs("reports", exist_ok=True)
    report_path = os.path.abspath("reports/custom_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_html)
    return report_path


def pytest_sessionfinish(session, exitstatus):
    """Generate custom report and open it in browser."""
    # If running under xdist, only the controller generates the report
    if _is_xdist_worker(session.config):
        return

    # Aggregate results from xdist workers if applicable
    all_results = list(_test_results)
    if _XDIST_DATA_DIR.exists():
        for fpath in sorted(_XDIST_DATA_DIR.glob("*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    all_results.append(json.load(f))
            except Exception:
                pass

    # Deduplicate by nodeid (prefer worker results if both exist)
    seen = {}
    for r in all_results:
        seen[r["nodeid"]] = r
    final_results = list(seen.values())

    if not final_results:
        return

    report_path = _generate_custom_report(final_results)

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", report_path])
        elif system == "Windows":
            os.startfile(report_path)
        else:
            subprocess.Popen(["xdg-open", report_path])
    except Exception:
        pass

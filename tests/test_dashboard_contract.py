from __future__ import annotations

import re
from pathlib import Path


def test_every_dashboard_navigation_target_exists() -> None:
    html = (Path(__file__).parents[1] / "apps" / "web" / "index.html").read_text(encoding="utf-8")
    targets = set(re.findall(r'data-page="([^"]+)"', html))
    sections = set(re.findall(r'<section id="([^"]+)" class="page', html))
    assert targets
    assert targets <= sections


def test_inline_button_handlers_have_implemented_functions() -> None:
    html = (Path(__file__).parents[1] / "apps" / "web" / "index.html").read_text(encoding="utf-8")
    script = html[html.rfind("<script"):]
    functions = set(re.findall(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', script))
    handlers = set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\s*\(', html))
    assert handlers
    assert handlers <= functions


def test_new_evaluation_and_settings_controls_are_wired() -> None:
    html = (Path(__file__).parents[1] / "apps" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'onclick="openPage(\'evaluations\')"' in html
    assert "function openPage(page)" in html
    assert "function checkApiHealth()" in html
    assert "function savePreferences()" in html
    assert "function submitBrowserRun()" in html
    assert "function resetSuiteExample()" in html

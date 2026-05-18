from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from loguru import logger
from playwright.sync_api import sync_playwright

@dataclass
class PageSnapshot:
    url: str
    html: str
    text: str
    title: str

class BrowserSession:
    def __init__(self, headless: bool = True, timeout_ms: int = 45000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    def snapshot(self, url: str) -> PageSnapshot:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={'width': 1440, 'height': 2200},
                locale='en-IN',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            )
            page = context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=self.timeout_ms)
            try:
                page.wait_for_load_state('networkidle', timeout=12000)
            except Exception:
                pass
            html = page.content()
            try:
                text = page.locator('body').inner_text(timeout=10000)
            except Exception:
                text = ''
            title = page.title() or ''
            browser.close()
            return PageSnapshot(url=url, html=html, text=text, title=title)

    def click_text(self, url: str, keywords: Iterable[str]) -> PageSnapshot:
        kws = [k.lower() for k in keywords]
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(viewport={'width': 1440, 'height': 2200}, locale='en-IN')
            page = context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=self.timeout_ms)
            try:
                page.wait_for_load_state('networkidle', timeout=12000)
            except Exception:
                pass
            anchors = page.locator('a,button,[role="button"]')
            count = anchors.count()
            for i in range(min(count, 250)):
                try:
                    item = anchors.nth(i)
                    label = (item.inner_text(timeout=1000) or item.get_attribute('aria-label') or item.get_attribute('title') or '').strip()
                    low = label.lower()
                    if any(k in low for k in kws):
                        item.click(timeout=3000)
                        try:
                            page.wait_for_load_state('networkidle', timeout=10000)
                        except Exception:
                            pass
                        break
                except Exception:
                    continue
            html = page.content()
            try:
                text = page.locator('body').inner_text(timeout=10000)
            except Exception:
                text = ''
            title = page.title() or ''
            browser.close()
            return PageSnapshot(url=page.url, html=html, text=text, title=title)

def detect_blocker(html: str, text: str) -> str | None:
    blob = f'{html[:25000]}\n{text[:25000]}'.lower()
    markers = [
        'captcha', 'recaptcha', 'not a robot', 'verify you are human', 'access denied',
        'forbidden', 'unusual traffic', 'blocked', 'bot detection', 'security check'
    ]
    for m in markers:
        if m in blob:
            return m
    return None

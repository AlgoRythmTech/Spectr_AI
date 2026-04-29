"""
Sandbox Research Engine — Blaxel-powered browser research for every query.

Gives each research task its own isolated computer with headless Chromium.
Fires up a sandbox, runs Playwright-based browser automation, extracts content
from legal databases, government portals, and search engines, then returns
structured research to feed into AI analysis.

Architecture:
  1. Sandbox Pool: Maintains reusable sandboxes (warm standby = 25ms resume)
  2. Browser Research: Puppeteer/Playwright scripts executed in sandbox
  3. Content Extraction: Cleans HTML → structured text for LLM consumption
  4. Smart Routing: Different research strategies for legal, tax, financial queries
"""

import os
import re
import json
import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("sandbox_research")

# === CONFIGURATION ===
BL_API_KEY = os.environ.get("BL_API_KEY", "")
SANDBOX_IMAGE = "blaxel/base-image:latest"  # Node.js 22 + Alpine
SANDBOX_MEMORY = 4096  # MB — enough for headless Chromium
SANDBOX_REGION = "us-pdx-1"
SANDBOX_TTL = 600  # 10 minutes idle → destroy sandbox to save money
SANDBOX_CLEANUP_INTERVAL = 120  # Sweep for stale sandboxes every 2 minutes

# === SANDBOX POOL ===
_sandbox_pool: dict[str, dict] = {}  # name -> {"instance": SandboxInstance, "ready": bool, "last_used": float}
_pool_lock = asyncio.Lock()
_POOL_MAX_SIZE = 3  # Max concurrent sandboxes
_setup_in_progress: set[str] = set()  # Sandbox names currently being set up
_cleanup_task_started = False  # Ensure only one cleanup loop runs


# === BROWSER SETUP SCRIPT ===
# Runs once when a new sandbox is created. Installs Chromium + Puppeteer on Alpine.
BROWSER_SETUP_SCRIPT = """#!/bin/sh
set -e

# Install Chromium and dependencies on Alpine
apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    wget \
    curl \
    jq 2>/dev/null || true

# Install puppeteer-core in /tmp (where research scripts run)
cd /tmp
npm init -y 2>/dev/null
npm install puppeteer-core 2>/dev/null

echo "BROWSER_READY"
"""


# === RESEARCH SCRIPT TEMPLATE ===
# Node.js script that runs in the sandbox to do actual browser research.
# Takes a JSON config via command line argument.

RESEARCH_SCRIPT = r"""
const puppeteer = require('puppeteer-core');
const fs = require('fs');

const config = JSON.parse(process.argv[2] || '{}');
const urls = config.urls || [];
const searchQueries = config.searchQueries || [];
const maxPages = config.maxPages || 8;
const timeout = config.timeout || 15000;

// --- Anti-bot fingerprint randomization ---
const USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
];
const UA = USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];

// Cloudflare / challenge page detectors
const BLOCKED_SIGNALS = [
    'just a moment', 'checking your browser', 'please wait',
    'attention required', 'access denied', 'ray id', 'cloudflare',
    'enable javascript', 'captcha', 'are you human', 'bot detected',
    'blocked', '403 forbidden', '429 too many requests'
];

function isBlockedPage(title, bodyText) {
    const combined = ((title || '') + ' ' + (bodyText || '').substring(0, 500)).toLowerCase();
    return BLOCKED_SIGNALS.some(sig => combined.includes(sig));
}

// Resolve DuckDuckGo redirect URLs to direct URLs
function resolveUrl(rawUrl) {
    if (!rawUrl) return rawUrl;
    try {
        if (rawUrl.includes('duckduckgo.com/l/?uddg=')) {
            const parsed = new URL(rawUrl);
            const real = parsed.searchParams.get('uddg');
            if (real) return decodeURIComponent(real);
        }
    } catch {}
    return rawUrl;
}

// Normalize URL for dedup (strip www, trailing slash, protocol)
function normalizeUrl(url) {
    try {
        const u = new URL(url);
        return (u.hostname.replace(/^www\./, '') + u.pathname.replace(/\/$/, '') + u.search).toLowerCase();
    } catch { return url.toLowerCase(); }
}

async function extractPageContent(page, url) {
    try {
        // Navigate with retry on timeout
        let retries = 2;
        let lastErr;
        for (let attempt = 0; attempt < retries; attempt++) {
            try {
                const response = await page.goto(url, {
                    waitUntil: attempt === 0 ? 'networkidle2' : 'domcontentloaded',
                    timeout: attempt === 0 ? timeout : timeout + 5000
                });
                // Check HTTP status
                const status = response ? response.status() : 0;
                if (status >= 400 && status !== 403) {
                    return { success: false, url, error: `HTTP ${status}`, httpStatus: status };
                }
                break;
            } catch (e) {
                lastErr = e;
                if (attempt < retries - 1) {
                    await new Promise(r => setTimeout(r, 1000 + Math.random() * 2000));
                }
            }
        }

        // Wait a beat for dynamic content
        await new Promise(r => setTimeout(r, 800 + Math.random() * 700));

        const content = await page.evaluate(() => {
            // Check if we're on a blocked/challenge page
            const bodyText = document.body ? document.body.innerText : '';
            const title = document.title || '';

            // Remove noise elements
            const removeSelectors = [
                'script', 'style', 'noscript', 'nav', 'footer', 'header',
                '.ad', '.ads', '.advertisement', '.sidebar', '.cookie-banner',
                '#cookie-consent', '#cookie-notice', '.popup', '.modal',
                '[role="navigation"]', '[role="banner"]', '[role="complementary"]',
                '.social-share', '.comments', '.comment-section', 'iframe',
                '.breadcrumb', '.breadcrumbs', '.pagination', '.newsletter',
                '.related-posts', '.author-bio', '.share-buttons',
                '.wp-block-code', 'pre code', '.print-only',
                '[class*="cookie"]', '[class*="consent"]', '[class*="gdpr"]',
                '[id*="cookie"]', '[id*="consent"]', '.skip-link'
            ];
            removeSelectors.forEach(sel => {
                try { document.querySelectorAll(sel).forEach(el => el.remove()); } catch {}
            });

            // Extract main content — try multiple selectors
            const mainSelectors = [
                'main article', 'article', '[role="main"]', 'main',
                '.post-content', '.entry-content', '.article-content',
                '.content-area', '#content', '.content', '.post-body',
                '.td-post-content', '.single-content', '.page-content'
            ];
            let target = null;
            for (const sel of mainSelectors) {
                target = document.querySelector(sel);
                if (target && target.innerText.trim().length > 100) break;
            }
            if (!target || target.innerText.trim().length < 100) target = document.body;

            // Structured text extraction
            function extractText(node, depth = 0) {
                if (depth > 20) return ''; // prevent infinite recursion
                let text = '';
                if (node.nodeType === Node.TEXT_NODE) {
                    const t = node.textContent.trim();
                    if (t) text += t + ' ';
                } else if (node.nodeType === Node.ELEMENT_NODE) {
                    const tag = node.tagName.toLowerCase();
                    const style = window.getComputedStyle(node);
                    // Skip hidden elements
                    if (style.display === 'none' || style.visibility === 'hidden') return '';

                    if (['h1','h2','h3','h4','h5','h6'].includes(tag)) {
                        const level = '#'.repeat(parseInt(tag[1]));
                        text += '\n\n' + level + ' ' + node.textContent.trim() + '\n\n';
                    } else if (tag === 'p') {
                        const pText = node.textContent.trim();
                        if (pText.length > 5) text += '\n' + pText + '\n';
                    } else if (tag === 'li') {
                        text += '\n- ' + node.textContent.trim();
                    } else if (tag === 'blockquote') {
                        text += '\n> ' + node.textContent.trim() + '\n';
                    } else if (tag === 'table') {
                        const rows = node.querySelectorAll('tr');
                        rows.forEach((row, i) => {
                            const cells = row.querySelectorAll('td, th');
                            const rowText = Array.from(cells).map(c => c.textContent.trim()).join(' | ');
                            text += '\n| ' + rowText + ' |';
                            if (i === 0) {
                                text += '\n|' + Array.from(cells).map(() => '---').join('|') + '|';
                            }
                        });
                        text += '\n';
                    } else if (tag === 'a' && node.href && node.textContent.trim()) {
                        text += node.textContent.trim() + ' ';
                    } else if (['br','hr'].includes(tag)) {
                        text += '\n';
                    } else if (tag === 'strong' || tag === 'b') {
                        text += '**' + node.textContent.trim() + '** ';
                    } else {
                        for (const child of node.childNodes) {
                            text += extractText(child, depth + 1);
                        }
                    }
                }
                return text;
            }

            const extracted = extractText(target);
            const metaDesc = document.querySelector('meta[name="description"]')?.content || '';
            const canonicalUrl = document.querySelector('link[rel="canonical"]')?.href || window.location.href;
            const datePublished = document.querySelector('meta[property="article:published_time"]')?.content
                || document.querySelector('time[datetime]')?.getAttribute('datetime')
                || '';

            return {
                title,
                bodyText: bodyText.substring(0, 200),
                metaDescription: metaDesc,
                url: canonicalUrl,
                datePublished,
                content: extracted.replace(/\n{3,}/g, '\n\n').trim().substring(0, 50000),
                wordCount: extracted.split(/\s+/).filter(w => w.length > 0).length
            };
        });

        // Check for blocked pages
        if (isBlockedPage(content.title, content.bodyText)) {
            return { success: false, url, error: 'Blocked by anti-bot protection', wordCount: 0 };
        }

        // Skip near-empty pages
        if (content.wordCount < 30) {
            return { success: false, url, error: 'Insufficient content', wordCount: content.wordCount };
        }

        delete content.bodyText;
        return { success: true, ...content };
    } catch (err) {
        return { success: false, url, error: err.message };
    }
}

async function searchGoogle(page, query) {
    try {
        // Random delay to appear human
        await new Promise(r => setTimeout(r, 500 + Math.random() * 1500));
        const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(query)}&num=10&hl=en`;
        await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout });

        const results = await page.evaluate(() => {
            const items = [];
            document.querySelectorAll('.g, .tF2Cxc, [data-sokoban-container]').forEach(el => {
                const linkEl = el.querySelector('a[href]');
                const titleEl = el.querySelector('h3');
                const snippetEl = el.querySelector('.VwiC3b, .IsZvec, .s3v9rd');
                if (linkEl && titleEl) {
                    const href = linkEl.getAttribute('href');
                    if (href && href.startsWith('http') && !href.includes('google.com')) {
                        items.push({
                            title: titleEl.textContent.trim(),
                            url: href,
                            snippet: snippetEl ? snippetEl.textContent.trim() : ''
                        });
                    }
                }
            });
            return items.slice(0, 10);
        });

        return results;
    } catch (err) {
        console.error('Google search error:', err.message);
        return [];
    }
}

async function searchDuckDuckGo(page, query) {
    try {
        const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
        await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout });

        const results = await page.evaluate(() => {
            const items = [];
            document.querySelectorAll('.result').forEach(el => {
                const linkEl = el.querySelector('.result__a');
                const snippetEl = el.querySelector('.result__snippet');
                if (linkEl) {
                    let url = linkEl.href || '';
                    // Extract actual URL from DuckDuckGo redirect
                    if (url.includes('duckduckgo.com/l/?uddg=')) {
                        try {
                            const u = new URL(url);
                            const real = u.searchParams.get('uddg');
                            if (real) url = decodeURIComponent(real);
                        } catch {}
                    }
                    items.push({
                        title: linkEl.textContent.trim(),
                        url,
                        snippet: snippetEl ? snippetEl.textContent.trim() : ''
                    });
                }
            });
            return items.slice(0, 10);
        });

        return results;
    } catch (err) {
        console.error('DuckDuckGo search error:', err.message);
        return [];
    }
}

// Bing as third fallback
async function searchBing(page, query) {
    try {
        const searchUrl = `https://www.bing.com/search?q=${encodeURIComponent(query)}&count=10`;
        await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout });

        const results = await page.evaluate(() => {
            const items = [];
            document.querySelectorAll('#b_results .b_algo').forEach(el => {
                const linkEl = el.querySelector('h2 a');
                const snippetEl = el.querySelector('.b_caption p');
                if (linkEl) {
                    items.push({
                        title: linkEl.textContent.trim(),
                        url: linkEl.href,
                        snippet: snippetEl ? snippetEl.textContent.trim() : ''
                    });
                }
            });
            return items.slice(0, 10);
        });

        return results;
    } catch (err) {
        console.error('Bing search error:', err.message);
        return [];
    }
}

(async () => {
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/chromium-browser',
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--single-process',
            '--no-zygote',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--mute-audio',
            '--no-first-run',
            '--ignore-certificate-errors',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080',
        ]
    });

    const page = await browser.newPage();
    await page.setUserAgent(UA);
    await page.setViewport({ width: 1920, height: 1080 });

    // Stealth: override navigator.webdriver
    await page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        window.chrome = { runtime: {} };
    });

    // Block images/fonts/media for speed
    await page.setRequestInterception(true);
    page.on('request', (req) => {
        const type = req.resourceType();
        if (['image', 'media', 'font', 'stylesheet'].includes(type)) {
            req.abort();
        } else {
            req.continue();
        }
    });

    const output = {
        searchResults: [],
        pageContents: [],
        errors: [],
        metadata: {
            startTime: Date.now(),
            urlsProcessed: 0,
            searchesPerformed: 0,
            blockedPages: 0,
            emptyPages: 0
        }
    };

    // Step 1: Run search queries across multiple engines
    for (const query of searchQueries) {
        try {
            // Try DuckDuckGo → Google → Bing
            let results = await searchDuckDuckGo(page, query);
            if (results.length < 3) {
                const googleResults = await searchGoogle(page, query);
                results = [...results, ...googleResults];
            }
            if (results.length < 3) {
                const bingResults = await searchBing(page, query);
                results = [...results, ...bingResults];
            }

            // Dedup by normalized URL
            const seen = new Set();
            const deduped = [];
            for (const r of results) {
                const resolved = resolveUrl(r.url);
                r.url = resolved;
                const norm = normalizeUrl(resolved);
                if (!seen.has(norm)) {
                    seen.add(norm);
                    deduped.push(r);
                }
            }

            output.searchResults.push({ query, results: deduped.slice(0, 10) });
            output.metadata.searchesPerformed++;

            // Auto-visit top results (more for the first query)
            const visitCount = output.searchResults.length === 1 ? 4 : 3;
            const visitUrls = deduped.slice(0, visitCount).map(r => r.url);
            urls.push(...visitUrls);
        } catch (err) {
            output.errors.push({ type: 'search', query, error: err.message });
        }
    }

    // Step 2: Visit URLs and extract content
    const visited = new Set();
    let pagesProcessed = 0;

    for (const rawUrl of urls) {
        if (pagesProcessed >= maxPages) break;
        const url = resolveUrl(rawUrl);
        const norm = normalizeUrl(url);
        if (visited.has(norm)) continue;
        visited.add(norm);

        const content = await extractPageContent(page, url);
        if (content.success) {
            output.pageContents.push(content);
            pagesProcessed++;
            output.metadata.urlsProcessed++;
        } else if (content.error && content.error.includes('Blocked')) {
            output.metadata.blockedPages++;
            output.errors.push({ type: 'blocked', url, error: content.error });
        } else {
            output.metadata.emptyPages++;
            output.errors.push({ type: 'extraction', url, error: content.error || 'Failed' });
        }
    }

    output.metadata.endTime = Date.now();
    output.metadata.durationMs = output.metadata.endTime - output.metadata.startTime;

    await browser.close();

    // Write results to file (safer than stdout for large payloads)
    fs.writeFileSync('/tmp/research_output.json', JSON.stringify(output, null, 2));
    console.log('RESEARCH_COMPLETE');
    console.log(JSON.stringify({
        urlsProcessed: output.metadata.urlsProcessed,
        searchesPerformed: output.metadata.searchesPerformed,
        blocked: output.metadata.blockedPages,
        empty: output.metadata.emptyPages
    }));
})();
"""


# === RESEARCH STRATEGIES ===
# Maps query types to search strategies for maximum relevance

LEGAL_RESEARCH_SITES = [
    # Primary case law databases
    "indiankanoon.org",
    "scconline.com",
    "manupatra.com",
    "casemine.com",
    "legalcrystal.com",
    "latestlaws.com",
    "legitquest.com",
    # Legal news & analysis
    "livelaw.in",
    "barandbench.com",
    "thewire.in/law",
    "theleaflet.in",
    "lawbeat.in",
    "lawctopus.com",
    "legallyindia.com",
    # Court & tribunal websites
    "main.sci.gov.in",           # Supreme Court
    "judgments.ecourts.gov.in",  # E-courts
    "nclt.gov.in",
    "nclat.gov.in",
    "itat.gov.in",
    "cestat.gov.in",
    # Tax-adjacent legal (dual usage)
    "taxguru.in",
    "caclubindia.com",
]

TAX_RESEARCH_SITES = [
    # Official government
    "incometaxindia.gov.in",
    "cbic-gst.gov.in",
    "gstcouncil.gov.in",
    "cbic.gov.in",
    "tin-nsdl.com",
    "eportal.incometax.gov.in",
    "tutorial.gst.gov.in",
    # Primary commentary
    "taxmann.com",
    "taxguru.in",
    "itatonline.org",
    "caclubindia.com",
    "cleartax.in",
    "taxscan.in",
    "a2ztaxcorp.com",
    "taxsutra.com",
    "taxindiaonline.com",
    # ICAI & professional bodies
    "icai.org",
    "icmai.in",
    "icsi.edu",
]

FINANCIAL_RESEARCH_SITES = [
    # Regulators
    "rbi.org.in",
    "sebi.gov.in",
    "irdai.gov.in",
    "pfrda.org.in",
    "ibbi.gov.in",
    "mca.gov.in",
    "fiuindia.gov.in",
    # Exchanges & markets
    "nseindia.com",
    "bseindia.com",
    "mcxindia.com",
    # Financial news
    "moneycontrol.com",
    "economictimes.indiatimes.com",
    "livemint.com",
    "business-standard.com",
    "financialexpress.com",
    "bloombergquint.com",
    # Corporate data
    "zaubacorp.com",
    "tofler.in",
    "screener.in",
]

COMPLIANCE_RESEARCH_SITES = [
    # Corporate
    "mca.gov.in",
    "ibbi.gov.in",
    # Financial regulators
    "rbi.org.in",
    "sebi.gov.in",
    "irdai.gov.in",
    # Labour & employment
    "epfindia.gov.in",
    "esic.gov.in",
    "labour.gov.in",
    "paycheck.in",
    # Trade & customs
    "dgft.gov.in",
    "customs.gov.in",
    # Environmental
    "cpcb.nic.in",
    "moef.gov.in",
    # Data protection
    "meity.gov.in",
    # FEMA/RBI
    "fema.rbi.org.in",
]

# Pre-built site: filter strings for search queries — ALL sites, not a subset
_LEGAL_SITE_FILTER = " OR ".join(f"site:{s}" for s in LEGAL_RESEARCH_SITES)
_TAX_SITE_FILTER = " OR ".join(f"site:{s}" for s in TAX_RESEARCH_SITES)
_FINANCIAL_SITE_FILTER = " OR ".join(f"site:{s}" for s in FINANCIAL_RESEARCH_SITES)
_COMPLIANCE_SITE_FILTER = " OR ".join(f"site:{s}" for s in COMPLIANCE_RESEARCH_SITES)
_ALL_LEGAL_TAX_SITES = " OR ".join(f"site:{s}" for s in sorted(set(
    LEGAL_RESEARCH_SITES + TAX_RESEARCH_SITES
)))
_ALL_SITES = " OR ".join(f"site:{s}" for s in sorted(set(
    LEGAL_RESEARCH_SITES + TAX_RESEARCH_SITES + FINANCIAL_RESEARCH_SITES + COMPLIANCE_RESEARCH_SITES
)))


def _build_search_queries(user_query: str, query_types: list[str]) -> list[str]:
    """Generate targeted search queries based on the user's question and its type."""
    queries = []

    # Primary query — direct (always first)
    queries.append(user_query)

    # Domain-specific expert queries
    if "legal" in query_types or "drafting" in query_types:
        queries.append(f"{user_query} site:indiankanoon.org OR site:livelaw.in OR site:scconline.com")
        queries.append(f"{user_query} Indian law latest judgment ruling 2024 2025 2026")
        queries.append(f"{user_query} supreme court high court order precedent")
    if "taxation" in query_types:
        queries.append(f"{user_query} site:taxguru.in OR site:caclubindia.com OR site:itatonline.org")
        queries.append(f"{user_query} income tax GST India CBDT notification circular 2024 2025 2026")
        queries.append(f"{user_query} TDS section amendment Finance Act")
    if "compliance" in query_types or "regulatory" in query_types:
        queries.append(f"{user_query} compliance India deadline notification circular 2024 2025 2026")
        queries.append(f"{user_query} site:mca.gov.in OR site:rbi.org.in OR site:sebi.gov.in")
    if "financial" in query_types:
        queries.append(f"{user_query} site:rbi.org.in OR site:sebi.gov.in OR site:nseindia.com")
        queries.append(f"{user_query} financial analysis India regulation FEMA FDI")
    if "company" in query_types or "corporate" in query_types:
        queries.append(f"{user_query} Companies Act 2013 MCA ROC")
        queries.append(f"{user_query} site:mca.gov.in OR site:taxguru.in corporate law")

    # Dedup and limit
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:5]  # Max 5 search queries per research task


def _build_direct_urls(user_query: str, query_types: list[str]) -> list[str]:
    """Generate direct URLs to check based on query content."""
    urls = []
    query_lower = user_query.lower()

    # If specific section numbers are mentioned, try IndianKanoon
    section_matches = re.findall(r'section\s+(\d+[A-Za-z]*)', query_lower)
    for sec in section_matches[:2]:
        urls.append(f"https://indiankanoon.org/search/?formInput=section+{sec}+income+tax")

    # If specific act names or subjects are mentioned
    if any(kw in query_lower for kw in ["gst", "cgst", "igst", "sgst"]):
        urls.append("https://cbic-gst.gov.in/gst-acts.html")
    if any(kw in query_lower for kw in ["income tax", "section 80", "section 194", "tds", "section 44"]):
        urls.append("https://incometaxindia.gov.in/pages/acts/income-tax-act.aspx")
    if any(kw in query_lower for kw in ["rera", "real estate"]):
        urls.append("https://rera.gov.in/")
    if any(kw in query_lower for kw in ["rbi", "reserve bank", "fema", "nbfc"]):
        urls.append("https://rbi.org.in/Scripts/NotificationUser.aspx")
    if any(kw in query_lower for kw in ["sebi", "securities", "ipo", "listing"]):
        urls.append("https://www.sebi.gov.in/legal/circulars.html")
    if any(kw in query_lower for kw in ["companies act", "mca", "roc", "annual return"]):
        urls.append("https://www.mca.gov.in/content/mca/global/en/acts-rules/ebooks.html")
    if any(kw in query_lower for kw in ["labour", "labor", "epf", "esic", "pf"]):
        urls.append("https://labour.gov.in/lcandbnotification")
    if any(kw in query_lower for kw in ["ibc", "insolvency", "nclt", "nclat"]):
        urls.append("https://ibbi.gov.in/")
    if any(kw in query_lower for kw in ["arbitration", "mediation"]):
        urls.append("https://indiankanoon.org/search/?formInput=arbitration+act")
    if any(kw in query_lower for kw in ["transfer pricing", "beps", "international tax"]):
        urls.append("https://incometaxindia.gov.in/pages/international-taxation.aspx")

    return urls[:4]


# === CORE ENGINE ===

async def _get_or_create_sandbox(sandbox_name: str = None) -> "SandboxInstance":
    """Get an existing sandbox from pool or create a new one."""
    if not BL_API_KEY:
        raise RuntimeError("BL_API_KEY not set — cannot create sandbox. Set the environment variable to use browser research.")

    from blaxel.core.sandbox import SandboxInstance

    if not sandbox_name:
        sandbox_name = f"spectr-research-{uuid.uuid4().hex[:8]}"

    async with _pool_lock:
        # Check pool for existing ready sandbox
        for name, info in list(_sandbox_pool.items()):
            if info.get("ready"):
                info["last_used"] = time.time()
                logger.info(f"Reusing sandbox from pool: {name}")
                return info["instance"]

        # Evict stale sandboxes if pool is full
        if len(_sandbox_pool) >= _POOL_MAX_SIZE:
            oldest_name = min(_sandbox_pool, key=lambda k: _sandbox_pool[k].get("last_used", 0))
            logger.info(f"Evicting sandbox from pool: {oldest_name}")
            try:
                await SandboxInstance.delete(oldest_name)
            except Exception:
                pass
            del _sandbox_pool[oldest_name]

    # Create new sandbox
    logger.info(f"Creating new sandbox: {sandbox_name}")
    try:
        sandbox = await SandboxInstance.create_if_not_exists({
            "name": sandbox_name,
            "image": SANDBOX_IMAGE,
            "memory": SANDBOX_MEMORY,
            "ports": [{"target": 3000, "protocol": "HTTP"}],
            "region": SANDBOX_REGION,
        })

        async with _pool_lock:
            _sandbox_pool[sandbox_name] = {
                "instance": sandbox,
                "ready": False,
                "last_used": time.time(),
            }

        return sandbox
    except Exception as e:
        logger.error(f"Failed to create sandbox {sandbox_name}: {e}")
        raise


def _get_sandbox_name(sandbox) -> str:
    """Safely extract sandbox name from metadata (handles both dict and object)."""
    meta = sandbox.metadata if hasattr(sandbox, "metadata") else {}
    if hasattr(meta, "name"):
        return meta.name
    if isinstance(meta, dict):
        return meta.get("name", "unknown")
    return "unknown"


async def _ensure_browser_ready(sandbox) -> bool:
    """Install Chromium + Puppeteer in sandbox if not already done."""
    sandbox_name = _get_sandbox_name(sandbox)

    async with _pool_lock:
        pool_entry = _sandbox_pool.get(sandbox_name, {})
        if pool_entry.get("ready"):
            return True
        if sandbox_name in _setup_in_progress:
            # Wait for setup to complete
            for _ in range(60):
                await asyncio.sleep(2)
                if _sandbox_pool.get(sandbox_name, {}).get("ready"):
                    return True
            return False

    _setup_in_progress.add(sandbox_name)
    try:
        logger.info(f"Setting up browser in sandbox {sandbox_name}...")

        # Write setup script
        await sandbox.fs.write("/tmp/setup_browser.sh", BROWSER_SETUP_SCRIPT)

        # Execute setup (install Chromium + puppeteer-core)
        process = await sandbox.process.exec({
            "name": "browser-setup",
            "command": "sh /tmp/setup_browser.sh",
            "wait_for_completion": True,
            "timeout": 60000,  # 60s max for package install
        })

        # Check if setup succeeded
        logs = getattr(process, 'logs', '') or ''
        if "BROWSER_READY" in logs or process.status == "completed":
            logger.info(f"Browser ready in sandbox {sandbox_name}")
            async with _pool_lock:
                if sandbox_name in _sandbox_pool:
                    _sandbox_pool[sandbox_name]["ready"] = True
            return True
        else:
            logger.warning(f"Browser setup failed in {sandbox_name}: status={process.status}, logs={logs[:200]}")
            return False

    except Exception as e:
        logger.error(f"Browser setup failed in {sandbox_name}: {e}")
        return False
    finally:
        _setup_in_progress.discard(sandbox_name)


async def _run_sandbox_script(sandbox, research_config: dict, script_content: str, output_file: str = "/tmp/research_output.json", timeout: int = 90000) -> dict:
    """Execute a Puppeteer research script in sandbox and return parsed results."""
    script_path = f"/tmp/research_{uuid.uuid4().hex[:6]}.js"
    await sandbox.fs.write(script_path, script_content)

    config_json = json.dumps(research_config).replace("'", "\\'")
    process = await sandbox.process.exec({
        "name": f"research-{uuid.uuid4().hex[:6]}",
        "command": f"PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser node {script_path} '{config_json}'",
        "working_dir": "/tmp",
        "wait_for_completion": True,
        "timeout": timeout,
    })

    try:
        result_json = await sandbox.fs.read(output_file)
        return json.loads(result_json)
    except Exception as e:
        logger.warning(f"Failed to read results from {output_file}: {e}")
        return {
            "searchResults": [], "pageContents": [],
            "errors": [{"type": "read_error", "error": str(e)}],
            "metadata": {"urlsProcessed": 0, "searchesPerformed": 0}
        }


async def execute_browser_research(
    user_query: str,
    query_types: list[str],
    max_pages: int = 8,
    timeout_ms: int = 45000,
) -> dict:
    """
    Standard sandbox research — single-pass browser research.
    Used as a fallback or when deep research is not needed.
    """
    start_time = time.time()
    sandbox = None
    sandbox_name = None

    try:
        sandbox = await _get_or_create_sandbox()
        sandbox_name = _get_sandbox_name(sandbox)
        logger.info(f"Research sandbox acquired: {sandbox_name}")

        browser_ready = await _ensure_browser_ready(sandbox)
        if not browser_ready:
            return _fail_result("Browser setup failed in sandbox.", sandbox_name, start_time)

        search_queries = _build_search_queries(user_query, query_types)
        direct_urls = _build_direct_urls(user_query, query_types)

        research_config = {
            "urls": direct_urls,
            "searchQueries": search_queries,
            "maxPages": max_pages,
            "timeout": timeout_ms,
        }

        await sandbox.fs.write("/tmp/research.js", RESEARCH_SCRIPT)
        results = await _run_sandbox_script(sandbox, research_config, RESEARCH_SCRIPT)

        research_summary = _format_research_for_llm(results, user_query)
        duration_ms = int((time.time() - start_time) * 1000)

        final_result = {
            "success": True,
            "search_results": results.get("searchResults", []),
            "page_contents": results.get("pageContents", []),
            "research_summary": research_summary,
            "metadata": {
                "sandbox_name": sandbox_name,
                "duration_ms": duration_ms,
                "urls_processed": results.get("metadata", {}).get("urlsProcessed", 0),
                "searches_performed": results.get("metadata", {}).get("searchesPerformed", 0),
            },
            "errors": results.get("errors", [])
        }

        # Cleanup sandbox after research to save cost (fire-and-forget)
        asyncio.create_task(_cleanup_after_research(sandbox_name))

        return final_result

    except Exception as e:
        logger.error(f"Sandbox research failed: {e}")
        # Cleanup on failure too — don't leave zombie sandboxes
        if sandbox_name:
            asyncio.create_task(_cleanup_after_research(sandbox_name))
        return _fail_result(str(e), sandbox_name, start_time)


async def execute_deep_research(
    user_query: str,
    query_types: list[str],
    progress_callback=None,
) -> dict:
    """
    DEEP RESEARCH ENGINE — Multi-phase, exhaustive browser research.

    This is the beast. When a user selects Deep Research, we don't just search.
    We investigate. We go so deep that opposing counsel won't know what hit them.

    PHASE 1: Broad Intelligence Sweep (5+ searches across Google, Scholar, News)
      → Collects 30-50 URLs, extracts top 12 pages
    PHASE 2: Entity & Citation Extraction
      → Parse phase 1 results for: case names, section numbers, act references,
        entity names, tribunal/court names, circular numbers
      → Build targeted follow-up queries from extracted entities
    PHASE 3: Deep Dive — Follow-up Research
      → Run 4-6 more targeted searches based on phase 2 findings
      → Visit 8-10 more pages, including sub-pages and linked documents
    PHASE 4: Opposing Counsel Analysis
      → Search for counter-arguments, conflicting judgments, dissenting opinions
      → Find cases that went the OTHER way
    PHASE 5: Timeline & Regulatory History
      → Build chronological trail of amendments, notifications, circulars
      → Track how the law evolved on this specific topic

    Total: 20-30 pages extracted, 10-15 searches, 3 minutes of intensive research.
    Result: A research dossier so thorough it could be filed as a brief.
    """
    start_time = time.time()
    sandbox = None
    sandbox_name = None
    all_results = {"searchResults": [], "pageContents": [], "errors": [], "metadata": {}}
    phase_summaries = []

    async def _progress(step: str, label: str, detail: str = "", items: list = None):
        if progress_callback:
            await progress_callback(step, label, detail, items or [])

    try:
        # ─── ACQUIRE SANDBOX ───
        await _progress("deep_init", "Initializing deep research environment",
                       "Spinning up isolated VM with headless Chromium...")
        sandbox = await _get_or_create_sandbox()
        sandbox_name = _get_sandbox_name(sandbox)
        logger.info(f"Deep research sandbox acquired: {sandbox_name}")

        browser_ready = await _ensure_browser_ready(sandbox)
        if not browser_ready:
            return _fail_result("Browser setup failed", sandbox_name, start_time)

        # ─── PHASE 1: BROAD INTELLIGENCE SWEEP ───
        await _progress("deep_phase1", "Phase 1 — Broad intelligence sweep",
                       "Searching across Google Web, News, and Scholar...",
                       ["Google Web", "Google News", "Google Scholar", "Legal Databases"])

        phase1_queries = _build_deep_search_queries_phase1(user_query, query_types)
        direct_urls = _build_direct_urls(user_query, query_types)

        phase1_config = {
            "urls": direct_urls,
            "searchQueries": phase1_queries,
            "maxPages": 12,
            "timeout": 20000,
        }

        phase1_results = await _run_sandbox_script(
            sandbox, phase1_config, RESEARCH_SCRIPT,
            output_file="/tmp/research_output.json", timeout=120000
        )

        p1_pages = len([p for p in phase1_results.get("pageContents", []) if p.get("success")])
        p1_searches = phase1_results.get("metadata", {}).get("searchesPerformed", 0)
        all_results["searchResults"].extend(phase1_results.get("searchResults", []))
        all_results["pageContents"].extend(phase1_results.get("pageContents", []))

        await _progress("deep_phase1_done", f"Phase 1 complete — {p1_pages} sources extracted",
                       f"{p1_searches} searches performed across multiple engines",
                       [p.get("title", "?")[:40] for p in phase1_results.get("pageContents", []) if p.get("success")][:6])

        # ─── PHASE 2: ENTITY & CITATION EXTRACTION ───
        await _progress("deep_phase2", "Phase 2 — Extracting entities and citations",
                       "Analyzing extracted content for case names, section numbers, acts, parties...")

        # Extract entities from all page content
        all_text = "\n".join(
            p.get("content", "") for p in phase1_results.get("pageContents", [])
            if p.get("success") and p.get("content")
        )
        # Also pull from search snippets
        for sr in phase1_results.get("searchResults", []):
            for r in sr.get("results", []):
                all_text += f"\n{r.get('snippet', '')}"

        entities = _extract_research_entities(all_text, user_query)

        await _progress("deep_phase2_done", f"Phase 2 complete — {sum(len(v) for v in entities.values())} entities found",
                       f"Cases: {len(entities.get('cases', []))} | Sections: {len(entities.get('sections', []))} | Acts: {len(entities.get('acts', []))} | Entities: {len(entities.get('entities', []))}",
                       entities.get("cases", [])[:4] + entities.get("sections", [])[:3])

        # ─── PHASE 3: TARGETED DEEP DIVE ───
        phase3_queries = _build_deep_search_queries_phase3(user_query, query_types, entities)

        if phase3_queries:
            await _progress("deep_phase3", f"Phase 3 — Deep dive ({len(phase3_queries)} targeted searches)",
                           "Following up on discovered cases, sections, and entities...",
                           phase3_queries[:5])

            # Build URLs from entity findings
            entity_urls = _build_entity_urls(entities)

            phase3_config = {
                "urls": entity_urls[:6],
                "searchQueries": phase3_queries,
                "maxPages": 10,
                "timeout": 20000,
            }

            phase3_results = await _run_sandbox_script(
                sandbox, phase3_config, RESEARCH_SCRIPT,
                output_file="/tmp/research_output.json", timeout=120000
            )

            p3_pages = len([p for p in phase3_results.get("pageContents", []) if p.get("success")])
            all_results["searchResults"].extend(phase3_results.get("searchResults", []))
            all_results["pageContents"].extend(phase3_results.get("pageContents", []))

            await _progress("deep_phase3_done", f"Phase 3 complete — {p3_pages} additional sources",
                           "Cross-referencing findings across multiple legal databases",
                           [p.get("title", "?")[:40] for p in phase3_results.get("pageContents", []) if p.get("success")][:5])

        # ─── PHASE 4: OPPOSING COUNSEL ANALYSIS ───
        await _progress("deep_phase4", "Phase 4 — Opposing counsel analysis",
                       "Searching for counter-arguments, conflicting judgments, dissenting opinions...",
                       ["Counter-arguments", "Conflicting rulings", "Dissenting opinions", "Risk factors"])

        opposing_queries = _build_opposing_counsel_queries(user_query, query_types, entities)

        if opposing_queries:
            phase4_config = {
                "urls": [],
                "searchQueries": opposing_queries,
                "maxPages": 6,
                "timeout": 15000,
            }

            phase4_results = await _run_sandbox_script(
                sandbox, phase4_config, RESEARCH_SCRIPT,
                output_file="/tmp/research_output.json", timeout=90000
            )

            p4_pages = len([p for p in phase4_results.get("pageContents", []) if p.get("success")])
            all_results["searchResults"].extend(phase4_results.get("searchResults", []))
            # Tag opposing content
            for pc in phase4_results.get("pageContents", []):
                if pc.get("success"):
                    pc["research_phase"] = "opposing_analysis"
            all_results["pageContents"].extend(phase4_results.get("pageContents", []))

            await _progress("deep_phase4_done", f"Phase 4 complete — {p4_pages} counter-argument sources",
                           "Identified potential weaknesses and opposing positions")

        # ─── PHASE 5: TIMELINE & REGULATORY HISTORY ───
        timeline_queries = _build_timeline_queries(user_query, query_types, entities)

        if timeline_queries:
            await _progress("deep_phase5", "Phase 5 — Regulatory timeline & amendment history",
                           "Tracing legislative history, amendments, and circular chronology...",
                           ["Amendment history", "Notification timeline", "Legislative intent", "Committee reports"])

            phase5_config = {
                "urls": [],
                "searchQueries": timeline_queries,
                "maxPages": 5,
                "timeout": 15000,
            }

            phase5_results = await _run_sandbox_script(
                sandbox, phase5_config, RESEARCH_SCRIPT,
                output_file="/tmp/research_output.json", timeout=60000
            )

            p5_pages = len([p for p in phase5_results.get("pageContents", []) if p.get("success")])
            all_results["searchResults"].extend(phase5_results.get("searchResults", []))
            for pc in phase5_results.get("pageContents", []):
                if pc.get("success"):
                    pc["research_phase"] = "timeline"
            all_results["pageContents"].extend(phase5_results.get("pageContents", []))

            await _progress("deep_phase5_done", f"Phase 5 complete — {p5_pages} historical sources",
                           "Full regulatory timeline constructed")

        # ─── COMPILE FINAL DOSSIER ───
        total_pages = len([p for p in all_results.get("pageContents", []) if p.get("success")])
        total_searches = sum(1 for sr in all_results.get("searchResults", []))
        total_words = sum(p.get("wordCount", 0) for p in all_results.get("pageContents", []) if p.get("success"))
        duration_ms = int((time.time() - start_time) * 1000)

        # Deduplicate pages by URL
        seen_urls = set()
        deduped_pages = []
        for pc in all_results.get("pageContents", []):
            url = pc.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped_pages.append(pc)
            elif not url:
                deduped_pages.append(pc)
        all_results["pageContents"] = deduped_pages

        research_summary = _format_deep_research_for_llm(all_results, user_query, entities, duration_ms)

        all_results["metadata"] = {
            "sandbox_name": sandbox_name,
            "duration_ms": duration_ms,
            "urls_processed": total_pages,
            "searches_performed": total_searches,
            "total_words_extracted": total_words,
            "entities_found": sum(len(v) for v in entities.values()),
            "phases_completed": 5,
            "research_type": "deep",
        }

        await _progress("deep_complete",
                       f"Deep research complete — {total_pages} sources, {total_words:,} words, {duration_ms / 1000:.0f}s",
                       f"Sandbox: {sandbox_name} | {total_searches} searches | {total_pages} pages | {sum(len(v) for v in entities.values())} entities",
                       [p.get("title", "?")[:40] for p in deduped_pages if p.get("success")][:8])

        final_result = {
            "success": True,
            "search_results": all_results.get("searchResults", []),
            "page_contents": deduped_pages,
            "research_summary": research_summary,
            "entities": entities,
            "metadata": all_results["metadata"],
            "errors": all_results.get("errors", []),
        }

        # Cleanup sandbox after deep research to save cost (fire-and-forget)
        asyncio.create_task(_cleanup_after_research(sandbox_name))

        return final_result

    except Exception as e:
        logger.error(f"Deep research failed: {e}", exc_info=True)
        # Cleanup on failure too — don't leave zombie sandboxes
        if sandbox_name:
            asyncio.create_task(_cleanup_after_research(sandbox_name))
        return _fail_result(str(e), sandbox_name, start_time)


def _fail_result(error: str, sandbox_name: str, start_time: float) -> dict:
    """Build a standardized failure result."""
    return {
        "success": False,
        "search_results": [],
        "page_contents": [],
        "research_summary": f"Research failed: {error}",
        "metadata": {
            "sandbox_name": sandbox_name or "none",
            "duration_ms": int((time.time() - start_time) * 1000),
            "urls_processed": 0,
            "searches_performed": 0,
        },
        "errors": [error],
    }


# ─────────────────────────────────────────────────────────────
# DEEP RESEARCH QUERY BUILDERS
# ─────────────────────────────────────────────────────────────

def _build_deep_search_queries_phase1(user_query: str, query_types: list[str]) -> list[str]:
    """Phase 1: Broad intelligence sweep — ALL research sites, not a subset."""
    queries = []
    queries.append(user_query)

    # Domain-specific expert searches — use FULL site lists
    if "legal" in query_types or "drafting" in query_types:
        queries.append(f"{user_query} {_LEGAL_SITE_FILTER}")
        queries.append(f"{user_query} supreme court high court judgment ruling India 2024 2025 2026")
        queries.append(f"{user_query} ratio decidendi precedent binding authority India")
    if "taxation" in query_types:
        queries.append(f"{user_query} {_TAX_SITE_FILTER}")
        queries.append(f"{user_query} CBDT CBIC notification circular India income tax GST 2024 2025 2026")
        queries.append(f"{user_query} ITAT tribunal ruling assessment year")
    if "compliance" in query_types or "regulatory" in query_types:
        queries.append(f"{user_query} {_COMPLIANCE_SITE_FILTER}")
        queries.append(f"{user_query} India regulatory compliance deadline notification 2024 2025 2026")
    if "financial" in query_types:
        queries.append(f"{user_query} {_FINANCIAL_SITE_FILTER}")
        queries.append(f"{user_query} FEMA FDI ECB India regulation")
    if "corporate" in query_types or "company" in query_types:
        queries.append(f"{user_query} Companies Act 2013 MCA ROC NCLT NCLAT IBC India")
        queries.append(f"{user_query} {_COMPLIANCE_SITE_FILTER}")

    # Always add a news search + academic search
    queries.append(f"{user_query} India latest news update 2025 2026")
    queries.append(f"{user_query} India legal analysis commentary")

    seen = set()
    unique = [q for q in queries if q not in seen and not seen.add(q)]
    return unique[:9]  # Up to 9 searches (was 7 — broader net now)


def _build_deep_search_queries_phase3(user_query: str, query_types: list[str], entities: dict) -> list[str]:
    """Phase 3: Targeted follow-up based on entities discovered in Phase 1.

    Uses site: filters for legal authority sources — not generic web pages.
    """
    queries = []
    is_legal = "legal" in query_types or "drafting" in query_types
    is_tax = "taxation" in query_types or "financial" in query_types

    # Case-specific deep dives — search ALL legal databases
    for case_name in entities.get("cases", [])[:4]:
        if is_legal:
            queries.append(f"\"{case_name}\" {_LEGAL_SITE_FILTER}")
        elif is_tax:
            queries.append(f"\"{case_name}\" {_TAX_SITE_FILTER}")
        else:
            queries.append(f"\"{case_name}\" full judgment ratio India {_ALL_LEGAL_TAX_SITES}")

    # Section-specific research — ALL authoritative sources
    for section in entities.get("sections", [])[:3]:
        if is_tax:
            queries.append(f"Section {section} interpretation judgment {_TAX_SITE_FILTER}")
        elif is_legal:
            queries.append(f"Section {section} interpretation judgment latest {_LEGAL_SITE_FILTER}")
        else:
            queries.append(f"Section {section} interpretation judgment India latest {_ALL_LEGAL_TAX_SITES}")

    # Act-specific research — ALL government and legal portals
    for act in entities.get("acts", [])[:2]:
        if is_tax:
            queries.append(f"{act} amendment notification circular {_TAX_SITE_FILTER}")
        else:
            queries.append(f"{act} amendment latest notification circular India {_LEGAL_SITE_FILTER}")

    # Circular/notification lookups
    for circular in entities.get("circulars", [])[:2]:
        queries.append(f"\"{circular}\" full text India")

    # Entity-specific research (companies, people)
    for entity in entities.get("entities", [])[:2]:
        queries.append(f"\"{entity}\" {user_query[:30]} India legal")

    seen = set()
    unique = [q for q in queries if q not in seen and not seen.add(q)]
    return unique[:6]


def _build_opposing_counsel_queries(user_query: str, query_types: list[str], entities: dict) -> list[str]:
    """Phase 4: Find what the OTHER side would argue. Counter-arguments, conflicting rulings.

    Uses legal authority sites so results are actual court decisions, not blog opinions.
    """
    queries = []
    q_lower = user_query.lower()

    # Flip the perspective — search ALL legal databases for rulings that went the OTHER way
    if any(kw in q_lower for kw in ["deduction", "exempt", "allowable", "eligible"]):
        queries.append(f"{user_query} disallowed rejected not eligible {_ALL_LEGAL_TAX_SITES}")
        queries.append(f"{user_query} revenue appeal department won India judgment {_LEGAL_SITE_FILTER}")
    elif any(kw in q_lower for kw in ["penalty", "prosecution", "demand"]):
        queries.append(f"{user_query} quashed set aside relief {_ALL_LEGAL_TAX_SITES}")
        queries.append(f"{user_query} reasonable cause defence India judgment {_LEGAL_SITE_FILTER}")
    else:
        queries.append(f"{user_query} against opposing view conflicting judgment {_ALL_LEGAL_TAX_SITES}")
        queries.append(f"{user_query} distinguished overruled India judgment {_LEGAL_SITE_FILTER}")

    # Find cases that went the other way — ALL legal databases
    for case_name in entities.get("cases", [])[:2]:
        queries.append(f"\"{case_name}\" distinguished overruled {_ALL_LEGAL_TAX_SITES}")
        # NEW: explicit stay / SLP queries so we catch Supreme Court stays on HC orders
        queries.append(f"\"{case_name}\" supreme court stay SLP 2024 2025 2026 India")

    # Find counter-circulars or amendments that changed the position — ALL sources
    for section in entities.get("sections", [])[:2]:
        queries.append(f"Section {section} conflicting judgments India high court {_ALL_LEGAL_TAX_SITES}")

    # === RECENCY LAYER — ALWAYS run these, even without named entities ===
    # Catches Supreme Court stays, recent SLPs, overrulings, and doctrinal shifts that
    # blew up the position between training cutoff and today. This is what the
    # reviewer caught us missing on right-to-be-forgotten (Karthick Theodore stay Jul 2024,
    # SLP (C) 4054/2026 stay Feb 2026).
    queries.append(f"{user_query} supreme court stay order SLP 2024 2025 2026 India {_LEGAL_SITE_FILTER}")
    queries.append(f"{user_query} latest supreme court judgment overruled stayed 2025 2026")
    queries.append(f"{user_query} high court judgment stayed by supreme court recent India")

    seen = set()
    unique = [q for q in queries if q not in seen and not seen.add(q)]
    return unique[:6]  # bumped from 4 to 6 for recency layer


def _build_timeline_queries(user_query: str, query_types: list[str], entities: dict) -> list[str]:
    """Phase 5: Build a chronological trail of legislative/regulatory evolution."""
    queries = []
    is_tax = "taxation" in query_types or "financial" in query_types

    for section in entities.get("sections", [])[:2]:
        site_filter = _TAX_SITE_FILTER if is_tax else _LEGAL_SITE_FILTER
        queries.append(f"Section {section} amendment history Finance Act India {site_filter}")
        queries.append(f"Section {section} insertion substitution omission timeline India {_ALL_LEGAL_TAX_SITES}")

    for act in entities.get("acts", [])[:2]:
        queries.append(f"{act} amendment history timeline India {_ALL_LEGAL_TAX_SITES}")

    if not queries:
        # Generic timeline query — use ALL sites
        queries.append(f"{user_query} amendment history timeline India {_ALL_LEGAL_TAX_SITES}")
        queries.append(f"{user_query} notification circular chronology India {_COMPLIANCE_SITE_FILTER}")

    seen = set()
    unique = [q for q in queries if q not in seen and not seen.add(q)]
    return unique[:4]


def _build_entity_urls(entities: dict) -> list[str]:
    """Generate direct URLs from extracted entities."""
    urls = []
    for case_name in entities.get("cases", [])[:3]:
        safe_name = case_name.replace(" ", "+").replace(".", "")
        urls.append(f"https://indiankanoon.org/search/?formInput={safe_name}")
    for section in entities.get("sections", [])[:2]:
        urls.append(f"https://indiankanoon.org/search/?formInput=section+{section}+income+tax")
    return urls[:5]


# ─────────────────────────────────────────────────────────────
# ENTITY EXTRACTION — Parse research content for key legal entities
# ─────────────────────────────────────────────────────────────

def _extract_research_entities(text: str, user_query: str) -> dict:
    """
    Extract legal entities from research text:
    - Case names (X v. Y, X vs Y)
    - Section numbers (Section 194T, s.43B)
    - Act references (Income Tax Act, Companies Act)
    - Circular/notification numbers
    - Named entities (companies, tribunals)
    """
    entities = {
        "cases": [],
        "sections": [],
        "acts": [],
        "circulars": [],
        "entities": [],
    }

    if not text:
        return entities

    # Limit text to first 100K chars for performance
    text = text[:100000]

    # ─── Case names ───
    case_patterns = [
        r'([A-Z][a-zA-Z\.\s]{2,35}?)\s+(?:v\.|vs\.?|versus)\s+([A-Z][a-zA-Z\.\s]{2,35}?)(?=\s+(?:held|where|ruled|observed|decided|confirmed|stated|opined|upheld|\(|\d{4}|,|\.))',
        r'([A-Z][a-zA-Z\.\s]{2,35}?)\s+(?:v\.|vs\.?|versus)\s+([A-Z][a-zA-Z\.\s]{2,35}?)$',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v/s\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    ]
    seen_cases = set()
    for pattern in case_patterns:
        for m in re.finditer(pattern, text, re.MULTILINE):
            p1 = m.group(1).strip().rstrip(",. ")
            p2 = m.group(2).strip().rstrip(",. ")
            case = f"{p1} v. {p2}"
            case_normalized = case.lower().strip()
            if 8 < len(case) < 80 and case_normalized not in seen_cases:
                seen_cases.add(case_normalized)
                entities["cases"].append(case)
    entities["cases"] = entities["cases"][:10]  # Cap at 10

    # ─── Section numbers ───
    section_patterns = [
        r'[Ss]ection\s+(\d+[A-Z]*(?:\([a-z0-9]+\))*)',
        r'[Ss]\.?\s*(\d+[A-Z]*(?:\([a-z0-9]+\))*)',
        r'(?:u/s|under section)\s+(\d+[A-Z]*(?:\([a-z0-9]+\))*)',
    ]
    seen_sections = set()
    for pattern in section_patterns:
        for m in re.finditer(pattern, text):
            sec = m.group(1).strip()
            if sec and sec not in seen_sections and not sec.startswith("20") and len(sec) < 15:
                seen_sections.add(sec)
                entities["sections"].append(sec)
    entities["sections"] = sorted(list(set(entities["sections"])))[:15]

    # ─── Act references ───
    act_patterns = [
        r'(Income[\s-]Tax\s+Act(?:\s*,?\s*\d{4})?)',
        r'(Companies\s+Act(?:\s*,?\s*\d{4})?)',
        r'((?:C|I|S)GST\s+Act(?:\s*,?\s*\d{4})?)',
        r'(FEMA\s*(?:\d{4})?)',
        r'(SEBI\s+Act(?:\s*,?\s*\d{4})?)',
        r'(Indian\s+Contract\s+Act(?:\s*,?\s*\d{4})?)',
        r'(Insolvency\s+and\s+Bankruptcy\s+Code(?:\s*,?\s*\d{4})?)',
        r'(Negotiable\s+Instruments\s+Act(?:\s*,?\s*\d{4})?)',
        r'((?:BNS|BNSS|BSA)(?:\s*,?\s*\d{4})?)',
        r'(Transfer\s+of\s+Property\s+Act(?:\s*,?\s*\d{4})?)',
        r'(Indian\s+Penal\s+Code|IPC)',
        r'(Code\s+of\s+Criminal\s+Procedure|CrPC)',
        r'(RERA\s*(?:\d{4})?)',
        r'(Finance\s+Act(?:\s*,?\s*\d{4})?)',
        r'(PMLA\s*(?:\d{4})?)',
    ]
    seen_acts = set()
    for pattern in act_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            act = m.group(1).strip()
            act_norm = act.lower()
            if act_norm not in seen_acts:
                seen_acts.add(act_norm)
                entities["acts"].append(act)
    entities["acts"] = entities["acts"][:8]

    # ─── Circular/notification numbers ───
    circular_patterns = [
        r'(?:Circular|Notification|Order)\s+No\.?\s*(\d+[\/-]\d+(?:[\/-]\d+)?)',
        r'(?:CBDT|CBIC|RBI|SEBI|MCA)\s+(?:Circular|Notification)\s+(?:No\.?\s*)?(\S+)',
        r'(?:F\.?\s*No\.?|File\s+No\.?)\s+(\d+[\/-]\d+[\/-]\d+(?:[\/-]\S+)?)',
    ]
    seen_circulars = set()
    for pattern in circular_patterns:
        for m in re.finditer(pattern, text):
            circ = m.group(1).strip() if m.group(1) else m.group(0).strip()
            if circ not in seen_circulars and len(circ) < 50:
                seen_circulars.add(circ)
                entities["circulars"].append(circ)
    entities["circulars"] = entities["circulars"][:5]

    # ─── Named entities (tribunals, courts, companies) ───
    tribunal_patterns = [
        r'(ITAT\s+[\w\s]+Bench)',
        r'(NCLT\s+[\w\s]+Bench)',
        r'((?:Bombay|Delhi|Madras|Calcutta|Allahabad|Karnataka|Kerala|Gujarat|Rajasthan|Punjab|Hyderabad|Telangana)\s+High\s+Court)',
        r'(Supreme\s+Court\s+of\s+India)',
        r'(National\s+Company\s+Law\s+(?:Tribunal|Appellate\s+Tribunal))',
        r'(Authority\s+for\s+Advance\s+Rulings?|AAR)',
    ]
    seen_entities = set()
    for pattern in tribunal_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            ent = m.group(1).strip()
            if ent.lower() not in seen_entities:
                seen_entities.add(ent.lower())
                entities["entities"].append(ent)
    entities["entities"] = entities["entities"][:6]

    return entities


# ─────────────────────────────────────────────────────────────
# DEEP RESEARCH LLM FORMATTER
# ─────────────────────────────────────────────────────────────

def _format_deep_research_for_llm(results: dict, user_query: str, entities: dict, duration_ms: int) -> str:
    """
    Format deep research results into an exhaustive research dossier for the AI.
    This is the mother of all context blocks — structured for maximum legal analysis.
    """
    parts = []
    meta = results.get("metadata", {})
    total_pages = len([p for p in results.get("pageContents", []) if p.get("success")])
    total_searches = len(results.get("searchResults", []))
    total_words = sum(p.get("wordCount", 0) for p in results.get("pageContents", []) if p.get("success"))

    parts.append("=" * 70)
    parts.append("DEEP RESEARCH DOSSIER — EXHAUSTIVE MULTI-PHASE INVESTIGATION")
    parts.append("=" * 70)
    parts.append(f"Subject: {user_query}")
    parts.append(f"Research depth: 5-phase deep investigation")
    parts.append(f"Sources analyzed: {total_pages} pages | {total_searches} search operations | {total_words:,} words extracted")
    parts.append(f"Duration: {duration_ms / 1000:.1f} seconds")
    parts.append("")

    # ─── ENTITY INTELLIGENCE SUMMARY ───
    if any(entities.values()):
        parts.append("─" * 50)
        parts.append("ENTITY INTELLIGENCE (Extracted from sources)")
        parts.append("─" * 50)
        if entities.get("cases"):
            parts.append(f"Cases Found ({len(entities['cases'])}):")
            for c in entities["cases"]:
                parts.append(f"  • {c}")
        if entities.get("sections"):
            parts.append(f"Statutory Sections ({len(entities['sections'])}):")
            parts.append(f"  {', '.join(f'Section {s}' for s in entities['sections'])}")
        if entities.get("acts"):
            parts.append(f"Acts Referenced ({len(entities['acts'])}):")
            for a in entities["acts"]:
                parts.append(f"  • {a}")
        if entities.get("circulars"):
            parts.append(f"Circulars/Notifications ({len(entities['circulars'])}):")
            for c in entities["circulars"]:
                parts.append(f"  • {c}")
        if entities.get("entities"):
            parts.append(f"Tribunals/Courts ({len(entities['entities'])}):")
            for e in entities["entities"]:
                parts.append(f"  • {e}")
        parts.append("")

    # ─── SEARCH RESULTS SUMMARY ───
    all_search_results = []
    for sr in results.get("searchResults", []):
        query = sr.get("query", "")
        sr_results = sr.get("results", [])
        if sr_results:
            parts.append(f"── Search: \"{query[:80]}\" ({len(sr_results)} results) ──")
            for idx, r in enumerate(sr_results[:6], 1):
                parts.append(f"  {idx}. {r.get('title', 'No title')}")
                parts.append(f"     {r.get('url', '')}")
                snippet = r.get("snippet", "")
                if snippet:
                    parts.append(f"     → {snippet[:300]}")
            parts.append("")

    # ─── PRIMARY SOURCE EXTRACTS ───
    primary_pages = [p for p in results.get("pageContents", [])
                     if p.get("success") and not p.get("research_phase")]
    primary_pages.sort(key=lambda p: p.get("wordCount", 0), reverse=True)

    if primary_pages:
        parts.append("=" * 70)
        parts.append(f"PRIMARY SOURCES ({len(primary_pages)} pages)")
        parts.append("=" * 70)

        for idx, pc in enumerate(primary_pages, 1):
            title = pc.get("title", "Unknown")
            url = pc.get("url", "")
            content = pc.get("content", "")
            word_count = pc.get("wordCount", 0)
            date = pc.get("datePublished", "")

            if content and len(content) > 50:
                parts.append(f"\n{'─' * 50}")
                parts.append(f"SOURCE {idx}: {title}")
                parts.append(f"URL: {url}")
                parts.append(f"Words: {word_count}" + (f" | Published: {date}" if date else ""))
                parts.append("─" * 50)

                if len(content) > 12000:
                    parts.append(content[:8000])
                    parts.append("\n[... content truncated for brevity ...]\n")
                    parts.append(content[-4000:])
                else:
                    parts.append(content)

    # ─── OPPOSING ANALYSIS SOURCES ───
    opposing_pages = [p for p in results.get("pageContents", [])
                      if p.get("success") and p.get("research_phase") == "opposing_analysis"]

    if opposing_pages:
        parts.append(f"\n{'=' * 70}")
        parts.append(f"OPPOSING COUNSEL ANALYSIS ({len(opposing_pages)} counter-argument sources)")
        parts.append("=" * 70)
        parts.append("WARNING: The following sources present arguments AGAINST the primary position.")
        parts.append("Use these to anticipate and prepare rebuttals.\n")

        for idx, pc in enumerate(opposing_pages, 1):
            title = pc.get("title", "Unknown")
            url = pc.get("url", "")
            content = pc.get("content", "")
            word_count = pc.get("wordCount", 0)

            if content and len(content) > 50:
                parts.append(f"COUNTER-SOURCE {idx}: {title}")
                parts.append(f"URL: {url} | Words: {word_count}")
                if len(content) > 6000:
                    parts.append(content[:5000])
                    parts.append("[... truncated ...]")
                else:
                    parts.append(content)
                parts.append("")

    # ─── TIMELINE SOURCES ───
    timeline_pages = [p for p in results.get("pageContents", [])
                      if p.get("success") and p.get("research_phase") == "timeline"]

    if timeline_pages:
        parts.append(f"\n{'=' * 70}")
        parts.append(f"LEGISLATIVE TIMELINE ({len(timeline_pages)} historical sources)")
        parts.append("=" * 70)

        for idx, pc in enumerate(timeline_pages, 1):
            title = pc.get("title", "Unknown")
            url = pc.get("url", "")
            content = pc.get("content", "")
            word_count = pc.get("wordCount", 0)

            if content and len(content) > 50:
                parts.append(f"TIMELINE SOURCE {idx}: {title}")
                parts.append(f"URL: {url} | Words: {word_count}")
                if len(content) > 5000:
                    parts.append(content[:4000])
                    parts.append("[... truncated ...]")
                else:
                    parts.append(content)
                parts.append("")

    # ─── MASTER CITATION INDEX ───
    all_successful = [p for p in results.get("pageContents", []) if p.get("success")]
    if all_successful:
        parts.append(f"\n{'=' * 70}")
        parts.append("MASTER CITATION INDEX — USE FOR ATTRIBUTION")
        parts.append("=" * 70)
        for idx, pc in enumerate(all_successful, 1):
            phase_tag = ""
            if pc.get("research_phase") == "opposing_analysis":
                phase_tag = " [OPPOSING]"
            elif pc.get("research_phase") == "timeline":
                phase_tag = " [TIMELINE]"
            parts.append(f"  [{idx}] {pc.get('title', '?')[:80]}{phase_tag}")
            parts.append(f"      {pc.get('url', '')}")

    return "\n".join(parts)


def _format_research_for_llm(results: dict, user_query: str) -> str:
    """Format raw research results into structured context for the AI model.

    Produces a clean, hierarchical document that maximizes LLM comprehension:
    - Summary header with stats
    - Search results with snippets (for breadth)
    - Full page extracts (for depth) — sorted by relevance/word count
    - Source attribution for citation generation
    """
    parts = []
    meta = results.get("metadata", {})
    urls_checked = meta.get("urlsProcessed", 0)
    searches_done = meta.get("searchesPerformed", 0)
    blocked = meta.get("blockedPages", 0)
    duration = meta.get("durationMs", 0)

    parts.append("=" * 60)
    parts.append("LIVE BROWSER RESEARCH — REAL-TIME WEB INTELLIGENCE")
    parts.append("=" * 60)
    parts.append(f"Query: {user_query}")
    parts.append(f"Sources extracted: {urls_checked} pages | {searches_done} search engines | {duration}ms")
    if blocked:
        parts.append(f"Note: {blocked} sources blocked by anti-bot protection")
    parts.append("")

    # Search results summary — gives the model breadth of what's out there
    all_search_results = []
    for sr in results.get("searchResults", []):
        query = sr.get("query", "")
        sr_results = sr.get("results", [])
        if sr_results:
            parts.append(f"── Search: \"{query}\" ({len(sr_results)} results) ──")
            for idx, r in enumerate(sr_results[:6], 1):
                title = r.get("title", "No title")
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                parts.append(f"  {idx}. {title}")
                parts.append(f"     {url}")
                if snippet:
                    parts.append(f"     → {snippet[:250]}")
                all_search_results.append(r)
            parts.append("")

    # Page content extracts — sorted by word count (most substantive first)
    page_contents = [pc for pc in results.get("pageContents", []) if pc.get("success")]
    page_contents.sort(key=lambda pc: pc.get("wordCount", 0), reverse=True)

    if page_contents:
        parts.append("=" * 60)
        parts.append(f"EXTRACTED SOURCES ({len(page_contents)} pages)")
        parts.append("=" * 60)

    for idx, pc in enumerate(page_contents, 1):
        title = pc.get("title", "Unknown Page")
        url = pc.get("url", "")
        content = pc.get("content", "")
        word_count = pc.get("wordCount", 0)
        date_published = pc.get("datePublished", "")

        if content and len(content) > 50:
            parts.append(f"\n{'─' * 50}")
            parts.append(f"SOURCE {idx}: {title}")
            parts.append(f"URL: {url}")
            parts.append(f"Words: {word_count}" + (f" | Published: {date_published}" if date_published else ""))
            parts.append(f"{'─' * 50}")

            # Smart truncation — keep beginning and end for context
            if len(content) > 10000:
                parts.append(content[:7000])
                parts.append("\n[... middle content omitted for brevity ...]\n")
                parts.append(content[-3000:])
            elif len(content) > 6000:
                parts.append(content[:5000])
                parts.append("\n[... content truncated ...]\n")
                parts.append(content[-1500:])
            else:
                parts.append(content)

    # Source attribution block — helps the model cite properly
    if page_contents:
        parts.append(f"\n{'=' * 60}")
        parts.append("CITATION SOURCES (use these for attribution)")
        parts.append("=" * 60)
        for idx, pc in enumerate(page_contents, 1):
            parts.append(f"  [{idx}] {pc.get('title', '?')[:80]} — {pc.get('url', '')}")

    # Errors (only if significant)
    errors = results.get("errors", [])
    if errors and len(errors) > 0:
        parts.append(f"\n── Research Notes ({len(errors)} issues) ──")
        for err in errors[:5]:
            if isinstance(err, dict):
                parts.append(f"  • {err.get('type', 'error')}: {err.get('url', '?')[:60]} — {err.get('error', str(err))[:80]}")
            else:
                parts.append(f"  • {err}")

    return "\n".join(parts)


# === SANDBOX MANAGEMENT ===

async def get_active_sandboxes() -> list[dict]:
    """Return info about all active research sandboxes."""
    result = []
    for name, info in _sandbox_pool.items():
        result.append({
            "name": name,
            "ready": info.get("ready", False),
            "last_used": info.get("last_used", 0),
            "age_seconds": int(time.time() - info.get("last_used", time.time())),
        })
    return result


async def cleanup_sandbox(sandbox_name: str) -> bool:
    """Delete a specific sandbox and remove from pool."""
    from blaxel.core.sandbox import SandboxInstance

    try:
        await SandboxInstance.delete(sandbox_name)
        async with _pool_lock:
            _sandbox_pool.pop(sandbox_name, None)
        logger.info(f"Sandbox {sandbox_name} cleaned up")
        return True
    except Exception as e:
        logger.warning(f"Sandbox cleanup failed for {sandbox_name}: {e}")
        async with _pool_lock:
            _sandbox_pool.pop(sandbox_name, None)
        return False


async def cleanup_all_sandboxes():
    """Delete all research sandboxes (call on shutdown)."""
    from blaxel.core.sandbox import SandboxInstance

    names = list(_sandbox_pool.keys())
    for name in names:
        try:
            await SandboxInstance.delete(name)
            logger.info(f"Cleaned up sandbox: {name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox {name}: {e}")

    async with _pool_lock:
        _sandbox_pool.clear()


async def cleanup_orphaned_sandboxes():
    """Destroy ALL remote Blaxel sandboxes with our prefix on startup.
    Catches orphans from previous server runs/crashes that leaked sandboxes.
    """
    if not BL_API_KEY:
        return 0

    from blaxel.core.sandbox import SandboxInstance
    destroyed = 0
    try:
        # List all sandboxes on the account
        sandboxes = await SandboxInstance.list()
        if not sandboxes:
            return 0

        for sb in sandboxes:
            name = ""
            if hasattr(sb, "metadata"):
                meta = sb.metadata
                name = meta.name if hasattr(meta, "name") else (meta.get("name", "") if isinstance(meta, dict) else "")
            elif hasattr(sb, "name"):
                name = sb.name

            # Only destroy sandboxes with our prefix
            if name and name.startswith("spectr-"):
                try:
                    await SandboxInstance.delete(name)
                    destroyed += 1
                    logger.info(f"Orphan cleanup: destroyed {name}")
                except Exception as e:
                    logger.warning(f"Orphan cleanup: failed to delete {name}: {e}")

        if destroyed:
            logger.info(f"Orphan cleanup complete: {destroyed} sandbox(es) destroyed")
    except Exception as e:
        logger.warning(f"Orphan cleanup failed (non-blocking): {e}")

    return destroyed


async def warm_sandbox_pool():
    """Pre-warm a sandbox so the first research query is fast."""
    try:
        sandbox = await _get_or_create_sandbox(f"spectr-warm-{uuid.uuid4().hex[:6]}")
        await _ensure_browser_ready(sandbox)
        logger.info("Sandbox pool pre-warmed")
    except Exception as e:
        logger.warning(f"Sandbox pre-warm failed (non-blocking): {e}")


async def _cleanup_after_research(sandbox_name: str):
    """Delete a sandbox after research is complete — saves cost.
    Called automatically after execute_browser_research / execute_deep_research.
    """
    if not sandbox_name:
        return
    try:
        await cleanup_sandbox(sandbox_name)
        logger.info(f"Post-research cleanup: sandbox {sandbox_name} destroyed")
    except Exception as e:
        logger.warning(f"Post-research cleanup failed for {sandbox_name}: {e}")


async def _idle_sandbox_reaper():
    """Background task that periodically destroys sandboxes idle > SANDBOX_TTL.
    Runs every SANDBOX_CLEANUP_INTERVAL seconds. Ensures no orphaned sandboxes
    accumulate on Blaxel and rack up charges.
    """
    from blaxel.core.sandbox import SandboxInstance

    while True:
        await asyncio.sleep(SANDBOX_CLEANUP_INTERVAL)
        try:
            now = time.time()
            stale = []
            async with _pool_lock:
                for name, info in list(_sandbox_pool.items()):
                    idle_seconds = now - info.get("last_used", now)
                    if idle_seconds > SANDBOX_TTL:
                        stale.append(name)

            for name in stale:
                try:
                    await SandboxInstance.delete(name)
                    logger.info(f"Idle reaper: destroyed sandbox {name} (idle {int(now - _sandbox_pool.get(name, {}).get('last_used', now))}s)")
                except Exception as e:
                    logger.warning(f"Idle reaper: failed to delete {name}: {e}")
                async with _pool_lock:
                    _sandbox_pool.pop(name, None)

            if stale:
                logger.info(f"Idle reaper: cleaned up {len(stale)} stale sandbox(es)")
        except Exception as e:
            logger.warning(f"Idle reaper error (will retry): {e}")


def start_idle_reaper():
    """Start the background sandbox idle reaper (call once from server startup)."""
    global _cleanup_task_started
    if _cleanup_task_started:
        return
    _cleanup_task_started = True
    asyncio.create_task(_idle_sandbox_reaper())
    logger.info(f"Sandbox idle reaper started — TTL={SANDBOX_TTL}s, sweep every {SANDBOX_CLEANUP_INTERVAL}s")


# === QUERY TYPE DETECTION ===

def should_use_sandbox_research(user_query: str, query_types: list[str]) -> bool:
    """Determine if this query would benefit from live browser research.

    Triggers sandbox for:
    - Complex legal questions needing latest case law
    - Tax queries needing current notifications/circulars
    - Regulatory compliance questions
    - Any query containing words like "latest", "recent", "current", "2024", "2025"
    - Queries about specific companies, cases, or government actions
    - Due diligence, risk assessment, market research queries

    Does NOT trigger for:
    - Simple greetings, calculations, format requests
    - Workflow execution commands
    - Internal document queries (vault)
    """
    query_lower = user_query.lower()

    # Skip for trivial queries
    skip_patterns = [
        r"^(hi|hello|hey|thanks|thank you|ok|okay|yes|no|sure)\b",
        r"^(help|menu|commands|what can you do)",
        r"^(calculate|compute|convert)\b",
        r"^(draft|template|format)\b.*\b(letter|email|notice)\b",
    ]
    if any(re.match(p, query_lower) for p in skip_patterns):
        return False

    # Skip very short queries (likely conversational)
    if len(user_query.split()) < 4:
        return False

    # Always trigger for these query types
    high_value_types = {"legal", "taxation", "compliance", "regulatory", "financial", "company"}
    if high_value_types.intersection(set(query_types)):
        return True

    # Trigger for recency indicators
    recency_keywords = [
        "latest", "recent", "current", "new", "updated", "amendment",
        "notification", "circular", "judgment", "order", "ruling",
        "2024", "2025", "2026", "this year", "last month", "this quarter",
        "budget", "finance act", "union budget",
    ]
    if any(kw in query_lower for kw in recency_keywords):
        return True

    # Trigger for specific research patterns
    research_patterns = [
        r"\bcase\s+law\b", r"\bjudgment\b", r"\bprecedent\b",
        r"\bnotification\b", r"\bcircular\b", r"\bpress\s+note\b",
        r"\bRBI\b", r"\bSEBI\b", r"\bCBDT\b", r"\bCBIC\b", r"\bMCA\b",
        r"\bsupreme\s+court\b", r"\bhigh\s+court\b", r"\btribunal\b",
        r"\bnclt\b", r"\bnclat\b", r"\bitat\b", r"\bsat\b",
        r"\bdue\s+diligence\b", r"\brisk\s+assessment\b",
        r"\bmarket\s+research\b", r"\bindustry\s+analysis\b",
        r"\bregulatory\s+update\b", r"\bpolicy\s+change\b",
        r"\bfema\b", r"\bfdi\b", r"\bfcra\b",
        r"\binsolvency\b", r"\bbankruptcy\b", r"\bibc\b",
        r"\btransfer\s+pricing\b", r"\binternational\s+tax\b",
        r"\banti.?money\s+laundering\b", r"\bpmla\b",
        r"\bcompan(y|ies)\s+act\b", r"\bpartnership\b",
        r"\blabou?r\s+(law|code|act)\b",
    ]
    if any(re.search(p, query_lower) for p in research_patterns):
        return True

    # Trigger for queries mentioning specific entities/companies
    entity_patterns = [
        r"\b[A-Z][a-z]+\s+(Ltd|Limited|Inc|Corp|LLP|Pvt)\b",
        r"\bv[\./]?\s+[A-Z]",  # Case citation pattern (X v. Y)
    ]
    if any(re.search(p, user_query) for p in entity_patterns):
        return True

    # Default: use sandbox for substantive queries (8+ words)
    if len(user_query.split()) >= 8:
        return True

    return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev-commons Skill — BM25 search engine for shared development patterns
Usage: python search.py "<query>" [--domain <domain>] [-n <max_results>]
       python search.py "<query>" --overview
       python search.py --domains

Domains: flask-patterns, electron-patterns, frontend-patterns, windows-pitfalls,
         git-release, code-conventions, security-patterns, nextjs-patterns, python-patterns
"""

import argparse
import csv
import re
import sys
import io
from pathlib import Path
from math import log
from collections import defaultdict

# Force UTF-8 for stdout/stderr (Windows cp1252 default)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============ CONFIGURATION ============
DATA_DIR = Path(__file__).parent.parent / "data"
MAX_RESULTS = 5

CSV_CONFIG = {
    "flask-patterns": {
        "file": "flask-patterns.csv",
        "search_cols": ["Name", "Category", "Pattern", "Pitfall", "Keywords"],
        "output_cols": ["Name", "Category", "Pattern", "Code", "Pitfall"]
    },
    "electron-patterns": {
        "file": "electron-patterns.csv",
        "search_cols": ["Name", "Category", "Pattern", "Pitfall", "Keywords"],
        "output_cols": ["Name", "Category", "Pattern", "Code", "Pitfall"]
    },
    "frontend-patterns": {
        "file": "frontend-patterns.csv",
        "search_cols": ["Name", "Category", "Pattern", "Pitfall", "Keywords"],
        "output_cols": ["Name", "Category", "Pattern", "Code", "Pitfall"]
    },
    "windows-pitfalls": {
        "file": "windows-pitfalls.csv",
        "search_cols": ["Issue", "Cause", "Fix", "Category", "Keywords"],
        "output_cols": ["Issue", "Cause", "Fix", "Category", "Severity"]
    },
    "git-release": {
        "file": "git-release.csv",
        "search_cols": ["Name", "Category", "Steps", "Pitfall", "Keywords"],
        "output_cols": ["Name", "Category", "Steps", "Command", "Pitfall"]
    },
    "code-conventions": {
        "file": "code-conventions.csv",
        "search_cols": ["Name", "Language", "Convention", "Keywords"],
        "output_cols": ["Name", "Language", "Convention", "Example"]
    },
    "security-patterns": {
        "file": "security-patterns.csv",
        "search_cols": ["Name", "Category", "Pattern", "Severity", "Keywords"],
        "output_cols": ["Name", "Category", "Pattern", "Code", "Severity"]
    },
    "nextjs-patterns": {
        "file": "nextjs-patterns.csv",
        "search_cols": ["Name", "Category", "Pattern", "Pitfall", "Keywords"],
        "output_cols": ["Name", "Category", "Pattern", "Code", "Pitfall"]
    },
    "python-patterns": {
        "file": "python-patterns.csv",
        "search_cols": ["Name", "Category", "Pattern", "Pitfall", "Keywords"],
        "output_cols": ["Name", "Category", "Pattern", "Code", "Pitfall"]
    },
}


# ============ BM25 IMPLEMENTATION ============
class BM25:
    """BM25 ranking algorithm for text search"""

    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_lengths = []
        self.avgdl = 0
        self.idf = {}
        self.doc_freqs = defaultdict(int)
        self.N = 0

    def tokenize(self, text):
        text = re.sub(r'[^\w\s]', ' ', str(text).lower())
        return [w for w in text.split() if len(w) > 1]

    def fit(self, documents):
        self.corpus = [self.tokenize(doc) for doc in documents]
        self.N = len(self.corpus)
        if self.N == 0:
            return
        self.doc_lengths = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.N

        for doc in self.corpus:
            seen = set()
            for word in doc:
                if word not in seen:
                    self.doc_freqs[word] += 1
                    seen.add(word)

        for word, freq in self.doc_freqs.items():
            self.idf[word] = log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query):
        query_tokens = self.tokenize(query)
        scores = []

        for idx, doc in enumerate(self.corpus):
            score = 0
            doc_len = self.doc_lengths[idx]
            term_freqs = defaultdict(int)
            for word in doc:
                term_freqs[word] += 1

            for token in query_tokens:
                if token in self.idf:
                    tf = term_freqs[token]
                    idf = self.idf[token]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                    score += idf * numerator / denominator

            scores.append((idx, score))

        return sorted(scores, key=lambda x: x[1], reverse=True)


# ============ SEARCH FUNCTIONS ============
def _load_csv(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _search_csv(filepath, search_cols, output_cols, query, max_results):
    if not filepath.exists():
        return []

    data = _load_csv(filepath)
    documents = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]

    bm25 = BM25()
    bm25.fit(documents)
    ranked = bm25.score(query)

    results = []
    for idx, score in ranked[:max_results]:
        if score > 0:
            row = data[idx]
            results.append({col: row.get(col, "") for col in output_cols if col in row})

    return results


DOMAIN_KEYWORDS = {
    "flask-patterns": ["flask", "route", "jsonify", "sse", "progress", "thread", "download", "stream", "proxy",
                       "api", "endpoint", "subtitle", "cache", "yt-dlp", "ytdlp", "ffmpeg", "tkinter"],
    "electron-patterns": ["electron", "pyinstaller", "ipc", "preload", "contextbridge", "builder", "updater",
                          "browserwindow", "tray", "protocol", "browserview", "nsis", "license"],
    "frontend-patterns": ["i18n", "translation", "escape", "xss", "localstorage", "dom", "onclick", "fetch",
                          "hidden", "blob", "debounce", "dark", "theme", "responsive", "eventsource", "keyboard"],
    "windows-pitfalls": ["windows", "backslash", "path", "utf8", "encoding", "ffmpeg", "pyinstaller",
                         "tkinter", "subprocess", "phantomjs", "max_path", "file lock", "port"],
    "git-release": ["version", "semver", "changelog", "tag", "release", "publish", "deploy", "hotfix",
                    "electron-builder", "pyinstaller", "github"],
    "code-conventions": ["naming", "convention", "snake_case", "camelCase", "import", "docstring", "commit",
                         "format", "style", "table", "typescript", "react", "css", "python", "javascript"],
    "security-patterns": ["license", "aes", "encryption", "hardware", "fingerprint", "api key", "secret",
                          "hmac", "xss", "cors", "injection", "gitignore", "nextauth", "oauth", "auth"],
    "nextjs-patterns": ["nextjs", "next.js", "app router", "api route", "prisma", "zustand", "shadcn",
                        "tailwind", "oklch", "server component", "client component", "zod", "middleware"],
    "python-patterns": ["python", "flask", "fastapi", "sqlite", "threading", "logging", "argparse",
                        "requests", "daemon", "requirements", "config", "dataclass", "pathlib", "csv"],
}


def detect_domain(query):
    query_lower = query.lower()
    scores = {domain: sum(1 for kw in keywords if kw in query_lower)
              for domain, keywords in DOMAIN_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "code-conventions"


def search(query, domain=None, max_results=MAX_RESULTS):
    if domain is None:
        domain = detect_domain(query)

    config = CSV_CONFIG.get(domain)
    if not config:
        return {"error": f"Unknown domain: {domain}. Available: {', '.join(CSV_CONFIG.keys())}"}

    filepath = DATA_DIR / config["file"]
    if not filepath.exists():
        return {"error": f"File not found: {filepath}", "domain": domain}

    results = _search_csv(filepath, config["search_cols"], config["output_cols"], query, max_results)

    return {
        "domain": domain,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results
    }


def search_all(query, max_results=3):
    """Search across all domains, return top results from each."""
    all_results = {}
    for domain in CSV_CONFIG:
        result = search(query, domain, max_results)
        if result.get("count", 0) > 0:
            all_results[domain] = result
    return all_results


def format_output(result):
    if "error" in result:
        return f"Error: {result['error']}"

    output = []
    output.append(f"## dev-commons Search Results")
    output.append(f"**Domain:** {result['domain']} | **Query:** {result['query']}")
    output.append(f"**Source:** {result['file']} | **Found:** {result['count']} results\n")

    for i, row in enumerate(result['results'], 1):
        output.append(f"### Result {i}")
        for key, value in row.items():
            value_str = str(value)
            if len(value_str) > 400:
                value_str = value_str[:400] + "..."
            output.append(f"- **{key}:** {value_str}")
        output.append("")

    return "\n".join(output)


def format_overview(results):
    output = ["## dev-commons — Cross-Domain Search\n"]
    for domain, result in results.items():
        output.append(f"### [{domain.upper()}] ({result['count']} matches)")
        for i, row in enumerate(result['results'], 1):
            first_key = list(row.keys())[0]
            first_val = str(row[first_key])[:80]
            output.append(f"  {i}. {first_val}")
        output.append("")
    return "\n".join(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="dev-commons Skill Search")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--domain", "-d", choices=list(CSV_CONFIG.keys()), help="Search domain")
    parser.add_argument("--max-results", "-n", type=int, default=MAX_RESULTS, help="Max results (default: 5)")
    parser.add_argument("--overview", "-o", action="store_true", help="Search all domains")
    parser.add_argument("--domains", action="store_true", help="List available domains")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.domains:
        print("Available domains:")
        for name, config in CSV_CONFIG.items():
            filepath = DATA_DIR / config["file"]
            count = len(_load_csv(filepath)) if filepath.exists() else 0
            print(f"  {name:20s} — {config['file']:25s} ({count} entries)")
        sys.exit(0)

    if not args.query:
        parser.print_help()
        sys.exit(1)

    if args.overview:
        results = search_all(args.query, args.max_results)
        if args.json:
            import json
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(format_overview(results))
    else:
        result = search(args.query, args.domain, args.max_results)
        if args.json:
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_output(result))

#!/usr/bin/env python3
"""Vendor-neutral HTML alt-text auditor.

Reads an HTML file, finds <img> tags, flags missing/weak alt text, and suggests improvements.
Outputs a JSON report and can optionally write a patched HTML file.

Stdlib-only.
"""

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple


DEFAULT_POLICY = {
    "ignore_src_prefixes": [],
    "placeholder_alt_patterns": [
        r"^image$",
        r"^photo$",
        r"^picture$",
        r"^img$",
        r"^placeholder$",
        r"^logo$",
    ],
}


def _load_policy(path: Optional[str]) -> Dict:
    if not path:
        return dict(DEFAULT_POLICY)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    merged = dict(DEFAULT_POLICY)
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged


def _is_filename_like(s: str) -> bool:
    s2 = s.strip().lower()
    if not s2:
        return False
    # looks like a path or URL fragment
    if "/" in s2 or "\\" in s2:
        return True
    # common extensions
    return bool(re.search(r"\.(png|jpg|jpeg|gif|webp|svg)$", s2))


def _clean_basename(src: str) -> str:
    src = src.split("?")[0].split("#")[0]
    base = os.path.basename(src)
    base = re.sub(r"\.(png|jpg|jpeg|gif|webp|svg)$", "", base, flags=re.I)
    base = re.sub(r"[_\-]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


@dataclass
class ImgNode:
    startpos: int
    endpos: int
    attrs: Dict[str, str]
    context_text: str


class ImgHTMLParser(HTMLParser):
    def __init__(self, html_text: str):
        super().__init__(convert_charrefs=False)
        self._html = html_text
        self.imgs: List[ImgNode] = []
        self._text_spans: List[Tuple[int, int, str]] = []
        self._open_tags: List[str] = []

    def handle_starttag(self, tag, attrs):
        self._open_tags.append(tag)
        if tag.lower() == "img":
            # Approximate positions: HTMLParser doesn't expose offsets directly.
            # We'll later patch by string operations using src matching; keep attrs and context.
            attrs_dict = {k.lower(): (v if v is not None else "") for k, v in attrs}
            self.imgs.append(ImgNode(startpos=-1, endpos=-1, attrs=attrs_dict, context_text=""))

    def handle_endtag(self, tag):
        if self._open_tags:
            self._open_tags.pop()

    def handle_data(self, data):
        # Collect text data (used as nearby context)
        t = _normalize_space(html.unescape(data))
        if t:
            # no positions; just store sequentially
            self._text_spans.append((-1, -1, t))

    def get_context_excerpt(self) -> str:
        # simple heuristic: last few text chunks
        chunks = [t for _, _, t in self._text_spans[-3:]]
        return _normalize_space(" ".join(chunks))


def analyze(html_text: str, policy: Dict) -> Dict:
    parser = ImgHTMLParser(html_text)
    parser.feed(html_text)

    placeholder_res = [re.compile(pat, flags=re.I) for pat in policy.get("placeholder_alt_patterns", [])]
    ignore_prefixes = policy.get("ignore_src_prefixes", []) or []

    findings = []
    summary = {
        "total_images": 0,
        "missing_alt": 0,
        "empty_alt": 0,
        "placeholder_alt": 0,
        "filename_alt": 0,
        "ignored": 0,
    }

    context = parser.get_context_excerpt()

    for img in parser.imgs:
        summary["total_images"] += 1
        src = img.attrs.get("src", "")
        alt = img.attrs.get("alt")
        title = img.attrs.get("title", "")
        aria_hidden = (img.attrs.get("aria-hidden", "").lower() == "true")
        role_presentation = (img.attrs.get("role", "").lower() == "presentation")

        if any(src.startswith(p) for p in ignore_prefixes):
            summary["ignored"] += 1
            continue

        issue_types = []
        if alt is None:
            issue_types.append("missing_alt")
        else:
            if _normalize_space(alt) == "":
                issue_types.append("empty_alt")
            if any(r.match(_normalize_space(alt).lower()) for r in placeholder_res):
                issue_types.append("placeholder_alt")
            if _is_filename_like(alt):
                issue_types.append("filename_alt")

        if not issue_types:
            continue

        for it in set(issue_types):
            if it in summary:
                summary[it] += 1

        suggested = ""
        if aria_hidden or role_presentation:
            suggested = ""  # decorative
        else:
            if _normalize_space(title):
                suggested = _normalize_space(title)
            else:
                base = _clean_basename(src)
                suggested = base if base else ""
            # If we still have nothing, fall back to context.
            if not suggested and context:
                suggested = context[:80]

        findings.append(
            {
                "src": src,
                "alt": alt,
                "issue_types": sorted(set(issue_types)),
                "suggested_alt": suggested,
                "context_excerpt": context,
            }
        )

    return {"summary": summary, "findings": findings}


def patch_html(html_text: str, report: Dict) -> str:
    # Very conservative patcher: for each finding, add/replace alt attribute on first matching <img ... src="...">.
    out = html_text
    for f in report.get("findings", []):
        src = f.get("src", "")
        suggested = f.get("suggested_alt", "")
        if src == "":
            continue
        # Find a likely <img ... src="..."> occurrence.
        # Handles single/double quotes.
        pattern = re.compile(r"<img\b[^>]*\bsrc\s*=\s*([\"'])" + re.escape(src) + r"\1[^>]*>", re.I)
        m = pattern.search(out)
        if not m:
            continue
        tag = m.group(0)
        # If aria-hidden or role=presentation present and suggested empty, keep alt empty.
        new_alt = suggested
        # Ensure proper HTML escaping
        escaped_alt = html.escape(new_alt, quote=True)
        if re.search(r"\balt\s*=", tag, flags=re.I):
            tag2 = re.sub(r"\balt\s*=\s*([\"']).*?\1", f'alt="{escaped_alt}"', tag, flags=re.I)
        else:
            # insert before closing >
            tag2 = tag[:-1] + f' alt="{escaped_alt}">' 
        out = out[: m.start()] + tag2 + out[m.end() :]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, help="Path to HTML file")
    ap.add_argument("--policy", help="Optional policy JSON")
    ap.add_argument("--report-out", help="Write JSON report to this path")
    ap.add_argument("--patched-out", help="Write patched HTML to this path")
    args = ap.parse_args()

    policy = _load_policy(args.policy)

    with open(args.html, "r", encoding="utf-8") as f:
        html_text = f.read()

    report = analyze(html_text, policy)

    if args.patched_out:
        patched = patch_html(html_text, report)
        with open(args.patched_out, "w", encoding="utf-8") as f:
            f.write(patched)

    if args.report_out:
        with open(args.report_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

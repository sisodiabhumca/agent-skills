#!/usr/bin/env python3
"""docx-style-auditor

Audits a .docx file for common style consistency issues by reading OpenXML.
Uses only the Python standard library (zipfile + xml.etree).

Checks (best-effort):
- Heading level jumps (Heading1 -> Heading3)
- Empty paragraphs (runs with no text)
- Direct formatting overrides on heading paragraphs (explicit font size)

Vendor-neutral: operates on OpenXML, not a specific editor.
"""

import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}

HEADING_RE = re.compile(r"heading\s*([1-9])$", re.IGNORECASE)


def _get_text(p):
    texts = []
    for t in p.findall(".//w:t", NS):
        if t.text:
            texts.append(t.text)
    return "".join(texts).strip()


def _pstyle(p):
    el = p.find("./w:pPr/w:pStyle", NS)
    if el is None:
        return None
    return el.attrib.get(f"{{{NS['w']}}}val")


def _has_explicit_font_size(p):
    # Look for w:sz inside run properties
    return p.find(".//w:rPr/w:sz", NS) is not None


def audit(docx_path):
    with zipfile.ZipFile(docx_path, "r") as z:
        try:
            xml = z.read("word/document.xml")
        except KeyError:
            raise SystemExit("Missing word/document.xml in docx")

    root = ET.fromstring(xml)
    ps = root.findall(".//w:p", NS)

    issues = []
    empty_streak = 0
    last_heading_level = None

    for idx, p in enumerate(ps, start=1):
        style = _pstyle(p)
        text = _get_text(p)

        if not text:
            empty_streak += 1
            if empty_streak >= 3:
                issues.append(
                    {
                        "issue_type": "excess_empty_paragraphs",
                        "severity": "low",
                        "location": f"paragraph:{idx}",
                        "excerpt": "(empty)",
                    }
                )
                empty_streak = 0
        else:
            empty_streak = 0

        if style:
            m = HEADING_RE.search(style)
            if m:
                level = int(m.group(1))
                if last_heading_level is not None and level - last_heading_level >= 2:
                    issues.append(
                        {
                            "issue_type": "heading_level_jump",
                            "severity": "medium",
                            "location": f"paragraph:{idx}",
                            "excerpt": text[:120],
                        }
                    )
                last_heading_level = level

                if _has_explicit_font_size(p):
                    issues.append(
                        {
                            "issue_type": "direct_formatting_on_heading",
                            "severity": "low",
                            "location": f"paragraph:{idx}",
                            "excerpt": text[:120],
                        }
                    )

    summary = {}
    for it in issues:
        summary[it["issue_type"]] = summary.get(it["issue_type"], 0) + 1

    return {"summary": summary, "issues": issues}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    rep = audit(args.input)
    print(f"Issues found: {len(rep['issues'])}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()

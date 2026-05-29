#!/usr/bin/env python3
"""Check whether repo skills have resolvable snapshots on skills.sh."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_REPO = "sisodiabhumca/agent-skills"
DEFAULT_BASE_URL = "https://skills.sh"


class TransientDownloadError(RuntimeError):
    pass


class CollectionUnavailableError(RuntimeError):
    pass


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def repo_skill_names(skills_dir: Path) -> list[str]:
    return sorted(
        child.name
        for child in skills_dir.iterdir()
        if child.is_dir() and (child / "SKILL.md").exists()
    )


def fetch_text(url: str, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": "agent-skills-publish-check/1.0"})
    try:
        with urlopen(request, timeout=timeout, context=ssl_context()) as response:
            return response.read().decode("utf-8", "ignore")
    except URLError as original_error:
        try:
            result = subprocess.run(
                ["curl", "-fsSL", "--max-time", str(timeout), url],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"could not fetch {url}: {original_error}") from exc
        if result.returncode != 0:
            raise RuntimeError(f"could not fetch {url}: {result.stderr.strip()}")
        return result.stdout


def collection_skill_names(base_url: str, repo: str, timeout: int) -> set[str]:
    owner, repo_name = repo.split("/", 1)
    html = fetch_text(f"{base_url.rstrip('/')}/{owner}/{repo_name}", timeout)
    pattern = rf"/{re.escape(owner)}/{re.escape(repo_name)}/([a-z0-9-]+)"
    indexed = set(re.findall(pattern, html))
    if not indexed:
        raise CollectionUnavailableError(
            "skills.sh collection response did not include any skill links"
        )
    return indexed


def download_url(base_url: str, repo: str, skill: str) -> str:
    owner, repo_name = repo.split("/", 1)
    return (
        f"{base_url.rstrip('/')}/api/download/"
        f"{quote(owner)}/{quote(repo_name)}/{quote(skill)}"
    )


def has_download_snapshot(base_url: str, repo: str, skill: str, timeout: int) -> bool:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            return has_download_snapshot_once(base_url, repo, skill, timeout)
        except TransientDownloadError as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt)

    raise RuntimeError(f"could not reach skills.sh for {skill}: {last_error}") from last_error


def has_download_snapshot_once(base_url: str, repo: str, skill: str, timeout: int) -> bool:
    url = f"{download_url(base_url, repo, skill)}?verify={int(time.time())}"
    request = Request(
        url,
        headers={"User-Agent": "agent-skills-publish-check/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout, context=ssl_context()) as response:
            return response.status == 200
    except HTTPError as exc:
        if exc.code == 404:
            return False
        if exc.code == 429 or 500 <= exc.code < 600:
            raise TransientDownloadError(f"HTTP {exc.code}") from exc
        raise
    except URLError as exc:
        return has_download_snapshot_with_curl(url, skill, timeout, exc)


def has_download_snapshot_with_curl(
    url: str,
    skill: str,
    timeout: int,
    original_error: URLError,
) -> bool:
    try:
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "-o",
                os.devnull,
                "-w",
                "%{http_code}",
                "--max-time",
                str(timeout),
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"could not reach skills.sh for {skill}: {original_error}") from exc

    status = result.stdout.strip()
    if status == "200":
        return True
    if status == "404":
        return False
    if status == "000" or status == "429" or status.startswith("5"):
        raise TransientDownloadError(f"curl status {status or 'unknown'}")
    raise RuntimeError(
        f"could not reach skills.sh for {skill}: curl status {status or 'unknown'}"
    )


def missing_snapshots(
    skills: list[str],
    *,
    base_url: str,
    repo: str,
    timeout: int,
) -> list[str]:
    missing: list[str] = []
    for skill in skills:
        if not has_download_snapshot(base_url, repo, skill, timeout):
            missing.append(skill)
    return missing


def cmd_missing(args: argparse.Namespace) -> int:
    skills = repo_skill_names(Path(args.skills_dir))
    try:
        indexed = collection_skill_names(args.base_url, args.repo, args.timeout)
    except CollectionUnavailableError as exc:
        print(f"names=")
        print(f"::warning::{exc}; skipping backfill indexing", file=sys.stderr)
        return 0
    missing = [skill for skill in skills if skill not in indexed]
    print(f"names={' '.join(missing)}")
    print(
        f"skills.sh collection entries missing: {len(missing)}/{len(skills)}",
        file=sys.stderr,
    )
    if missing:
        print(", ".join(missing), file=sys.stderr)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    expected = args.skills or os.environ.get("SKILLS_TO_INDEX", "").split()
    if not expected:
        print("No skills provided for verification.")
        return 0

    missing = expected
    for attempt in range(1, args.attempts + 1):
        try:
            if args.download_api:
                missing = missing_snapshots(
                    expected,
                    base_url=args.base_url,
                    repo=args.repo,
                    timeout=args.timeout,
                )
                success_message = "skills.sh download API resolves all indexed skills."
                warning_subject = "download API did not resolve"
            else:
                indexed = collection_skill_names(args.base_url, args.repo, args.timeout)
                missing = [skill for skill in expected if skill not in indexed]
                success_message = "skills.sh collection lists all indexed skills."
                warning_subject = "collection did not show"
        except CollectionUnavailableError as exc:
            print(f"::warning::{exc}; verification skipped")
            return 0
        except RuntimeError as exc:
            print(f"::warning::skills.sh verification skipped after request error: {exc}")
            return 0
        if not missing:
            print(success_message)
            return 0
        print(f"Attempt {attempt}/{args.attempts}: still missing {', '.join(missing)}")
        if attempt != args.attempts:
            time.sleep(args.delay)

    print(
        f"::error::skills.sh {warning_subject} these skills after verification: "
        f"{', '.join(missing)}",
        file=sys.stderr,
    )
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=20)

    subparsers = parser.add_subparsers(dest="command", required=True)

    missing = subparsers.add_parser("missing")
    missing.add_argument("--skills-dir", default="skills")
    missing.set_defaults(func=cmd_missing)

    verify = subparsers.add_parser("verify")
    verify.add_argument("skills", nargs="*")
    verify.add_argument("--attempts", type=int, default=10)
    verify.add_argument("--delay", type=int, default=30)
    verify.add_argument("--download-api", action="store_true")
    verify.set_defaults(func=cmd_verify)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

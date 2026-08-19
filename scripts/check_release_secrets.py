from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


FORBIDDEN_TRACKED_PATHS = (
    re.compile(r"(^|/)\.env$", re.IGNORECASE),
    re.compile(r"\.(db|sqlite|sqlite3|log)$", re.IGNORECASE),
    re.compile(r"(^|/).*private.*\.(json|txt|md)$", re.IGNORECASE),
)
SECRET_PATTERNS = {
    "github_token": re.compile(
        r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"
    ),
    "telegram_token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider_key": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{24,}|AIza[A-Za-z0-9_-]{30,})\b"),
}


def tracked_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return [repo_root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def scan_text(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def remote_has_userinfo(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    parsed = urlsplit(result.stdout.strip())
    return parsed.scheme in {"http", "https"} and parsed.username is not None


def scan_repository(repo_root: Path) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    if remote_has_userinfo(repo_root):
        findings.append((".git/config", "credential_in_remote_url"))
    for path in tracked_files(repo_root):
        relative = path.relative_to(repo_root).as_posix()
        if any(pattern.search(relative) for pattern in FORBIDDEN_TRACKED_PATHS):
            findings.append((relative, "forbidden_tracked_private_path"))
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend((relative, category) for category in scan_text(text))
    return sorted(set(findings))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail closed on tracked release credentials.")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo_root = Path(args.repo).expanduser().resolve()
    findings = scan_repository(repo_root)
    if findings:
        for path, category in findings:
            print(f"{category}: {path}")
        raise SystemExit(1)
    print(f"release secret scan PASS: {len(tracked_files(repo_root))} tracked files")


if __name__ == "__main__":
    main()

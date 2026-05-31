import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT_ROOT / "ai-test-artifacts"
GENERATED_TESTS_DIR = PROJECT_ROOT / ".ai-generated-tests"
ALLOWED_SUFFIXES = {".py", ".js", ".html", ".css"}
IGNORED_PREFIXES = ("data/", ".github/")


def run_git_command(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def discover_changed_files(base_ref: str, head_ref: str) -> list[str]:
    output = run_git_command("diff", "--name-only", f"{base_ref}..{head_ref}")
    files = [line.strip() for line in output.splitlines() if line.strip()]
    relevant = []
    for file_path in files:
        path = Path(file_path)
        if path.suffix not in ALLOWED_SUFFIXES:
            continue
        if any(file_path.startswith(prefix) for prefix in IGNORED_PREFIXES):
            continue
        relevant.append(file_path)
    return relevant


def load_file_bundle(changed_files: list[str]) -> list[dict]:
    bundle = []
    for file_path in changed_files:
        absolute_path = PROJECT_ROOT / file_path
        if not absolute_path.exists() or not absolute_path.is_file():
            continue

        content = absolute_path.read_text(encoding="utf-8")
        bundle.append(
            {
                "path": file_path,
                "content": content[:12000],
            }
        )
    return bundle


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def call_ai_provider(prompt: str) -> dict:
    api_key = os.getenv("AI_TEST_API_KEY")
    model = os.getenv("AI_TEST_MODEL")
    api_url = os.getenv("AI_TEST_API_URL", "https://api.openai.com/v1/chat/completions")

    if not api_key or not model:
        raise RuntimeError(
            "Missing AI provider configuration. Set AI_TEST_API_KEY and AI_TEST_MODEL."
        )

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a software test generator. Generate only valid JSON. "
                    "Prefer Python unittest tests for Python files and describe manual checks "
                    "for frontend-only changes when executable browser tests would be brittle."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        api_url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AI API HTTP error {exc.code}: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"AI API network error: {exc.reason}") from exc

    parsed = json.loads(raw)
    content = parsed["choices"][0]["message"]["content"]
    cleaned = strip_code_fences(content)
    return json.loads(cleaned)


def build_prompt(base_ref: str, head_ref: str, file_bundle: list[dict]) -> str:
    return json.dumps(
        {
            "task": (
                "Generate diff-aware regression tests for the changed files in this repository. "
                "Return strict JSON with keys summary, manual_checks, and test_files. "
                "test_files must be a list of objects with path and content. "
                "If no safe executable tests can be generated for a frontend file change, "
                "return an empty test_files list and put clear manual/browser checks in manual_checks."
            ),
            "constraints": [
                "Use Python unittest for executable tests.",
                "Do not rely on external packages.",
                "Only generate tests that target changed behavior.",
                "Keep file paths under .ai-generated-tests/.",
            ],
            "base_ref": base_ref,
            "head_ref": head_ref,
            "changed_files": file_bundle,
        },
        indent=2,
    )


def write_report(report: dict) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

    (ARTIFACT_DIR / "ai_test_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    summary_lines = [
        "# AI Test Generation Report",
        "",
        f"Summary: {report.get('summary', 'No summary provided.')}",
        "",
        "## Manual Checks",
    ]
    manual_checks = report.get("manual_checks", [])
    if manual_checks:
        summary_lines.extend(f"- {item}" for item in manual_checks)
    else:
        summary_lines.append("- None")

    summary_lines.extend(["", "## Generated Test Files"])
    test_files = report.get("test_files", [])
    if test_files:
        summary_lines.extend(f"- {item['path']}" for item in test_files)
    else:
        summary_lines.append("- None")

    (ARTIFACT_DIR / "ai_test_report.md").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    for item in test_files:
        relative_path = item.get("path", "")
        if not relative_path.startswith(".ai-generated-tests/"):
            continue
        destination = PROJECT_ROOT / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(item.get("content", ""), encoding="utf-8")


def build_skip_report(message: str) -> dict:
    return {
        "summary": message,
        "manual_checks": [],
        "test_files": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    args = parser.parse_args()

    try:
        changed_files = discover_changed_files(args.base_ref, args.head_ref)
    except subprocess.CalledProcessError as exc:
        write_report(build_skip_report(f"Could not compute git diff: {exc.stderr.strip()}"))
        return 1

    if not changed_files:
        write_report(build_skip_report("No relevant code changes were detected."))
        return 0

    file_bundle = load_file_bundle(changed_files)
    prompt = build_prompt(args.base_ref, args.head_ref, file_bundle)

    try:
        report = call_ai_provider(prompt)
    except RuntimeError as exc:
        if os.getenv("AI_TEST_REQUIRED", "false").lower() == "true":
            write_report(build_skip_report(str(exc)))
            return 1
        write_report(build_skip_report(f"AI test generation skipped: {exc}"))
        return 0

    write_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

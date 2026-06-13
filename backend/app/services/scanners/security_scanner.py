"""
Security Scanner Layer — runs BEFORE LLM review.
Bandit: Python-specific AST-based security checker
Semgrep: Multi-language pattern-based scanner
Results feed into the LLM prompt so AI + static analysis compound each other.
"""
import subprocess
import json
import tempfile
import os
from typing import Dict, List, Optional


class BanditScanner:
    """Python AST security scanner."""

    def scan_files(self, files: List[Dict]) -> Dict:
        """
        Scan Python files from a PR for security issues.
        files: list of {"filename": str, "patch": str, "content": str}
        """
        py_files = [f for f in files if f.get("filename", "").endswith(".py")]
        if not py_files:
            return {"total_issues": 0, "high": 0, "medium": 0, "low": 0, "findings": []}

        findings = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in py_files:
                content = f.get("content", f.get("patch", ""))
                if not content:
                    continue
                # Strip diff markers from patch
                clean = "\n".join(
                    line[1:] if line.startswith("+") and not line.startswith("+++") else line
                    for line in content.split("\n")
                    if not line.startswith("-")
                )
                path = os.path.join(tmpdir, os.path.basename(f["filename"]))
                with open(path, "w") as fh:
                    fh.write(clean)

            result = subprocess.run(
                ["bandit", "-r", tmpdir, "-f", "json", "-q"],
                capture_output=True, text=True, timeout=60
            )

            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    raw_findings = data.get("results", [])
                    for r in raw_findings:
                        findings.append({
                            "tool": "bandit",
                            "severity": r.get("issue_severity", "").lower(),
                            "confidence": r.get("issue_confidence", "").lower(),
                            "file": r.get("filename", "").replace(tmpdir + "/", ""),
                            "line": r.get("line_number"),
                            "title": r.get("test_id", "") + ": " + r.get("issue_text", ""),
                            "cwe": r.get("issue_cwe", {}).get("id"),
                            "more_info": r.get("more_info", ""),
                        })
                except json.JSONDecodeError:
                    pass

        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "total_issues": len(findings),
            "high": severity_counts["high"],
            "medium": severity_counts["medium"],
            "low": severity_counts["low"],
            "findings": findings,
        }


class SemgrepScanner:
    """Multi-language pattern-based scanner."""

    # Built-in rulesets that cover common issues
    RULESETS = [
        "p/owasp-top-ten",
        "p/secrets",
        "p/security-audit",
    ]

    def scan_files(self, files: List[Dict], language: Optional[str] = None) -> Dict:
        """Scan changed files using Semgrep OWASP + secrets rulesets."""
        if not files:
            return {"total_findings": 0, "critical": 0, "high": 0, "findings": []}

        findings = []
        with tempfile.TemporaryDirectory() as tmpdir:
            written = []
            for f in files:
                filename = f.get("filename", "")
                content = f.get("content", f.get("patch", ""))
                if not content or not filename:
                    continue
                # Strip diff markers
                clean = "\n".join(
                    line[1:] if line.startswith("+") and not line.startswith("+++") else line
                    for line in content.split("\n")
                    if not line.startswith("-")
                )
                safe_name = filename.replace("/", "_")
                path = os.path.join(tmpdir, safe_name)
                with open(path, "w", errors="ignore") as fh:
                    fh.write(clean)
                written.append(path)

            if not written:
                return {"total_findings": 0, "critical": 0, "high": 0, "findings": []}

            cmd = [
                "semgrep",
                "--config", "p/owasp-top-ten",
                "--config", "p/secrets",
                "--json",
                "--quiet",
                "--timeout", "30",
                tmpdir,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for r in data.get("results", []):
                        sev = r.get("extra", {}).get("severity", "INFO").lower()
                        findings.append({
                            "tool": "semgrep",
                            "severity": sev,
                            "file": r.get("path", "").replace(tmpdir + "/", ""),
                            "line": r.get("start", {}).get("line"),
                            "rule_id": r.get("check_id", ""),
                            "title": r.get("extra", {}).get("message", ""),
                            "cwe": r.get("extra", {}).get("metadata", {}).get("cwe", []),
                            "owasp": r.get("extra", {}).get("metadata", {}).get("owasp", []),
                        })
                except json.JSONDecodeError:
                    pass

        critical = sum(1 for f in findings if f.get("severity") in ("error", "critical"))
        high = sum(1 for f in findings if f.get("severity") == "warning")

        return {
            "total_findings": len(findings),
            "critical": critical,
            "high": high,
            "findings": findings,
        }


class SecurityScannerService:
    """Orchestrates both scanners and merges output."""

    def __init__(self):
        self.bandit = BanditScanner()
        self.semgrep = SemgrepScanner()

    def scan(self, files: List[Dict], language: Optional[str] = None) -> Dict:
        """
        Run all scanners on the PR files.
        Returns merged scan_results dict that gets injected into LLM prompt.
        """
        bandit_result = {"total_issues": 0, "high": 0, "medium": 0, "low": 0, "findings": []}
        semgrep_result = {"total_findings": 0, "critical": 0, "high": 0, "findings": []}

        try:
            bandit_result = self.bandit.scan_files(files)
        except Exception as e:
            print(f"Bandit scan failed: {e}")

        try:
            semgrep_result = self.semgrep.scan_files(files, language)
        except Exception as e:
            print(f"Semgrep scan failed: {e}")

        # Unified high-severity findings for display
        all_critical = []
        for f in bandit_result.get("findings", []):
            if f.get("severity") == "high":
                all_critical.append({
                    "tool": "bandit",
                    "severity": "critical",
                    "file": f.get("file"),
                    "line": f.get("line"),
                    "title": f.get("title"),
                })
        for f in semgrep_result.get("findings", []):
            if f.get("severity") in ("error", "critical"):
                all_critical.append({
                    "tool": "semgrep",
                    "severity": "critical",
                    "file": f.get("file"),
                    "line": f.get("line"),
                    "title": f.get("title"),
                    "rule": f.get("rule_id"),
                })

        return {
            "bandit": bandit_result,
            "semgrep": semgrep_result,
            "critical_findings": all_critical,
            "total_static_issues": bandit_result["total_issues"] + semgrep_result["total_findings"],
        }

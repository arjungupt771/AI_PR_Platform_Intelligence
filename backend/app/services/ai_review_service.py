"""
Multi-LLM Review Engine
Primary: Groq (llama-3.3-70b-versatile) — fast, free-tier friendly
Optional: OpenAI GPT-4o, Google Gemini 1.5 Flash
Produces a consensus score + per-model breakdown.
"""
import json
import time
import asyncio
from typing import List, Dict, Optional, Tuple
from app.core.config import settings
from app.services.qdrant_service import QdrantService

REVIEW_SYSTEM_PROMPT = """You are an elite senior software engineer performing a thorough code review.
Respond ONLY with a valid JSON object — no markdown, no preamble, no backticks.

{
  "summary": "2-3 sentence executive summary",
  "overall_score": <float 0.0-10.0>,
  "issues": [
    {
      "severity": "<critical|warning|suggestion|info>",
      "file": "<filename>",
      "line": <optional int>,
      "title": "<short title>",
      "description": "<detailed explanation>",
      "suggestion": "<specific fix>"
    }
  ],
  "suggestions": ["<general suggestion>"],
  "security_flags": ["<security concern>"],
  "metrics": {
    "complexity": "<low|medium|high>",
    "test_coverage_hint": "<good|missing|partial>",
    "documentation": "<good|missing|partial>",
    "breaking_changes": <true|false>
  }
}

Scoring: 9-10 excellent, 7-8 good, 5-6 fair, 3-4 poor, 1-2 critical problems."""


class GroqReviewer:
    """Primary reviewer — Groq API (llama-3.3-70b-versatile)."""

    def __init__(self):
        from groq import Groq
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"
        self.provider = "groq"

    def review(self, prompt: str) -> Tuple[Dict, int, int]:
        start = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.1,
        )
        latency = int((time.time() - start) * 1000)
        raw = resp.choices[0].message.content
        tokens = resp.usage.total_tokens if resp.usage else 0
        return _parse_review(raw), tokens, latency

    def chat(self, system: str, messages: List[Dict]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=1024,
            temperature=0.3,
        )
        return resp.choices[0].message.content


class OpenAIReviewer:
    """Optional reviewer — OpenAI GPT-4o."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"
        self.provider = "openai"

    def review(self, prompt: str) -> Tuple[Dict, int, int]:
        start = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        latency = int((time.time() - start) * 1000)
        raw = resp.choices[0].message.content
        tokens = resp.usage.total_tokens if resp.usage else 0
        return _parse_review(raw), tokens, latency


class GeminiReviewer:
    """Optional reviewer — Google Gemini 1.5 Flash."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=REVIEW_SYSTEM_PROMPT,
        )
        self.provider = "gemini"
        self.model_name = "gemini-1.5-flash"

    def review(self, prompt: str) -> Tuple[Dict, int, int]:
        start = time.time()
        resp = self.model.generate_content(prompt)
        latency = int((time.time() - start) * 1000)
        raw = resp.text
        tokens = 0
        if hasattr(resp, "usage_metadata"):
            tokens = getattr(resp.usage_metadata, "total_token_count", 0)
        return _parse_review(raw), tokens, latency


def _parse_review(raw: str) -> Dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception:
        return {
            "summary": "Parse error — raw response stored.",
            "overall_score": None,
            "issues": [],
            "suggestions": [],
            "security_flags": [],
            "metrics": {},
        }


def _build_consensus(llm_results: List[Dict]) -> Dict:
    """
    Merge multiple LLM reviews into a consensus result.
    - Issues that appear in 2+ reviews get higher confidence
    - Score = weighted average (Groq 40%, OpenAI 35%, Gemini 25%)
    - Consensus score = % of models that flagged ≥1 critical issue
    """
    weights = {"groq": 0.4, "openai": 0.35, "gemini": 0.25}
    scores = []
    total_weight = 0
    all_issues = []
    all_security = set()
    all_suggestions = []

    for r in llm_results:
        provider = r.get("provider", "groq")
        w = weights.get(provider, 0.33)
        score = r.get("data", {}).get("overall_score")
        if score is not None:
            scores.append(score * w)
            total_weight += w
        for issue in r.get("data", {}).get("issues", []):
            issue["source_model"] = r.get("model", "unknown")
            all_issues.append(issue)
        for sf in r.get("data", {}).get("security_flags", []):
            all_security.add(sf)
        all_suggestions.extend(r.get("data", {}).get("suggestions", []))

    consensus_score = round(sum(scores) / total_weight, 2) if total_weight > 0 else None

    # Deduplicate issues by file+title similarity
    deduped = _deduplicate_issues(all_issues, llm_results)

    # Agreement % = how many models flagged critical issues
    models_with_critical = sum(
        1 for r in llm_results
        if any(i.get("severity") == "critical" for i in r.get("data", {}).get("issues", []))
    )
    agreement_pct = round((models_with_critical / len(llm_results)) * 100) if llm_results else 0

    # Build per-model summary for UI
    model_breakdown = []
    for r in llm_results:
        d = r.get("data", {})
        model_breakdown.append({
            "provider": r.get("provider"),
            "model": r.get("model"),
            "score": d.get("overall_score"),
            "issue_count": len(d.get("issues", [])),
            "critical_count": sum(1 for i in d.get("issues", []) if i.get("severity") == "critical"),
            "security_flags": len(d.get("security_flags", [])),
            "latency_ms": r.get("latency_ms", 0),
        })

    # Use best summary (from highest-scoring model)
    best = max(llm_results, key=lambda r: r.get("data", {}).get("overall_score") or 0)
    summary = best.get("data", {}).get("summary", "")

    # Merge metrics
    metrics = best.get("data", {}).get("metrics", {})

    return {
        "summary": summary,
        "overall_score": consensus_score,
        "consensus_agreement": agreement_pct,
        "model_breakdown": model_breakdown,
        "issues": deduped,
        "suggestions": list(dict.fromkeys(all_suggestions))[:10],
        "security_flags": list(all_security),
        "metrics": metrics,
        "models_used": [r.get("model") for r in llm_results],
    }


def _deduplicate_issues(issues: List[Dict], llm_results: List[Dict]) -> List[Dict]:
    """
    Mark issues that multiple models agreed on with higher confidence.
    Simple dedup: same file + similar severity = same issue.
    """
    seen: Dict[str, Dict] = {}
    for issue in issues:
        key = f"{issue.get('file','')}-{issue.get('severity','')}-{issue.get('title','')[:30]}"
        if key in seen:
            seen[key]["confirmed_by"] = seen[key].get("confirmed_by", 1) + 1
        else:
            issue["confirmed_by"] = 1
            seen[key] = issue

    # Sort: most confirmed first, then by severity
    severity_order = {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}
    return sorted(
        seen.values(),
        key=lambda i: (-(i.get("confirmed_by", 1)), severity_order.get(i.get("severity", "info"), 4))
    )


class AIReviewService:
    """Orchestrates multi-LLM reviews with RAG context injection."""

    def __init__(self):
        self.qdrant = QdrantService()
        self._groq = None
        self._openai = None
        self._gemini = None

    def _get_groq(self) -> GroqReviewer:
        if not self._groq:
            self._groq = GroqReviewer()
        return self._groq

    def _get_openai(self) -> Optional[OpenAIReviewer]:
        if not settings.openai_api_key:
            return None
        if not self._openai:
            try:
                self._openai = OpenAIReviewer()
            except Exception:
                return None
        return self._openai

    def _get_gemini(self) -> Optional[GeminiReviewer]:
        if not settings.google_api_key:
            return None
        if not self._gemini:
            try:
                self._gemini = GeminiReviewer()
            except Exception:
                return None
        return self._gemini

    async def review_pull_request(
        self,
        diff: str,
        files: List[Dict],
        repo_full_name: str,
        pr_title: str,
        pr_description: Optional[str] = None,
        repo_id: Optional[int] = None,
        scan_results: Optional[Dict] = None,
    ) -> Dict:
        # 1. RAG: get relevant context
        context_chunks = []
        if repo_id:
            context_chunks = await self.qdrant.search_relevant_context(
                repo_id=repo_id,
                query=f"{pr_title} {pr_description or ''} {self._extract_key_terms(diff)}",
                limit=8,
            )

        # 2. Build prompt
        prompt = self._build_prompt(
            diff=self._truncate_diff(diff, 40000),
            files=files,
            pr_title=pr_title,
            pr_description=pr_description,
            context_chunks=context_chunks,
            scan_results=scan_results,
        )

        # 3. Run all available LLMs (Groq always runs; others if keys present)
        llm_results = []
        loop = asyncio.get_event_loop()

        # Groq — primary, always runs
        try:
            data, tokens, latency = await loop.run_in_executor(
                None, self._get_groq().review, prompt
            )
            llm_results.append({
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "data": data,
                "tokens": tokens,
                "latency_ms": latency,
            })
        except Exception as e:
            print(f"Groq review failed: {e}")

        # OpenAI — optional
        oai = self._get_openai()
        if oai:
            try:
                data, tokens, latency = await loop.run_in_executor(
                    None, oai.review, prompt
                )
                llm_results.append({
                    "provider": "openai",
                    "model": "gpt-4o",
                    "data": data,
                    "tokens": tokens,
                    "latency_ms": latency,
                })
            except Exception as e:
                print(f"OpenAI review failed: {e}")

        # Gemini — optional
        gem = self._get_gemini()
        if gem:
            try:
                data, tokens, latency = await loop.run_in_executor(
                    None, gem.review, prompt
                )
                llm_results.append({
                    "provider": "gemini",
                    "model": "gemini-1.5-flash",
                    "data": data,
                    "tokens": tokens,
                    "latency_ms": latency,
                })
            except Exception as e:
                print(f"Gemini review failed: {e}")

        if not llm_results:
            raise RuntimeError("All LLM reviewers failed")

        # 4. Consensus
        consensus = _build_consensus(llm_results)
        consensus["llm_results"] = llm_results
        consensus["tokens_used"] = sum(r.get("tokens", 0) for r in llm_results)
        return consensus

    async def chat_about_pr(
        self,
        pr_diff: str,
        review_summary: Optional[str],
        conversation_history: List[Dict],
        user_message: str,
        repo_id: Optional[int] = None,
    ) -> str:
        context_chunks = []
        if repo_id:
            context_chunks = await self.qdrant.search_relevant_context(
                repo_id=repo_id, query=user_message, limit=4
            )

        system = f"""You are a senior software engineer assistant for a PR review platform.
You have access to the PR diff, previous review summary, and codebase context.
Be specific, technical, and reference exact code when answering.

PR Diff (truncated):
```
{self._truncate_diff(pr_diff, 8000)}
```

Review Summary: {review_summary or "No review yet."}

Codebase Context:
{self._format_context(context_chunks)}"""

        messages = conversation_history[-20:] + [{"role": "user", "content": user_message}]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._get_groq().chat, system, messages
        )

    def _build_prompt(self, diff, files, pr_title, pr_description, context_chunks, scan_results=None):
        files_summary = "\n".join(
            f"- {f['filename']} (+{f['additions']} -{f['deletions']})" for f in files[:20]
        )
        context_section = self._format_context(context_chunks)
        scan_section = ""
        if scan_results:
            bandit = scan_results.get("bandit", {})
            semgrep = scan_results.get("semgrep", {})
            scan_section = f"""
**Static Analysis Results (pre-LLM scan):**
- Bandit: {bandit.get('total_issues', 0)} issues ({bandit.get('high', 0)} high, {bandit.get('medium', 0)} medium)
- Semgrep: {semgrep.get('total_findings', 0)} findings
Consider these when scoring — static tools caught these already.
"""
        return f"""Review this pull request:

**Title:** {pr_title}
**Description:** {pr_description or "No description."}

**Files Changed:**
{files_summary}
{scan_section}
**Codebase Context (semantic memory):**
{context_section}

**Diff:**
```diff
{diff}
```

Return the JSON review object."""

    def _format_context(self, chunks: List[Dict]) -> str:
        if not chunks:
            return "No additional context."
        return "\n\n".join(
            f"File: {c.get('file_path','?')}\n```\n{c.get('content','')[:400]}\n```"
            for c in chunks
        )

    def _truncate_diff(self, diff: str, max_chars: int) -> str:
        if len(diff) <= max_chars:
            return diff
        h = max_chars // 2
        return diff[:h] + "\n\n... [truncated] ...\n\n" + diff[-h:]

    def _extract_key_terms(self, diff: str) -> str:
        import re
        terms = []
        for pat in [r"def (\w+)", r"class (\w+)", r"function (\w+)", r"const (\w+)\s*="]:
            terms.extend(re.findall(pat, diff)[:5])
        return " ".join(set(terms))

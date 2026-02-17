from __future__ import annotations
from dataclasses import dataclass

INJECTION_MARKERS=("ignore previous instructions","reveal the system prompt","jailbreak","disable safety","override policy","exfiltrate")

@dataclass(frozen=True)
class SecurityScanResult:
    safe: bool
    details: str

def detect_prompt_injection(user_content: str) -> SecurityScanResult:
    lower=user_content.lower(); m=[x for x in INJECTION_MARKERS if x in lower]
    return SecurityScanResult(False,f"Potential prompt injection markers found: {', '.join(m)}") if m else SecurityScanResult(True,"No prompt-injection signatures found")

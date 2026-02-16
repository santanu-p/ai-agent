from __future__ import annotations
import json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from .gates import gate_allowed_modifications, gate_canary_threshold, gate_deterministic_replay, gate_forbidden_apis, gate_performance_budget, gate_save_compatibility, gate_security_prompt_injection, gate_static_checks
from .models import AIPolicy, EnforcementReport, GateResult, PatchContext

REQUIRED_GATES=("static_lint_type_checks","deterministic_replay_validation","backward_save_load_compatibility","canary_telemetry_threshold")

class AIPatchEnforcer:
    def __init__(self, policy:AIPolicy, quarantine_dir:Path|None=None) -> None:
        self.policy=policy; self.quarantine_dir=quarantine_dir or Path('.ai_policy/quarantine')

    def enforce(self, ctx:PatchContext)->EnforcementReport:
        results=[
            gate_allowed_modifications(self.policy,ctx),
            gate_forbidden_apis(self.policy,ctx),
            gate_security_prompt_injection(ctx),
            gate_performance_budget(self.policy,ctx),
            gate_static_checks(self.policy,ctx),
            gate_deterministic_replay(self.policy,ctx),
            gate_save_compatibility(self.policy,ctx),
            gate_canary_threshold(self.policy,ctx),
        ]
        status={r.gate:r.passed for r in results}
        all_ok=all(status.get(g,False) for g in REQUIRED_GATES) and all(r.passed for r in results)
        if all_ok: return EnforcementReport(ctx.patch_id,False,results)
        self._auto_revert(ctx.repo_path)
        q=self._write_quarantine(ctx.patch_id,results)
        return EnforcementReport(ctx.patch_id,True,results,q)

    def _auto_revert(self, repo_path:Path)->None:
        subprocess.run('git reset --hard HEAD',cwd=repo_path,shell=True,check=False,capture_output=True)

    def _write_quarantine(self, patch_id:str, results:list[GateResult])->Path:
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        p=self.quarantine_dir/f'{patch_id}.json'
        p.write_text(json.dumps({"patch_id":patch_id,"timestamp":datetime.now(timezone.utc).isoformat(),"quarantined":True,"results":[{"gate":r.gate,"passed":r.passed,"details":r.details} for r in results]},indent=2,sort_keys=True),encoding='utf-8')
        return p

from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
from .models import AIPolicy, GateResult, PatchContext
from .security import detect_prompt_injection

def gate_allowed_modifications(policy:AIPolicy,ctx:PatchContext)->GateResult:
    bad_files=[p for p in ctx.changed_files if not any(p==pre or p.startswith(f"{pre}/") for pre in policy.allowed_path_prefixes)]
    bad_domains=[d for d in ctx.changed_domains if d not in policy.allowed_config_domains]
    if bad_files or bad_domains:
        msg=[]
        if bad_files: msg.append(f"Disallowed file changes: {', '.join(sorted(bad_files))}")
        if bad_domains: msg.append(f"Disallowed config domains: {', '.join(sorted(bad_domains))}")
        return GateResult("allowed_modification_policy",False," | ".join(msg))
    return GateResult("allowed_modification_policy",True,"All file and config domain changes are authorized")

def gate_forbidden_apis(policy:AIPolicy,ctx:PatchContext)->GateResult:
    v=[]
    for rel in ctx.changed_files:
        p=ctx.repo_path/rel
        if p.exists() and p.is_file():
            c=p.read_text(encoding="utf-8",errors="ignore")
            for api in policy.forbidden_apis:
                if api in c: v.append(f"{rel}: {api}")
    return GateResult("forbidden_api_policy",False,f"Forbidden API usage: {', '.join(v)}") if v else GateResult("forbidden_api_policy",True,"No forbidden APIs detected in changed files")

def gate_security_prompt_injection(ctx:PatchContext)->GateResult:
    issues=[detect_prompt_injection(b).details for b in ctx.user_content_blobs if not detect_prompt_injection(b).safe]
    return GateResult("prompt_injection_security",False," | ".join(issues)) if issues else GateResult("prompt_injection_security",True,"User-content prompt injection scan passed")

def _run(cmds:tuple[str,...], cwd:Path)->list[str]:
    fails=[]
    for cmd in cmds:
        p=subprocess.run(cmd,cwd=cwd,shell=True,text=True,capture_output=True)
        if p.returncode!=0: fails.append(f"`{cmd}` failed: {p.stderr.strip() or p.stdout.strip()}")
    return fails

def gate_static_checks(policy:AIPolicy,ctx:PatchContext)->GateResult:
    f=_run(policy.lint_commands+policy.typecheck_commands,ctx.repo_path)
    return GateResult("static_lint_type_checks",False," | ".join(f)) if f else GateResult("static_lint_type_checks",True,"Lint and typecheck commands succeeded")

def gate_deterministic_replay(policy:AIPolicy,ctx:PatchContext)->GateResult:
    if ctx.replay_runner is None: return GateResult("deterministic_replay_validation",False,"No replay runner provided")
    d1=hashlib.sha256(ctx.replay_runner(policy.replay_seed).encode()).hexdigest(); d2=hashlib.sha256(ctx.replay_runner(policy.replay_seed).encode()).hexdigest()
    return GateResult("deterministic_replay_validation",False,f"Replay digests differ ({d1[:12]} != {d2[:12]})") if d1!=d2 else GateResult("deterministic_replay_validation",True,f"Replay deterministic digest {d1[:12]}")

def gate_save_compatibility(policy:AIPolicy,ctx:PatchContext)->GateResult:
    if not ctx.save_snapshots: return GateResult("backward_save_load_compatibility",False,"No save snapshots were supplied")
    min_v,max_v=policy.save_compatibility.allowed_version_range; req=set(policy.save_compatibility.required_keys)
    for i,s in enumerate(ctx.save_snapshots):
        v=s.get("version")
        if not isinstance(v,int) or not(min_v<=v<=max_v): return GateResult("backward_save_load_compatibility",False,f"Snapshot {i} has unsupported version {v}; expected {min_v}-{max_v}")
        miss=req.difference(s.keys())
        if miss: return GateResult("backward_save_load_compatibility",False,f"Snapshot {i} missing required keys: {', '.join(sorted(miss))}")
        try: json.loads(json.dumps(s,sort_keys=True))
        except Exception as exc: return GateResult("backward_save_load_compatibility",False,f"Snapshot {i} failed round-trip: {exc}")
    return GateResult("backward_save_load_compatibility",True,"Save snapshots are backward compatible")

def gate_performance_budget(policy:AIPolicy,ctx:PatchContext)->GateResult:
    frame=ctx.performance_metrics.get("frame_time_ms_p95"); mem=ctx.performance_metrics.get("memory_mb_peak")
    if frame is None or mem is None: return GateResult("performance_budget",False,"Missing frame_time_ms_p95 or memory_mb_peak metrics")
    if frame>policy.performance_budget.frame_time_ms_p95_max: return GateResult("performance_budget",False,f"Frame budget exceeded ({frame} > {policy.performance_budget.frame_time_ms_p95_max})")
    if mem>policy.performance_budget.memory_mb_peak_max: return GateResult("performance_budget",False,f"Memory budget exceeded ({mem} > {policy.performance_budget.memory_mb_peak_max})")
    return GateResult("performance_budget",True,"Frame-time and memory budgets satisfied")

def gate_canary_threshold(policy:AIPolicy,ctx:PatchContext)->GateResult:
    m=ctx.canary_metrics; t=policy.canary_thresholds
    missing=[k for k in ("error_rate","p95_latency_ms","timeout_rate") if k not in m]
    if missing: return GateResult("canary_telemetry_threshold",False,f"Missing canary metrics: {', '.join(missing)}")
    if m["error_rate"]>t.max_error_rate: return GateResult("canary_telemetry_threshold",False,f"Canary error rate {m['error_rate']} exceeds {t.max_error_rate}")
    if m["p95_latency_ms"]>t.max_p95_latency_ms: return GateResult("canary_telemetry_threshold",False,f"Canary p95 latency {m['p95_latency_ms']} exceeds {t.max_p95_latency_ms}")
    if m["timeout_rate"]>t.max_timeout_rate: return GateResult("canary_telemetry_threshold",False,f"Canary timeout rate {m['timeout_rate']} exceeds {t.max_timeout_rate}")
    return GateResult("canary_telemetry_threshold",True,"Canary telemetry thresholds satisfied")

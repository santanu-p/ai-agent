#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from ai.policy import PatchContext, enforce_patch


def _load(path:str)->dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))

def main()->int:
    policy=_load('ai/policy/default_policy.json')
    raw=_load('ai/policy/sample_patch_context.json')
    ctx=PatchContext(
        patch_id=raw['patch_id'], repo_path=Path(raw.get('repo_path','.')).resolve(),
        changed_files=tuple(raw.get('changed_files',[])), changed_domains=tuple(raw.get('changed_domains',[])),
        user_content_blobs=tuple(raw.get('user_content_blobs',[])), performance_metrics=raw.get('performance_metrics',{}),
        canary_metrics=raw.get('canary_metrics',{}), save_snapshots=tuple(raw.get('save_snapshots',[])),
        replay_runner=lambda seed: f'deterministic::{seed}'
    )
    rep=enforce_patch(policy,ctx)
    print(json.dumps({"patch_id":rep.patch_id,"quarantined":rep.quarantined,"quarantine_record":str(rep.quarantine_record) if rep.quarantine_record else None,"gate_results":[{"gate":g.gate,"passed":g.passed,"details":g.details} for g in rep.gate_results]},indent=2))
    return 1 if rep.quarantined else 0

if __name__=='__main__':
    raise SystemExit(main())

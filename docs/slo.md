# SLO Targets

## Availability

- Target: `99.9%` monthly for control plane and runtime-plane entrypoints.
- Error budget: ~43.2 minutes monthly downtime.

## Latency

- Interactive execution target: `p95 < 15s`.
- Policy simulation target: `p95 < 2s`.

## Recovery

- `RPO 5m` for trace + memory event streams.
- `RTO 30m` for region failover.

## Learning effectiveness

- Minimum 4-week rolling reduction in recurring failure class rate.
- Auto-upgrade patch promotion only if benchmark composite improves.


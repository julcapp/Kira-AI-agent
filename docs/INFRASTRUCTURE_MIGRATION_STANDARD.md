# Infrastructure portability and V2P migration

Status: architectural requirements; implementation and restore drills pending. Approved direction: migrate from Hyper-V guest to clean Ubuntu Server on bare metal without dependence on hardware or hosting provider.

## P0 — protect data before any change
- Inventory repositories, image versions, persistent volumes, databases, user records, tasks, scheduler state, agent registry, prompts, skills, documents, media, integration state, access policies and audit logs.
- Store code and sanitized configuration templates in Git; never commit secrets, personal data, live databases, private keys or deployment-specific addresses.
- Use consistent database-native backups (SQLite online backup API; PostgreSQL pg_dump or validated physical backup after migration). Encrypt off-host archives; keep keys separately; checksum and test restores.
- Target 3-2-1-1-0 backup policy: three copies, two storage types, one offsite, one isolated/immutable, zero verified restore errors. Proposed cadence: hourly DB (48h), daily data/config (30d), weekly full (12 weeks), monthly archive (12 months); adjust for privacy and retention obligations. Weekly isolated restore drill. Proposed RPO 1h, RTO 4h, not yet demonstrated.
- Export Hyper-V VM to independent storage and verify import; if reusing host hardware, protect ALL guest VMs before any destructive operation. Never erase original system before validated recovery.

## P1 — portable deployment
- Pin supported Ubuntu/Docker and application dependency versions; use Compose, repeatable provisioning, explicit volumes and environment schemas. Avoid dependence on MAC, fixed disk device names or absolute provider IPs. Keep sensitive configuration encrypted outside Git.
- Stable DNS names and reverse proxy; TLS and authentication must pass checks before exposing services. Preserve logical service identity on migration.
- Gateway Manager: provider-neutral registry with endpoint, port, host-key fingerprint, key reference, role, health and audit state. Selective outbound proxy only for authorized services; no global host routing changes by default. Validate new endpoint before switching; keep previous endpoint for rollback. Do not share private keys across machines. Separate inbound proxy from outbound egress. Provider availability/terms must be respected.
- Backup, Migration, Recovery, Monitoring and Deployment capabilities belong to a shared infrastructure control plane. Privileged operations require narrowly scoped authorization and logging; do not expose root shell through ordinary application APIs.

## P2 — V2P cutover
1. Inventory hardware, disk/RAID, network, boot and drivers; provision clean supported Ubuntu on new physical hardware. Keep original VM operating.
2. Deploy pinned code/images; restore encrypted configuration and data to isolated target. Disable production webhooks, outbound messaging, schedulers and payment actions in clone; use separate credentials and test endpoints.
3. Validate integrity, record counts, user authorization, agent/skill registry, API health, scheduler behavior, integration and load tests. Verify restart and backup restore.
4. Lower DNS TTL ahead of planned cutover; establish maintenance window; quiesce writes and schedulers on source; take final consistent backup and verify checksum; restore target and verify.
5. Enable single production writer/scheduler, switch DNS and webhooks, check TLS and external reachability. Avoid split brain. Monitor errors and data integrity.
6. Rollback on failed acceptance: stop target writes, reconcile any new data before restoring source, revert DNS/webhooks and verify. Keep source and backups for at least 14 days of stable operation before approved retirement.

## Acceptance gates
- No loss of committed records within agreed RPO; measured restore time; successful restart; authenticated API and webhook checks; no duplicate jobs; valid HTTPS; off-host backup verified; rollback exercised.
- Existing production must not be interrupted during preparation. Actual migration requires hardware readiness and verified backups. This document does not claim implementation or operational readiness.

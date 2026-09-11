# Self-managed storage, capacity and migration

## Goal
The scanner must never assume a fixed disk size. At startup and periodically it discovers filesystem capacity, database size, ingestion rate and forecasted storage exhaustion. It automatically keeps data quality within configured safety limits and asks for more storage only after safe cleanup/compression options are exhausted.

## Storage classes
- HOT: live state, recent order books and ticks required for current detectors.
- WARM: recent signal snapshots and replay material.
- COLD: compressed historical event archives.
- LEARNED: compact signal outcomes, feature statistics, calibration and configuration versions. Never delete these merely because raw data expires.

## Adaptive capacity policy
1. Discover mounted filesystems and free space at boot.
2. Keep a configurable emergency reserve (percentage and minimum GB).
3. Estimate bytes/day separately for each dataset class.
4. Forecast days-to-critical-space using a rolling ingestion window.
5. Compress and compact cold data before deleting it.
6. Delete expired raw data according to retention policy.
7. Reduce optional sampling/retention only when required; never silently disable safety-critical market feeds.
8. If the forecast remains below the safety horizon, raise a storage expansion event containing current capacity, growth rate, projected exhaustion date and recommended additional capacity.

The recommendation is calculated from actual capacity and growth, not from a hard-coded 100/200 GB assumption.

## Automatic use of newly added disks
The service periodically discovers new mounted filesystems. A disk is eligible only if its filesystem is writable, has sufficient free space and is not an OS/system-critical mount. The storage manager can assign eligible data directories using a manifest such as:

```yaml
storage:
  auto_discover: true
  minimum_free_gb: 10
  emergency_reserve_percent: 15
  prefer_mounts: []
  classes:
    hot: auto
    warm: auto
    cold: auto
```

New storage is added to the storage pool/index and new cold partitions are placed there. Existing data is migrated gradually in the background; the live market-ingestion process is not stopped merely because a disk was added. The manager records filesystem UUIDs so a path rename does not create duplicate datasets.

## Migration to another server
The project is designed to be portable. Configuration is separated from secrets, persistent data lives in explicit volumes, and the database/schema has versioned migrations.

Target workflow:

```text
New Ubuntu server
  -> install Docker
  -> clone repository
  -> run bootstrap
  -> restore encrypted backup/manifest
  -> discover disks
  -> validate feeds
  -> start scanner
```

A future one-command installer should perform preflight checks, detect CPU/RAM/disk/network, create directories, pull the pinned images, initialize the schema, restore data if requested, and run health checks. It must not copy secrets into Git.

## Learning vs deletion
Raw ticks and full depth snapshots are expendable after their retention period when equivalent signal/replay statistics have been materialized. Signal events retain the exact configuration version, detector version, timestamps, prices, liquidity and outcome horizons needed to audit historical decisions. Learned statistics are compact and retained much longer.

## No fake self-learning
The optimizer must not modify production thresholds merely because one backtest looks better. Candidate changes require minimum sample size, walk-forward/out-of-sample evaluation, comparison with the current configuration, and a rollbackable version. The UI should explain why a candidate was promoted or rejected.

## Safety
This system is research/alerting software for manual spot trading. It does not place orders. Storage automation must never delete secrets, configuration history, signal outcomes, or the only copy of a recoverable database without a verified backup policy.

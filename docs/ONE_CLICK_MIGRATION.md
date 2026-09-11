# One-click migration contract

The deployment should expose a single bootstrap entry point for a fresh Ubuntu host. The installer is expected to:

1. Verify Docker/Compose, filesystem permissions, CPU/RAM/disk and network.
2. Discover all eligible mounted data disks.
3. Create a stable directory layout and storage manifest using filesystem UUIDs.
4. Pull pinned application images/build the application.
5. Initialize or migrate the database schema.
6. Restore a selected backup/portable archive when supplied.
7. Validate exchange connectivity and clock synchronization.
8. Start services with health checks and automatic restart policies.
9. Rebalance cold-data partitions onto newly discovered capacity.
10. Print the dashboard address and a concise health report.

Secrets are supplied separately through environment variables or a secret manager and are never committed to Git.

## Portability requirement
Never assume `/dev/sda`, a particular disk count, a fixed IP, or a fixed hostname. Persist logical data identities and filesystem UUIDs. A server with 100 GB, 200 GB, 1 TB, or multiple disks must use the same application configuration and adapt its retention/storage plan from observed capacity.

## Backup requirement
A migration must support an integrity-checked backup containing database data, configuration versions, learned statistics and signal outcomes. Large raw archives can be optional and restored separately.

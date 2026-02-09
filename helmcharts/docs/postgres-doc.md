# PostgreSQL Deployment Architecture Guide

This document explains the differences between standalone and replicated PostgreSQL deployments, specifically for lab and development environments.

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Standalone Mode](#standalone-mode)
3. [Replication Mode](#replication-mode)
4. [Comparison Matrix](#comparison-matrix)
5. [Configuration Examples](#configuration-examples)
6. [Resource Planning](#resource-planning)
7. [Recommendations](#recommendations)

---

## Architecture Overview

PostgreSQL can be deployed in two primary architectures:

```
STANDALONE                          REPLICATION
┌──────────────┐                   ┌──────────────┐
│   Primary    │                   │   Primary    │──WAL──┐
│              │                   │              │       │
│  Read/Write  │                   │  Read/Write  │       ▼
└──────────────┘                   └──────────────┘    ┌──────────┐
                                                       │ Replica  │
                                                       │          │
                                                       │Read-Only │
                                                       └──────────┘
```

---

## Standalone Mode

**Configuration:**
```yaml
architecture: standalone
```

### ✅ Advantages

1. **Simplicity**
   - Single pod to manage
   - No replication complexity
   - Easier troubleshooting
   - Straightforward backups

2. **Resource Efficiency**
   - Minimal CPU/memory footprint
   - ~250m-500m CPU sufficient for lab
   - ~256-512Mi RAM sufficient for lab
   - Single persistent volume

3. **Performance**
   - No replication overhead
   - No WAL streaming latency
   - Faster writes (no sync wait)
   - All resources dedicated to serving queries

4. **Cost-Effective**
   - Lower resource consumption
   - Fewer pods to run
   - Less storage needed
   - Ideal for development/lab environments

5. **Development Friendly**
   - Quick restarts
   - Easy to reset/recreate
   - Simple connection strings
   - No failover complexity

### ❌ Disadvantages

1. **No High Availability**
   - Single point of failure
   - Downtime during pod restart
   - No automatic failover
   - Manual recovery required

2. **No Read Scalability**
   - All queries hit one instance
   - Cannot distribute read load
   - Limited by single pod resources

3. **Backup Impact**
   - Backups affect primary performance
   - No read replica for reporting
   - Maintenance requires downtime

4. **No Disaster Recovery**
   - No hot standby for failures
   - Recovery from backups only
   - Potential data loss since last backup

### 🎯 Best For

- **Development environments**
- **Lab/testing setups**
- **Single-node deployments**
- **Low traffic applications**
- **Airflow metadata database**
- **Learning PostgreSQL**
- **Resource-constrained environments**

---

## Replication Mode

**Configuration:**
```yaml
architecture: replication
readReplicas:
  replicaCount: 1
```

### ✅ Advantages

1. **High Availability**
   - Automatic failover possible
   - Zero-downtime for pod restarts
   - Replicas take over if primary fails
   - Continuous service availability

2. **Read Scalability**
   - Distribute read queries across replicas
   - Offload reporting to replicas
   - Better query performance under load
   - Multiple connection endpoints

3. **Backup Friendly**
   - Run backups on replica
   - No primary performance impact
   - Continuous replica for recovery
   - Hot standby always available

4. **Production-Like**
   - Mirror production architecture
   - Test failover scenarios
   - Practice HA configurations
   - Learn replication management

5. **Data Safety**
   - Synchronous replication = zero data loss
   - Multiple copies of data
   - Quick recovery time
   - Geographic distribution possible

### ❌ Disadvantages

1. **Resource Intensive**
   - 2x+ pods running
   - 2x+ storage volumes
   - Higher CPU/memory usage
   - Network bandwidth for WAL streaming

2. **Complexity**
   - Replication lag monitoring
   - Failover configuration
   - Split-brain scenarios
   - Connection routing logic

3. **Performance Overhead**
   - Synchronous commits add latency
   - WAL streaming uses bandwidth
   - Replica apply lag
   - More I/O operations

4. **Cost**
   - 2x+ infrastructure cost
   - More persistent volumes
   - Higher cloud costs
   - Additional monitoring needed

5. **Management Overhead**
   - Monitor replication health
   - Handle replica divergence
   - Manage replication slots
   - Configure pg_hba.conf correctly

6. **Development Friction**
   - Slower to spin up/down
   - More complex debugging
   - Multiple pods to check logs
   - Harder to reset state

### 🎯 Best For

- **Production environments**
- **High-traffic applications**
- **Mission-critical databases**
- **Read-heavy workloads**
- **Geographic distribution**
- **Testing HA scenarios**
- **Learning replication patterns**

---

## Comparison Matrix

|         Aspect         |   Standalone   |     Replication      |
|------------------------|----------------|----------------------|
| **Setup Complexity**   | ⭐ Simple      | ⭐⭐⭐ Complex        |
| **Resource Usage**     | ⭐ Low (1 pod) | ⭐⭐⭐ High (2+ pods) |
| **High Availability**  | ❌ None        | ✅ Yes               |
| **Read Scalability**   | ❌ Limited     | ✅ Excellent         |
| **Write Performance**  | ⭐⭐⭐ Fastest  | ⭐⭐ Slower (sync)   |
| **Data Safety**        | ⭐ Backup only | ⭐⭐⭐ Real-time copy |
| **Maintenance**        | ⭐ Easy        | ⭐⭐⭐ Complex        |
| **Cost**               | ⭐ Low         | ⭐⭐⭐ High           |
| **Lab/Dev Friendly**   | ✅ Excellent   | ⚠️ Overkill          |
| **Production Ready**   | ⚠️ Risky       | ✅ Recommended       |

---

## Configuration Examples

### Standalone Configuration (Recommended for Lab)

**File: `postgres-values.yaml`**
```yaml
architecture: standalone

auth:
  enablePostgresUser: true
  postgresPassword: postgresadmin
  username: airflow
  password: airflow
  database: airflow

primary:
  resources:
    requests:
      cpu: 250m              # 0.25 CPU core baseline
      memory: 256Mi
    limits:
      cpu: 1000m             # 1 CPU core max
      memory: 512Mi
  persistence:
    enabled: true
    size: 5Gi
```

**Resource footprint:**
- 1 pod
- 1 persistent volume (5Gi)
- ~250m CPU average, 1 CPU max
- ~256-512Mi RAM

---

### Replication Configuration (Production-Like)

**File: `postgres-values.yaml`**
```yaml
architecture: replication

auth:
  enablePostgresUser: true
  postgresPassword: postgresadmin
  username: airflow
  password: airflow
  database: airflow
  replicationUsername: repl_user
  replicationPassword: replication_pass

replication:
  synchronousCommit: "off"       # "on" for zero data loss
  numSynchronousReplicas: 0      # 1 for synchronous

primary:
  resources:
    requests:
      cpu: 500m                  # 0.5 CPU core baseline
      memory: 512Mi
    limits:
      cpu: 2000m                 # 2 CPU cores max
      memory: 1Gi
  persistence:
    enabled: true
    size: 10Gi

readReplicas:
  name: read
  replicaCount: 1                # Number of read replicas
  resources:
    requests:
      cpu: 250m                  # Less than primary
      memory: 256Mi
    limits:
      cpu: 1000m                 # 1 CPU core max
      memory: 512Mi
  persistence:
    enabled: true
    size: 10Gi
```

**Resource footprint:**
- 2 pods (1 primary + 1 replica)
- 2 persistent volumes (10Gi each = 20Gi total)
- ~750m CPU average (500m + 250m), 3 CPU max total
- ~768Mi-1.5Gi RAM total

---

## Resource Planning

### Lab Environment Constraints

Assuming typical lab resources:
- **CPU**: 4-8 cores total available
- **RAM**: 8-16GB total available
- **Storage**: 50-100GB available

### Standalone Budget (Recommended)
```
PostgreSQL:     250m CPU,  256Mi RAM,  5Gi storage
Airflow:        1500m CPU, 2Gi RAM,    10Gi storage
Redis:          100m CPU,  128Mi RAM,  1Gi storage
pgAdmin:        100m CPU,  256Mi RAM,  1Gi storage
---
TOTAL:          ~2 CPU,    ~3Gi RAM,   ~17Gi storage
Utilization:    25-50%     20-40%      20-30%
```
✅ **Leaves headroom for development pods and system overhead**

### Replication Budget
```
PostgreSQL:     750m CPU,  768Mi RAM,  20Gi storage
Airflow:        1500m CPU, 2Gi RAM,    10Gi storage
Redis:          100m CPU,  128Mi RAM,  1Gi storage
pgAdmin:        100m CPU,  256Mi RAM,  1Gi storage
---
TOTAL:          ~2.5 CPU,  ~3.5Gi RAM, ~32Gi storage
Utilization:    30-60%     25-45%      30-50%
```
⚠️ **Less headroom, tighter on resources**

---

## Recommendations

### For Lab Environment (Current Setup) ✅ RECOMMENDED

**Use Standalone Mode:**
```yaml
architecture: standalone
```

**Reasons:**
1. ✅ Sufficient for Airflow metadata database
2. ✅ Conserves lab resources for other services
3. ✅ Simpler to manage and troubleshoot
4. ✅ Faster development iteration
5. ✅ Easier to reset/recreate
6. ✅ Lower learning curve
7. ✅ No HA requirements in lab

**When to switch to Replication:**
- Testing HA scenarios specifically
- Learning replication mechanics
- Simulating production architecture
- Running heavy read queries that need offloading
- Preparing for production deployment

---

### For Production Environment

**Use Replication Mode:**
```yaml
architecture: replication
replication:
  synchronousCommit: "on"
  numSynchronousReplicas: 1
readReplicas:
  replicaCount: 2
```

**Reasons:**
1. ✅ High availability required
2. ✅ Zero data loss acceptable
3. ✅ Read scalability needed
4. ✅ Business continuity critical
5. ✅ Resources available
6. ✅ Monitoring in place

---

## Decision Flowchart

```
Is this a production environment?
├─ YES → Use Replication
│         ├─ Critical data? → synchronousCommit: "on"
│         └─ Read-heavy? → replicaCount: 2+
│
└─ NO → Is this a lab/dev environment?
         ├─ YES → Use Standalone ✅
         │
         └─ NO → Are you learning HA/replication?
                  ├─ YES → Use Replication
                  └─ NO → Use Standalone
```

---

## Monitoring & Operations

### Standalone Mode

**Check status:**
```bash
kubectl get pods -l app.kubernetes.io/name=postgresql
kubectl logs <pod-name>
```

**Connect:**
```bash
kubectl port-forward svc/postgresql 5432:5432
psql -h localhost -U airflow -d airflow
```

### Replication Mode

**Check replication status:**
```sql
-- On primary
SELECT * FROM pg_stat_replication;

-- On replica
SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
```

**Check lag:**
```sql
SELECT
  CASE
    WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn()
    THEN 0
    ELSE EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())
  END AS lag_seconds;
```

---

## Conclusion

**For your current lab setup with Airflow:**

🎯 **Recommendation: Standalone Mode**

- Optimal resource usage
- Simpler operations
- Sufficient for development
- Easy to upgrade to replication later if needed

Keep the current configuration:
```yaml
architecture: standalone
```

Only switch to replication when you specifically need to test HA scenarios or production-like architectures.

---

## References

- [PostgreSQL Replication Documentation](https://www.postgresql.org/docs/current/runtime-config-replication.html)
- [Bitnami PostgreSQL Helm Chart](https://github.com/bitnami/charts/tree/main/bitnami/postgresql)
- [PostgreSQL High Availability](https://www.postgresql.org/docs/current/high-availability.html)
- [Streaming Replication](https://www.postgresql.org/docs/current/warm-standby.html#STREAMING-REPLICATION)

---

**Last Updated:** 2026-02-09
**Author:** Lab Infrastructure Team

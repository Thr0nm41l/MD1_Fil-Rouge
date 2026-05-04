# Kubernetes Secrets Guide

Complete guide to understanding, creating, retrieving, and using Kubernetes secrets in your lab environment.

---

## Table of Contents
1. [What Are Kubernetes Secrets?](#what-are-kubernetes-secrets)
2. [Secret Types](#secret-types)
3. [Creating Secrets](#creating-secrets)
4. [Retrieving Secrets](#retrieving-secrets)
5. [Using Secrets in Pods](#using-secrets-in-pods)
6. [Best Practices](#best-practices)
7. [Security Considerations](#security-considerations)
8. [Practical Examples](#practical-examples)
9. [Troubleshooting](#troubleshooting)

---

## What Are Kubernetes Secrets?

Kubernetes Secrets are objects that store **sensitive information** like passwords, OAuth tokens, SSH keys, or TLS certificates.

### Why Use Secrets?

✅ **Separation of concerns** - Keep sensitive data out of application code
✅ **Centralized management** - One place to manage credentials
✅ **Access control** - RBAC can restrict who can read secrets
✅ **Encrypted at rest** - (if configured) Encrypted in etcd
✅ **Automatic updates** - Changes propagate to pods (for volume mounts)

### How They Work

```
┌─────────────────┐
│  Create Secret  │
│  kubectl/YAML   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   etcd Store    │
│  (base64 data)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Pod Mount     │
│ • Env Vars      │
│ • Volume Files  │
└─────────────────┘
```

### Important Notes

⚠️ **Secrets are NOT encrypted by default** - They're only base64 encoded
⚠️ **Anyone with API access can decode them** - Use RBAC to restrict access
⚠️ **Not a replacement for proper secret management** - Consider Vault, Sealed Secrets, etc. for production

---

## Secret Types

Kubernetes supports multiple secret types:

|                Type                   |             Usage           |            Example           |
|---------------------------------------|-----------------------------|------------------------------|
|                   `Opaque`            | Generic key-value pairs     | Database passwords, API keys |
| `kubernetes.io/service-account-token` | Service account tokens      | Automatically created        |
| `kubernetes.io/dockerconfigjson`      | Docker registry credentials | Pull private images          |
| `kubernetes.io/tls`                   | TLS certificates            | HTTPS ingress                |
| `kubernetes.io/basic-auth`            | Basic authentication        | HTTP basic auth              |
| `kubernetes.io/ssh-auth`              | SSH keys                    | Git clone operations         |
| `bootstrap.kubernetes.io/token`       | Bootstrap tokens            | Node joining                 |

**Most common: `Opaque`** (default type for generic secrets)

---

## Creating Secrets

### Method 1: From Literal Values (Quick & Easy)

**Create secret with key-value pairs:**

```bash
kubectl create secret generic postgres-passwords \
  --from-literal=postgres-password='postgresadmin' \
  --from-literal=airflow-password='airflow' \
  --from-literal=readonly-password='readonly123'
```

**Result:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-passwords
type: Opaque
data:
  postgres-password: cG9zdGdyZXNhZG1pbg==    # base64 encoded
  airflow-password: YWlyZmxvdw==
  readonly-password: cmVhZG9ubHkxMjM=
```

**Pros:** ✅ Fast, simple for few values
**Cons:** ⚠️ Passwords visible in shell history

---

### Method 2: From Files (Recommended for Certificates)

**Create files:**
```bash
echo -n 'postgresadmin' > postgres-password.txt
echo -n 'airflow' > airflow-password.txt
```

**Create secret from files:**
```bash
kubectl create secret generic postgres-passwords \
  --from-file=postgres-password=postgres-password.txt \
  --from-file=airflow-password=airflow-password.txt
```

**Or entire directory:**
```bash
kubectl create secret generic my-certs --from-file=./certs/
```

**Pros:** ✅ Better for large files (certs, keys)
**Cons:** ⚠️ Files left on disk

---

### Method 3: From YAML Manifest (GitOps Friendly)

⚠️ **WARNING:** Don't commit unencrypted secrets to Git!

**Base64 encode values first:**
```bash
echo -n 'postgresadmin' | base64
# Output: cG9zdGdyZXNhZG1pbg==

echo -n 'airflow' | base64
# Output: YWlyZmxvdw==
```

**Create YAML file:**
```yaml
# postgres-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-passwords
  namespace: default
type: Opaque
data:
  # Values must be base64 encoded
  postgres-password: cG9zdGdyZXNhZG1pbg==
  airflow-password: YWlyZmxvdw==
```

**Or use `stringData` (auto-encodes):**
```yaml
# postgres-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-passwords
  namespace: default
type: Opaque
stringData:
  # Plain text - Kubernetes will base64 encode automatically
  postgres-password: postgresadmin
  airflow-password: airflow
```

**Apply:**
```bash
kubectl apply -f postgres-secret.yaml
```

**Pros:** ✅ Declarative, version-controllable (with encryption)
**Cons:** ⚠️ Risk of committing secrets to Git

---

### Method 4: Docker Registry Secret

**For pulling images from private registries:**

```bash
kubectl create secret docker-registry my-registry-secret \
  --docker-server=docker.io \
  --docker-username=myuser \
  --docker-password=mypassword \
  --docker-email=myemail@example.com
```

**Use in pod:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  imagePullSecrets:
    - name: my-registry-secret
  containers:
    - name: app
      image: myregistry.com/myapp:latest
```

---

### Method 5: TLS Secret

**For HTTPS ingress:**

```bash
kubectl create secret tls my-tls-secret \
  --cert=path/to/cert.crt \
  --key=path/to/cert.key
```

**Use in ingress:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
spec:
  tls:
    - hosts:
        - example.com
      secretName: my-tls-secret
```

---

## Retrieving Secrets

### List All Secrets

```bash
# List secrets in current namespace
kubectl get secrets

# List secrets in all namespaces
kubectl get secrets --all-namespaces

# List with more details
kubectl get secrets -o wide
```

**Output:**
```
NAME                  TYPE                                  DATA   AGE
postgres-passwords    Opaque                                3      5m
default-token-abc123  kubernetes.io/service-account-token   3      30d
```

---

### View Secret Details

```bash
# Basic info (doesn't show data)
kubectl describe secret postgres-passwords

# View as YAML (shows base64 encoded data)
kubectl get secret postgres-passwords -o yaml

# View as JSON
kubectl get secret postgres-passwords -o json
```

**Output (YAML):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-passwords
  namespace: default
type: Opaque
data:
  postgres-password: cG9zdGdyZXNhZG1pbg==
  airflow-password: YWlyZmxvdw==
```

---

### Decode Secret Values

**Method 1: Using kubectl + base64**
```bash
# Get specific key
kubectl get secret postgres-passwords -o jsonpath='{.data.postgres-password}' | base64 --decode
# Output: postgresadmin

# Get all keys
kubectl get secret postgres-passwords -o json | jq -r '.data | map_values(@base64d)'
```

**Method 2: Using kubectl direct decode** (Kubernetes 1.24+)
```bash
# View decoded values
kubectl get secret postgres-passwords -o jsonpath='{.data.postgres-password}' | base64 -d
```

**Method 3: Quick one-liner for all keys**
```bash
kubectl get secret postgres-passwords -o go-template='{{range $k,$v := .data}}{{printf "%s: %s\n" $k ($v|base64decode)}}{{end}}'
```

**Output:**
```
postgres-password: postgresadmin
airflow-password: airflow
readonly-password: readonly123
```

---

### Export Secret to File

```bash
# Export entire secret as YAML
kubectl get secret postgres-passwords -o yaml > secret-backup.yaml

# Export decoded values
kubectl get secret postgres-passwords -o jsonpath='{.data.postgres-password}' | base64 --decode > postgres-password.txt
```

---

## Using Secrets in Pods

### Method 1: Environment Variables (Simple, Common)

**Single environment variable from secret:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
    - name: app
      image: myapp:latest
      env:
        # Single key from secret
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-passwords
              key: postgres-password

        - name: AIRFLOW_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-passwords
              key: airflow-password
```

**All keys from secret as environment variables:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
    - name: app
      image: myapp:latest
      envFrom:
        # All keys become env vars
        - secretRef:
            name: postgres-passwords
```

**Result inside container:**
```bash
echo $postgres-password  # postgresadmin
echo $airflow-password   # airflow
```

**Pros:** ✅ Simple, widely supported
**Cons:** ⚠️ Visible in `kubectl describe pod`, process listings

---

### Method 2: Volume Mounts (More Secure, Auto-Updates)

**Mount secret as files:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
    - name: app
      image: myapp:latest
      volumeMounts:
        - name: secret-volume
          mountPath: /etc/secrets
          readOnly: true

  volumes:
    - name: secret-volume
      secret:
        secretName: postgres-passwords
```

**Result inside container:**
```bash
ls /etc/secrets/
# postgres-password
# airflow-password
# readonly-password

cat /etc/secrets/postgres-password
# postgresadmin
```

**Mount specific keys only:**

```yaml
volumes:
  - name: secret-volume
    secret:
      secretName: postgres-passwords
      items:
        - key: postgres-password
          path: db-password.txt
        - key: airflow-password
          path: airflow-password.txt
```

**Result:**
```bash
ls /etc/secrets/
# db-password.txt
# airflow-password.txt
```

**Pros:** ✅ More secure, auto-updates, fine-grained control
**Cons:** ⚠️ Slightly more complex

---

### Method 3: Init Container Pattern

**Load secrets before main app starts:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  initContainers:
    - name: load-secrets
      image: busybox:latest
      command:
        - sh
        - -c
        - |
          echo "Loading secrets..."
          cat /secrets/postgres-password > /config/db-password
          chmod 600 /config/db-password
      volumeMounts:
        - name: secret-volume
          mountPath: /secrets
        - name: config-volume
          mountPath: /config

  containers:
    - name: app
      image: myapp:latest
      volumeMounts:
        - name: config-volume
          mountPath: /config

  volumes:
    - name: secret-volume
      secret:
        secretName: postgres-passwords
    - name: config-volume
      emptyDir: {}
```

**Pros:** ✅ Pre-process secrets, validate before app starts
**Cons:** ⚠️ More complex setup

---

## Best Practices

### ✅ DO

1. **Use RBAC to restrict access**
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: secret-reader
   rules:
     - apiGroups: [""]
       resources: ["secrets"]
       resourceNames: ["postgres-passwords"]
       verbs: ["get", "list"]
   ```

2. **Use volume mounts over environment variables**
   - Secrets auto-update with volume mounts
   - Less visible in process listings

3. **Enable encryption at rest** (for production)
   ```yaml
   # /etc/kubernetes/manifests/kube-apiserver.yaml
   --encryption-provider-config=/etc/kubernetes/encryption-config.yaml
   ```

4. **Use separate secrets for different components**
   ```bash
   kubectl create secret generic postgres-secret --from-literal=password=xxx
   kubectl create secret generic redis-secret --from-literal=password=yyy
   kubectl create secret generic airflow-secret --from-literal=password=zzz
   ```

5. **Rotate secrets regularly**
   ```bash
   kubectl delete secret postgres-passwords
   kubectl create secret generic postgres-passwords --from-literal=password='new-password'
   kubectl rollout restart deployment/myapp
   ```

6. **Use tools for production secrets**
   - **Sealed Secrets** - Encrypt secrets for Git storage
   - **External Secrets Operator** - Sync from Vault/AWS Secrets Manager
   - **SOPS** - Encrypt secrets in YAML files

---

### ❌ DON'T

1. ❌ **Commit unencrypted secrets to Git**
   ```bash
   # BAD - secret visible in Git history
   git add postgres-secret.yaml
   git commit -m "Add secret"
   ```

2. ❌ **Use secrets for non-sensitive data**
   ```bash
   # BAD - use ConfigMap instead
   kubectl create secret generic app-config --from-literal=app-name='myapp'
   ```

3. ❌ **Print secrets to logs**
   ```bash
   # BAD - secret leaked in logs
   echo "Password is: $DB_PASSWORD"

   # GOOD
   echo "Connecting to database..."
   ```

4. ❌ **Share secrets across namespaces**
   - Secrets are namespace-scoped
   - Create separate secrets per namespace

5. ❌ **Use default service account tokens for apps**
   - Create dedicated service accounts
   - Disable auto-mounting if not needed:
     ```yaml
     apiVersion: v1
     kind: ServiceAccount
     metadata:
       name: myapp
     automountServiceAccountToken: false
     ```

---

## Security Considerations

### 🔐 Secret Security Levels

**Lab Environment (Current):**
```
Security Level: ★☆☆☆☆ (Low)
- Base64 encoded (not encrypted)
- Stored in plaintext in etcd
- Accessible via kubectl
```

**Production Minimum:**
```
Security Level: ★★★☆☆ (Medium)
- Encryption at rest enabled
- RBAC restricting access
- Secrets in volume mounts
- Regular rotation policy
```

**Enterprise Production:**
```
Security Level: ★★★★★ (High)
- External secret manager (Vault)
- Automatic rotation
- Audit logging enabled
- Secrets never in cluster
```

---

### Encryption at Rest (Production)

**Enable for production clusters:**

1. **Create encryption config:**
```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

2. **Update kube-apiserver:**
```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
--encryption-provider-config=/etc/kubernetes/encryption-config.yaml
```

3. **Encrypt existing secrets:**
```bash
kubectl get secrets --all-namespaces -o json | kubectl replace -f -
```

---

## Practical Examples

### Example 1: PostgreSQL with Secrets

**Create secret:**
```bash
kubectl create secret generic postgres-secret \
  --from-literal=postgres-password='postgresadmin' \
  --from-literal=user-password='airflow' \
  --from-literal=database='airflow'
```

**Use in Helm values:**
```yaml
# postgres-values.yaml
auth:
  existingSecret: "postgres-secret"
  secretKeys:
    adminPasswordKey: "postgres-password"
    userPasswordKey: "user-password"
```

**Deploy:**
```bash
helm upgrade --install postgresql bitnami/postgresql -f postgres-values.yaml
```

---

### Example 2: Airflow with Multiple Secrets

**Create secrets:**
```bash
# Fernet key for Airflow
kubectl create secret generic airflow-fernet-key \
  --from-literal=fernet-key='your-fernet-key-here'

# Database connection
kubectl create secret generic airflow-db-secret \
  --from-literal=connection='postgresql://airflow:password@postgresql:5432/airflow'

# Redis password
kubectl create secret generic airflow-redis-secret \
  --from-literal=password='redis-password'
```

**Use in pod:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: airflow-webserver
spec:
  containers:
    - name: webserver
      image: apache/airflow:2.8.0
      env:
        - name: AIRFLOW__CORE__FERNET_KEY
          valueFrom:
            secretKeyRef:
              name: airflow-fernet-key
              key: fernet-key

        - name: AIRFLOW__CORE__SQL_ALCHEMY_CONN
          valueFrom:
            secretKeyRef:
              name: airflow-db-secret
              key: connection

        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: airflow-redis-secret
              key: password
```

---

### Example 3: API Keys as Files

**Create secret:**
```bash
kubectl create secret generic api-keys \
  --from-file=github-token=./github-token.txt \
  --from-file=slack-webhook=./slack-webhook.txt
```

**Mount in pod:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
        - name: app
          image: myapp:latest
          volumeMounts:
            - name: api-keys
              mountPath: /etc/api-keys
              readOnly: true
      volumes:
        - name: api-keys
          secret:
            secretName: api-keys
            defaultMode: 0400  # Read-only by owner
```

**Use in application:**
```python
# Read API keys from files
with open('/etc/api-keys/github-token') as f:
    github_token = f.read().strip()

with open('/etc/api-keys/slack-webhook') as f:
    slack_webhook = f.read().strip()
```

---

### Example 4: TLS Certificate

**Create from cert files:**
```bash
kubectl create secret tls my-tls-cert \
  --cert=server.crt \
  --key=server.key
```

**Use in Ingress:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
spec:
  tls:
    - hosts:
        - myapp.example.com
      secretName: my-tls-cert
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp
                port:
                  number: 80
```

---

## Troubleshooting

### Secret Not Found

**Error:**
```
Error: secret "postgres-passwords" not found
```

**Solution:**
```bash
# Check if secret exists
kubectl get secret postgres-passwords

# Check namespace
kubectl get secret postgres-passwords -n <namespace>

# Create if missing
kubectl create secret generic postgres-passwords --from-literal=password=xxx
```

---

### Cannot Decode Secret

**Error:**
```
error: unable to decode secret
```

**Solution:**
```bash
# Verify secret data
kubectl get secret postgres-passwords -o yaml

# Check base64 encoding
kubectl get secret postgres-passwords -o jsonpath='{.data.password}' | base64 --decode
```

---

### Pod Can't Access Secret

**Error:**
```
Error from server (Forbidden): secrets "postgres-passwords" is forbidden
```

**Solution:**
```bash
# Check RBAC permissions
kubectl auth can-i get secret/postgres-passwords --as=system:serviceaccount:default:myapp

# Create role and binding
kubectl create role secret-reader --verb=get --resource=secrets --resource-name=postgres-passwords
kubectl create rolebinding myapp-secret-reader --role=secret-reader --serviceaccount=default:myapp
```

---

### Secret Not Updating in Pod

**Issue:** Changed secret but pod still has old value

**Solution:**
```bash
# If using environment variables - restart pod
kubectl rollout restart deployment/myapp

# If using volume mounts - wait (kubelet polls every ~60s)
# Or force by deleting pod
kubectl delete pod <pod-name>
```

---

### View What Pod Sees

**Check environment variables:**
```bash
kubectl exec <pod-name> -- env | grep PASSWORD
```

**Check mounted files:**
```bash
kubectl exec <pod-name> -- ls /etc/secrets
kubectl exec <pod-name> -- cat /etc/secrets/password
```

---

## Quick Reference

### Common Commands

```bash
# Create secret
kubectl create secret generic my-secret --from-literal=key=value

# List secrets
kubectl get secrets

# View secret
kubectl get secret my-secret -o yaml

# Decode secret
kubectl get secret my-secret -o jsonpath='{.data.key}' | base64 --decode

# Delete secret
kubectl delete secret my-secret

# Update secret
kubectl create secret generic my-secret --from-literal=key=newvalue --dry-run=client -o yaml | kubectl apply -f -

# Copy secret to another namespace
kubectl get secret my-secret -n source-ns -o yaml | \
  sed 's/namespace: source-ns/namespace: target-ns/' | \
  kubectl apply -f -
```

---

### Secret vs ConfigMap

|      Feature   |           Secret       |       ConfigMap      |
|----------------|------------------------|----------------------|
| **Purpose**    | Sensitive data         | Non-sensitive config |
| **Encoding**   | Base64                 | Plain text           |
| **Size Limit** | 1MB                    | 1MB                  |
| **Use For**    | Passwords, keys, certs | App config, env vars |
| **Visibility** | Less visible in logs   | Visible everywhere   |

**Rule of thumb:** If you wouldn't want it in logs or Git, use a Secret!

---

## Conclusion

### For Your Lab Environment

**Recommended Approach:**

1. ✅ **Use `kubectl create secret` for quick testing**
2. ✅ **Use volume mounts over env vars**
3. ✅ **Create separate secrets per service**
4. ⚠️ **For production, add encryption at rest and use external secret manager**

### Next Steps

- [ ] Create secrets for PostgreSQL passwords
- [ ] Update Helm values to use existing secrets
- [ ] Test secret rotation procedures
- [ ] Document secret naming conventions
- [ ] Plan for production secret management

---

## References

- [Kubernetes Secrets Documentation](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Secrets Best Practices](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [External Secrets Operator](https://external-secrets.io/)
- [SOPS](https://github.com/mozilla/sops)

---

**Last Updated:** 2026-02-09
**Author:** Lab Infrastructure Team

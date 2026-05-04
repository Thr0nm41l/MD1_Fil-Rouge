# MkDocs — Documentation Site

This project uses **MkDocs** with the **Material** theme to serve all documentation as a web site, deployed inside the Kubernetes cluster.

---

## How It Works

MkDocs reads the `documentation/` directory as its source (`docs_dir: .`) and the `mkdocs.yaml` file as its configuration. The site is served by a pod in the `documentation` namespace, which continuously syncs the repository via a git-sync sidecar — the same pattern used by Airflow for DAGs.

```
GitHub repo (feature/serviceAPI)
        │  git-sync (every 60 s)
        ▼
/docs/repo/documentation/     ← mkdocs.yaml + all .md files
        │
        ▼
mkdocs serve → port 8000 → svc/mkdocs → kubectl port-forward
```

---

## Accessing the Site

The service is a ClusterIP — access it via port-forward:

```bash
kubectl port-forward svc/mkdocs 8080:8000 -n documentation
```

Then open: [http://localhost:8080](http://localhost:8080)

---

## Deployment

The full deployment manifest is at `helmcharts/mkdocs-deployment.yaml`. It creates:

- The `documentation` namespace
- A `Deployment` with three containers:
  - `git-sync-init` — init container that clones the repo before the pod starts
  - `mkdocs` — runs `mkdocs serve` on port 8000
  - `git-sync` — sidecar that re-syncs from GitHub every 60 s
- A `ClusterIP` Service on port 8000

To deploy:

```bash
kubectl apply -f helmcharts/mkdocs-deployment.yaml
kubectl wait --for=condition=ready pod -l app=mkdocs -n documentation --timeout=120s
```

To remove:

```bash
kubectl delete -f helmcharts/mkdocs-deployment.yaml
```

---

## Configuration (`mkdocs.yaml`)

The configuration file lives at `documentation/mkdocs.yaml`.

```yaml
site_name: Ecotrack Documentation
theme:
  name: material
  palette:
    scheme: slate      # dark mode
    primary: indigo
    accent: indigo
  features:
    - navigation.sections   # group nav entries under section headers
    - navigation.top        # "back to top" button
    - search.highlight      # highlight search terms in results

docs_dir: .   # documentation/ is both the config root and the content root
```

### Active Material features

| Feature | Effect |
|---|---|
| `navigation.sections` | Top-level nav items render as section headers instead of expandable links |
| `navigation.top` | Shows a "Back to top" button when scrolling up |
| `search.highlight` | Highlights the search query in the matched page |

---

## Adding a Page

1. Create a `.md` file anywhere under `documentation/`
2. Add an entry to the `nav:` block in `mkdocs.yaml`
3. Push to `feature/serviceAPI` — the site updates within 60 seconds

Example — adding a new how-to guide:

```yaml
# documentation/mkdocs.yaml
nav:
  - How-to Guides:
    - Existing Guide: howto/existing.md
    - My New Guide: howto/my-new-guide.md   # ← add this line
```

Pages not listed in `nav:` are still built and searchable but won't appear in the sidebar.

---

## Local Development

Run the site locally without Kubernetes:

```bash
# Install dependencies
pip install mkdocs-material

# Serve with live reload
cd documentation/
mkdocs serve -f mkdocs.yaml --dev-addr 0.0.0.0:8000
```

The dev server watches for file changes and reloads the browser automatically. Any `.md` file saved under `documentation/` is reflected immediately.

To build a static site instead of serving:

```bash
mkdocs build -f mkdocs.yaml
# Output in documentation/site/
```

---

## Page Structure

MkDocs renders standard Markdown. The Material theme additionally supports:

**Admonitions:**
```markdown
!!! note
    This is a note.

!!! warning
    This is a warning.
```

**Code blocks with syntax highlighting:**
````markdown
```python
def hello():
    print("hello")
```
````

**Tables** (standard GitHub-flavoured Markdown):
```markdown
| Column A | Column B |
|---|---|
| value 1  | value 2  |
```

---

## Troubleshooting

### Site not updating after a push

The git-sync sidecar polls every 60 s. Wait a minute then refresh. To force an immediate re-sync, restart the pod:

```bash
kubectl rollout restart deployment/mkdocs -n documentation
```

### Pod stuck in `Init` state

The init container needs to reach GitHub. Check network access from within the cluster:

```bash
kubectl logs -n documentation -l app=mkdocs -c git-sync-init
```

### `mkdocs serve` crashes on startup

The most common cause is a broken `nav:` reference (a page listed in the nav that doesn't exist on disk). Check the pod logs:

```bash
kubectl logs -n documentation -l app=mkdocs -c mkdocs
```

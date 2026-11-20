# CICADA

Smart Observability & Hackathon Project.

---

## Collaborator Quickstart

### 1. Clone the repository
```bash
git clone https://github.com/naamamaatra/cicada.git
cd cicada
```

### 2. Workflow Guidelines
To avoid merge conflicts while contributing in parallel:

1. **Always sync with `main` before starting a feature:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a feature branch:**
   ```bash
   git checkout -b feat/<feature-name>
   ```

3. **Commit and push your feature branch:**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   git push -u origin feat/<feature-name>
   ```

4. **Merge to `main` via PR on GitHub** after testing locally.

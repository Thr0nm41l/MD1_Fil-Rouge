#!/usr/bin/env bash
#
# run_api_tests.sh — Démo de la suite de tests API ECOTRACK
#
#   Lance les tests pytest de l'API et affiche un résumé lisible pour la soutenance.
#
#   Modes :
#     ./run_api_tests.sh            → tests UNITAIRES seuls (rapide, aucune infra)   [défaut]
#     ./run_api_tests.sh --full     → suite COMPLÈTE : ouvre le port-forward PostgreSQL,
#                                     récupère les identifiants du cluster, lance les 58 tests,
#                                     puis referme proprement le tunnel
#     ./run_api_tests.sh --cov      → ajoute le rapport de couverture
#     ./run_api_tests.sh --help     → aide
#
#   Pré-requis : venv ~/.venv/pytest, kubectl pointant sur le cluster (mode --full).
#
set -uo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration (ajuste si besoin, ou surcharge via variables d'environnement)
# ─────────────────────────────────────────────────────────────────────────────
REPO_DIR="${REPO_DIR:-$HOME/Documents/GitRepos/MD1_Fil-Rouge}"
VENV="${VENV:-$HOME/.venv/pytest}"
NAMESPACE="${NAMESPACE:-datalake}"
PG_SVC="${PG_SVC:-postgres-postgresql}"
PG_SECRET="${PG_SECRET:-postgres-postgresql}"      # secret K8s contenant le mot de passe
PG_LOCAL_PORT="${PG_LOCAL_PORT:-5432}"
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-$PG_LOCAL_PORT}"
export POSTGRES_DB="${POSTGRES_DB:-Ecotrack}"
export POSTGRES_USER="${POSTGRES_USER:-postgres}"

# ─────────────────────────────────────────────────────────────────────────────
# Couleurs
# ─────────────────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  G=$'\e[1;32m'; R=$'\e[1;31m'; Y=$'\e[1;33m'; B=$'\e[1;36m'; DIM=$'\e[2m'; N=$'\e[0m'
else
  G=""; R=""; Y=""; B=""; DIM=""; N=""
fi

MODE="unit"; COV=""
for arg in "$@"; do
  case "$arg" in
    --full)  MODE="full" ;;
    --unit)  MODE="unit" ;;
    --cov)   COV="--cov=. --cov-report=term-missing" ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# \{0,1\}//; 1d'
      exit 0 ;;
    *) echo "${R}Option inconnue : $arg${N}"; exit 2 ;;
  esac
done

banner() { echo; echo "${B}══════════════════════════════════════════════════════════════${N}"; echo "${B}  $1${N}"; echo "${B}══════════════════════════════════════════════════════════════${N}"; }

PF_PID=""
cleanup() {
  if [[ -n "$PF_PID" ]] && kill -0 "$PF_PID" 2>/dev/null; then
    echo "${DIM}Fermeture du tunnel PostgreSQL (pid $PF_PID)…${N}"
    kill "$PF_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

# ─────────────────────────────────────────────────────────────────────────────
# 1. Vérifications
# ─────────────────────────────────────────────────────────────────────────────
banner "ECOTRACK — Suite de tests API   (mode : ${MODE})"

[[ -d "$REPO_DIR/apiservice" ]] || { echo "${R}✗ Dépôt introuvable : $REPO_DIR/apiservice${N} (surcharge avec REPO_DIR=…)"; exit 1; }
[[ -f "$VENV/bin/activate" ]]   || { echo "${R}✗ venv introuvable : $VENV${N} (surcharge avec VENV=…)"; exit 1; }

# shellcheck disable=SC1091
source "$VENV/bin/activate"
echo "${G}✓${N} venv activé        ${DIM}$VENV${N}"
echo "${G}✓${N} pytest             ${DIM}$(pytest --version 2>&1 | head -n1)${N}"
echo "${G}✓${N} dépôt              ${DIM}$REPO_DIR${N}"

cd "$REPO_DIR/apiservice"

PYTEST_FILTER=(-m "not integration")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Mode --full : tunnel PostgreSQL + identifiants
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$MODE" == "full" ]]; then
  command -v kubectl >/dev/null || { echo "${R}✗ kubectl introuvable${N}"; exit 1; }

  if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    echo "${DIM}Récupération du mot de passe depuis le secret $PG_SECRET…${N}"
    POSTGRES_PASSWORD="$(kubectl get secret "$PG_SECRET" -n "$NAMESPACE" -o jsonpath='{.data.postgres-password}' 2>/dev/null | base64 -d)" || true
    export POSTGRES_PASSWORD
  fi
  [[ -n "${POSTGRES_PASSWORD:-}" ]] || { echo "${R}✗ Mot de passe PostgreSQL non résolu${N} — définis POSTGRES_PASSWORD=… et relance."; exit 1; }

  echo "${DIM}Ouverture du tunnel : svc/$PG_SVC $PG_LOCAL_PORT:5432 -n $NAMESPACE…${N}"
  kubectl port-forward "svc/$PG_SVC" "$PG_LOCAL_PORT:5432" -n "$NAMESPACE" >/dev/null 2>&1 &
  PF_PID=$!

  # Attente active de la disponibilité du port (max ~15 s)
  for i in $(seq 1 30); do
    if (exec 3<>"/dev/tcp/localhost/$PG_LOCAL_PORT") 2>/dev/null; then exec 3>&- 3<&-; break; fi
    sleep 0.5
    [[ "$i" == "30" ]] && { echo "${R}✗ PostgreSQL injoignable sur localhost:$PG_LOCAL_PORT${N}"; exit 1; }
  done
  echo "${G}✓${N} PostgreSQL joignable ${DIM}localhost:$PG_LOCAL_PORT/$POSTGRES_DB (user $POSTGRES_USER)${N}"
  PYTEST_FILTER=()   # on lève le filtre → tous les tests (unitaires + intégration)
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Exécution
# ─────────────────────────────────────────────────────────────────────────────
banner "Exécution de pytest"
LOG="$(mktemp)"
set -o pipefail
pytest tests/ "${PYTEST_FILTER[@]}" -v -ra --tb=short --color=yes $COV 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Résumé
# ─────────────────────────────────────────────────────────────────────────────
SUMMARY="$(grep -E '^(=+ ).*(passed|failed|error|skipped)' "$LOG" | tail -n1 | sed -E 's/=//g; s/^ *//; s/ *$//')"
rm -f "$LOG"

echo
if [[ "$RC" -eq 0 ]]; then
  echo "${G}┌────────────────────────────────────────────────────────────┐${N}"
  echo "${G}│  ✓  TESTS RÉUSSIS                                           │${N}"
  echo "${G}│  ${SUMMARY}${N}"
  echo "${G}└────────────────────────────────────────────────────────────┘${N}"
  [[ "$MODE" == "unit" ]] && echo "${DIM}(tests d'intégration ignorés en mode unitaire — lance --full pour la base live)${N}"
else
  echo "${R}┌────────────────────────────────────────────────────────────┐${N}"
  echo "${R}│  ✗  ÉCHEC                                                   │${N}"
  echo "${R}│  ${SUMMARY}${N}"
  echo "${R}└────────────────────────────────────────────────────────────┘${N}"
fi
echo
exit "$RC"
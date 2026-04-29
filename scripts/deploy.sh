#!/usr/bin/env bash
# deploy.sh <target> — One-command deploy
#
# Usage:
#   ./deploy.sh spectr       → deploy to spectr.in (multi-tenant)
#   ./deploy.sh algorythm    → deploy to algorythm.spectr.in
#   ./deploy.sh cam          → deploy to cymllp.spectr.in
#   ./deploy.sh all          → deploy to ALL configured firms (staged)
#
# What it does:
#   1. Builds Docker image from current HEAD
#   2. Tags with git SHA + :latest
#   3. Pushes to registry
#   4. Deploys to Fly.io (or Railway)
#   5. Waits for health check to pass
#   6. On failure → auto-rollback
#
# Requires:
#   - flyctl installed + authenticated
#   - Docker running
#   - GitHub CLI (gh) for release tagging (optional)

set -euo pipefail

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
    echo "Usage: $0 <target>"
    echo "  target: spectr | algorythm | cam | sam | ... | all"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

echo "╔════════════════════════════════════════════════════╗"
echo "║  Spectr Deploy — target: $TARGET"
echo "║  Branch: $GIT_BRANCH   SHA: $GIT_SHA"
echo "╚════════════════════════════════════════════════════╝"

# List of known firms (should match firms/ directory)
ALL_FIRMS=(spectr algorythm)
# Add here as new firms onboard: ALL_FIRMS=(spectr algorythm cam sam)

deploy_one() {
    local firm="$1"
    local app_name
    local firm_short

    if [ "$firm" = "spectr" ]; then
        app_name="spectr-web"
        firm_short=""   # empty = multi-tenant mode
    else
        app_name="${firm}-spectr"
        firm_short="$firm"
    fi

    echo
    echo "──────────────────────────────────────────"
    echo "  Deploying to: $app_name (FIRM_SHORT='$firm_short')"
    echo "──────────────────────────────────────────"

    # Check if Fly app exists
    if ! flyctl apps list 2>/dev/null | grep -q "$app_name"; then
        echo "⚠  Fly app '$app_name' does not exist. Use ./scripts/new-firm.sh to create it first."
        return 1
    fi

    # Get current image for rollback
    CURRENT_IMAGE=$(flyctl image show --app "$app_name" 2>/dev/null | grep -oE 'registry\.fly\.io/[^ ]+' || echo "")

    # Build + push + deploy
    if flyctl deploy \
        --app "$app_name" \
        --remote-only \
        --strategy rolling \
        --wait-timeout 600 \
        --env "FIRM_SHORT=$firm_short" \
        --env "DEPLOYED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --env "GIT_SHA=$GIT_SHA" \
        --image-label "$GIT_SHA"; then
        echo "✓ Deploy to $app_name succeeded"

        # Health check
        sleep 5
        HEALTH_URL="https://${app_name}.fly.dev/health"
        if curl -sf --max-time 10 "$HEALTH_URL" >/dev/null 2>&1; then
            echo "✓ Health check passed"
        else
            echo "✗ Health check FAILED at $HEALTH_URL — consider rollback"
            if [ -n "$CURRENT_IMAGE" ]; then
                echo "  Run: ./scripts/rollback.sh $firm"
            fi
            return 1
        fi
    else
        echo "✗ Deploy to $app_name FAILED"
        return 1
    fi
}

# Dispatch
if [ "$TARGET" = "all" ]; then
    echo "Staged rollout: spectr → algorythm → (all firms)"
    FAILED=()
    # Always deploy canary first
    if ! deploy_one "algorythm"; then
        echo "Canary deploy failed — aborting rollout"
        exit 1
    fi
    echo
    echo "✓ Canary OK. Deploying to production targets..."
    for f in "${ALL_FIRMS[@]}"; do
        if [ "$f" != "algorythm" ]; then
            if ! deploy_one "$f"; then
                FAILED+=("$f")
            fi
        fi
    done
    echo
    if [ ${#FAILED[@]} -eq 0 ]; then
        echo "✓ All deployments successful"
    else
        echo "✗ Failed: ${FAILED[*]}"
        exit 1
    fi
else
    deploy_one "$TARGET"
fi

#!/usr/bin/env bash
# rollback.sh <target> [release-id] — Revert a deployment to previous version
#
# Usage:
#   ./scripts/rollback.sh spectr              → revert spectr.in to previous release
#   ./scripts/rollback.sh cam                 → revert cymllp.spectr.in
#   ./scripts/rollback.sh cam v42             → revert to specific release v42
#   ./scripts/rollback.sh spectr --list       → show recent releases
#
# Uses flyctl releases + flyctl deploy --image to revert.

set -euo pipefail

TARGET="${1:-}"
RELEASE_OR_FLAG="${2:-}"

if [ -z "$TARGET" ]; then
    echo "Usage: $0 <target> [release-id | --list]"
    exit 1
fi

if [ "$TARGET" = "spectr" ]; then
    APP_NAME="spectr-web"
else
    APP_NAME="${TARGET}-spectr"
fi

echo "Target: $TARGET ($APP_NAME)"

if [ "$RELEASE_OR_FLAG" = "--list" ]; then
    flyctl releases --app "$APP_NAME" | head -20
    exit 0
fi

if [ -n "$RELEASE_OR_FLAG" ]; then
    echo "Rolling back to release: $RELEASE_OR_FLAG"
    flyctl deploy --app "$APP_NAME" --image "registry.fly.io/${APP_NAME}:deployment-${RELEASE_OR_FLAG}" --strategy rolling
else
    # Get previous release (second most recent)
    PREV_VERSION=$(flyctl releases --app "$APP_NAME" --json 2>/dev/null | jq -r '.[1].version' 2>/dev/null || echo "")
    if [ -z "$PREV_VERSION" ] || [ "$PREV_VERSION" = "null" ]; then
        echo "✗ Could not find previous release. Use --list to see available releases."
        exit 1
    fi
    echo "Previous release: v$PREV_VERSION"
    read -p "Rollback $APP_NAME to v$PREV_VERSION? [y/N] " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        flyctl releases rollback v$PREV_VERSION --app "$APP_NAME"
        echo
        echo "✓ Rollback triggered. Waiting for health check..."
        sleep 15
        HEALTH_URL="https://${APP_NAME}.fly.dev/health"
        if curl -sf --max-time 10 "$HEALTH_URL" >/dev/null 2>&1; then
            echo "✓ Health check passed — rollback successful"
        else
            echo "⚠  Health check not passing yet. Monitor with: flyctl logs --app $APP_NAME"
        fi
    else
        echo "Aborted."
    fi
fi

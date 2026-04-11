#!/usr/bin/env bash
set -euo pipefail

WORKFLOWS_DIR=".github/workflows"
GITHUB_TOKEN=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --token)
            GITHUB_TOKEN="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper function for curl
gh_api() {
    local url="$1"
    if [ -n "$GITHUB_TOKEN" ]; then
        curl -s -H "Authorization: token $GITHUB_TOKEN" "$url"
    else
        curl -s "$url"
    fi
}

if [ ! -d "$WORKFLOWS_DIR" ]; then
    echo "No workflows found in $WORKFLOWS_DIR"
    exit 1
fi

echo "Starting GitHub Actions update..."
echo

find "$WORKFLOWS_DIR" -type f \( -name "*.yml" \) | while read -r workflow; do
    echo "Processing workflow: $workflow"

    grep -E 'uses: .*@' "$workflow" | while read -r line; do
        echo "  Found action line: $line"

        repo_full=$(echo "$line" | sed -E 's/.*uses: ([^@]+)@.*/\1/')
        repo=$(echo "$repo_full" | cut -d/ -f1,2)

        ref=$(echo "$line" | sed -E 's/.*@([^ ]+).*/\1/')
        echo "    Repo: $repo"
        echo "    Current ref: $ref"

        latest_tag=$(
          gh_api "https://api.github.com/repos/$repo/tags?per_page=100" \
          | jq -r '.[].name' \
          | sort -V \
          | tail -n 1
        )

        new_line="${line%@*}@${latest_tag}"

        # Escape for sed
        escaped_old_line=$(printf '%s\n' "$line" | sed 's/[\/&]/\\&/g')
        escaped_new_line=$(printf '%s\n' "$new_line" | sed 's/[\/&]/\\&/g')

        # Replace the old line with the new line
        sed -i "s|$escaped_old_line|$escaped_new_line|" "$workflow"

        echo "    Updated $repo@$ref -> $latest_tag"
        echo
    done
done

echo "All workflows processed."

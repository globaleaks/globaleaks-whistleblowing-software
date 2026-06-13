#!/usr/bin/env bash
set -euo pipefail

WORKFLOWS_DIR=".github/workflows"
GITHUB_TOKEN=""
UPGRADE_TAGS=0
DRY_RUN=0
VERBOSE=0

usage() {
    cat <<'EOF'
Usage: bump_gitactions_version.sh [OPTIONS]

Pins every `uses: owner/repo@<ref>` in .github/workflows/*.yml to a 40-char
commit SHA, with `# <tag>` as a trailing comment.

The script prompts for a GitHub token without echoing it. Leave the prompt
empty to fall back to $GITHUB_TOKEN/$GH_TOKEN, or to run anonymously.

Options:
  --upgrade       Bump to the latest stable tag before pinning
  --dry-run       Show what would change, don't write files
  --dir <PATH>    Workflows directory (default: .github/workflows)
  -v, --verbose   Print API URLs and raw responses on error
  -h, --help      This help
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --upgrade)      UPGRADE_TAGS=1; shift ;;
        --dry-run)      DRY_RUN=1; shift ;;
        --dir)          WORKFLOWS_DIR="$2"; shift 2 ;;
        -v|--verbose)   VERBOSE=1; shift ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# Read the token without echoing it, so it never lands in argv, shell history,
# terminal logs, or CI logs. An empty answer falls back to the environment.
read -rsp "GitHub token (leave empty to skip): " token_input < /dev/tty || token_input=""
echo
GITHUB_TOKEN="${token_input:-${GITHUB_TOKEN:-${GH_TOKEN:-}}}"
unset token_input

command -v jq   >/dev/null || { echo "ERROR: jq is not installed. apt/brew install jq" >&2; exit 2; }
command -v curl >/dev/null || { echo "ERROR: curl is not installed" >&2; exit 2; }

# Calls a GitHub API URL.
#   $1 = URL
#   $2 = path of a file where body will be written
# Echoes the HTTP code on stdout. Subshell-safe: nothing depends on globals.
gh_api() {
    local url="$1" body_file="$2" http_code
    if [ -n "$GITHUB_TOKEN" ]; then
        http_code=$(curl -sSL -o "$body_file" -w '%{http_code}' \
            -H "Authorization: token $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github+json" "$url" 2>/dev/null || echo "000")
    else
        http_code=$(curl -sSL -o "$body_file" -w '%{http_code}' \
            -H "Accept: application/vnd.github+json" "$url" 2>/dev/null || echo "000")
    fi
    echo "${http_code:-000}"
}

# resolve_sha owner/repo tag → 40-char commit SHA on stdout.
# Return: 0 success, 1 transient error (skip this one), 2 fatal (abort).
resolve_sha() {
    local repo="$1" ref="$2" body_file http_code body type sha msg
    body_file=$(mktemp)

    http_code=$(gh_api "https://api.github.com/repos/$repo/git/refs/tags/$ref" "$body_file")
    body=$(cat "$body_file")

    case "$http_code" in
        200) ;;
        000)
            echo "    ✗ network error contacting api.github.com" >&2
            rm -f "$body_file"; return 1 ;;
        401)
            echo "    ✗ HTTP 401 — invalid GITHUB_TOKEN" >&2
            rm -f "$body_file"; return 2 ;;
        403|429)
            msg=$(echo "$body" | jq -r '.message // empty' 2>/dev/null)
            if [[ "$msg" == *"rate limit"* ]] || [[ "$msg" == *"API rate"* ]]; then
                echo "    ✗ GitHub API rate limit hit. Re-run and provide a token at the prompt." >&2
                rm -f "$body_file"; return 2
            fi
            echo "    ✗ HTTP $http_code — $msg" >&2
            rm -f "$body_file"; return 2 ;;
        404)
            # Maybe it's a branch, not a tag
            http_code=$(gh_api "https://api.github.com/repos/$repo/branches/$ref" "$body_file")
            body=$(cat "$body_file")
            if [ "$http_code" = "200" ]; then
                sha=$(echo "$body" | jq -r '.commit.sha // empty')
                if [[ "$sha" =~ ^[0-9a-f]{40}$ ]]; then
                    rm -f "$body_file"; echo "$sha"; return 0
                fi
            fi
            echo "    ✗ ref '$ref' not found in $repo (neither tag nor branch)" >&2
            [ $VERBOSE -eq 1 ] && echo "      URL: https://api.github.com/repos/$repo/git/refs/tags/$ref" >&2
            rm -f "$body_file"; return 1 ;;
        *)
            echo "    ✗ unexpected HTTP $http_code for $repo@$ref" >&2
            [ $VERBOSE -eq 1 ] && echo "      Body: $body" >&2
            rm -f "$body_file"; return 1 ;;
    esac

    type=$(echo "$body" | jq -r '.object.type // empty')
    sha=$(echo "$body" | jq -r '.object.sha // empty')
    if [ -z "$sha" ]; then
        echo "    ✗ malformed API response" >&2
        [ $VERBOSE -eq 1 ] && echo "      Body: $body" >&2
        rm -f "$body_file"; return 1
    fi

    # Annotated tag → dereference to commit
    if [ "$type" = "tag" ]; then
        http_code=$(gh_api "https://api.github.com/repos/$repo/git/tags/$sha" "$body_file")
        body=$(cat "$body_file")
        if [ "$http_code" != "200" ]; then
            echo "    ✗ failed to dereference annotated tag (HTTP $http_code)" >&2
            rm -f "$body_file"; return 1
        fi
        sha=$(echo "$body" | jq -r '.object.sha // empty')
    fi

    rm -f "$body_file"

    if ! [[ "$sha" =~ ^[0-9a-f]{40}$ ]]; then
        echo "    ✗ got non-SHA response: '$sha'" >&2
        return 1
    fi
    echo "$sha"
}

latest_tag() {
    local repo="$1" body_file http_code
    body_file=$(mktemp)
    http_code=$(gh_api "https://api.github.com/repos/$repo/tags?per_page=100" "$body_file")
    if [ "$http_code" = "200" ]; then
        jq -r '.[].name' "$body_file" \
            | grep -E '^v?[0-9]+\.[0-9]+(\.[0-9]+)?$' \
            | sort -V | tail -n 1
    fi
    rm -f "$body_file"
}

[ -d "$WORKFLOWS_DIR" ] || { echo "ERROR: $WORKFLOWS_DIR not found" >&2; exit 1; }

echo "Starting GitHub Actions pinning..."
[ $DRY_RUN -eq 1 ]     && echo "  (dry-run mode — no files will be written)"
[ -z "$GITHUB_TOKEN" ] && echo "  ⚠ anonymous mode — 60 req/h rate limit. Provide a token to raise it."
echo

TOTAL=0
PINNED=0
FAILED=0

while IFS=: read -r workflow lineno content; do
    [[ "$content" =~ uses:[[:space:]]*\.?\.?/ ]] && continue
    [[ "$content" =~ uses:[[:space:]]*docker:// ]] && continue

    full=$(echo "$content" | sed -E 's/.*uses:[[:space:]]*"?([^"#[:space:]]+@[^"#[:space:]]+).*/\1/')
    [[ "$full" != *"@"* ]] && continue

    repo_full="${full%@*}"
    ref="${full##*@}"
    repo=$(echo "$repo_full" | cut -d/ -f1,2)
    TOTAL=$((TOTAL + 1))

    if [[ "$ref" =~ ^[0-9a-f]{40}$ ]] && [ $UPGRADE_TAGS -eq 0 ]; then
        echo "  ✓ $workflow:$lineno  $repo_full@${ref:0:12}…  (already pinned)"
        continue
    fi

    target_tag="$ref"
    if [ $UPGRADE_TAGS -eq 1 ]; then
        latest=$(latest_tag "$repo" || true)
        if [ -n "$latest" ] && [ "$latest" != "$ref" ]; then
            echo "  ▸ $repo: upgrade $ref → $latest"
            target_tag="$latest"
        fi
    fi

    echo "  ▸ resolving $repo@$target_tag …"
    set +e
    sha=$(resolve_sha "$repo" "$target_tag")
    rc=$?
    set -e

    if [ $rc -eq 2 ]; then
        echo
        echo "Aborting: GitHub API is unusable. Fix the issue above and re-run." >&2
        exit 2
    fi
    if [ $rc -ne 0 ] || [ -z "$sha" ]; then
        FAILED=$((FAILED + 1))
        continue
    fi

    new_full="${repo_full}@${sha} # ${target_tag}"
    new_content=$(echo "$content" \
        | sed -E "s|${repo_full//\//\\/}@[^[:space:]\"#]+([[:space:]]*#[^\n]*)?|${new_full//\//\\/}|")

    if [ "$content" = "$new_content" ]; then
        echo "    · no change needed"
        continue
    fi

    echo "    → @${sha:0:12}…  # $target_tag"

    if [ $DRY_RUN -eq 0 ]; then
        esc_new=$(printf '%s' "$new_content" | sed 's/[\\&|]/\\&/g')
        sed -i.bak "${lineno}s|.*|${esc_new}|" "$workflow"
        rm -f "${workflow}.bak"
    fi
    PINNED=$((PINNED + 1))

done < <(grep -RnE '^[[:space:]]*-?[[:space:]]*uses:[[:space:]]+[^.#[:space:]][^[:space:]]*@' "$WORKFLOWS_DIR")

echo
echo "Done."
echo "  Scanned: $TOTAL"
echo "  Pinned:  $PINNED"
[ $FAILED -gt 0 ] && echo "  Failed:  $FAILED   ← re-run with --verbose to see why"
[ $DRY_RUN -eq 1 ] && echo "  (dry run — re-run without --dry-run to apply)"

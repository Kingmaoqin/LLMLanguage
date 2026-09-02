#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
results_root="$repo_root/results"
output="$repo_root/project_archive/manifests/LOCAL_RESULTS_INVENTORY.csv"

mkdir -p "$(dirname "$output")"
tmp_output="$(mktemp "$(dirname "$output")/.results-inventory.XXXXXX")"
trap 'rm -f "$tmp_output"' EXIT

printf 'path,bytes,sha256\n' > "$tmp_output"

if [[ -d "$results_root" ]]; then
  while IFS= read -r -d '' result_file; do
    relative_path="${result_file#"$repo_root/"}"
    bytes="$(stat -c '%s' "$result_file")"
    digest="$(sha256sum "$result_file" | cut -d ' ' -f 1)"
    printf '"%s",%s,%s\n' "$relative_path" "$bytes" "$digest" >> "$tmp_output"
  done < <(find "$results_root" -type f -print0 | LC_ALL=C sort -z)
fi

mv "$tmp_output" "$output"
trap - EXIT

printf 'Wrote %s\n' "$output"

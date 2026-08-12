#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_root="$repo_root/logs"
archive_root="$repo_root/logs_archive"
manifest="$archive_root/MANIFEST.csv"

mkdir -p "$archive_root"
tmp_manifest="$(mktemp "$archive_root/.manifest.XXXXXX")"
trap 'rm -f "$tmp_manifest"' EXIT

printf 'source_path,source_bytes,source_sha256,archive_path,archive_bytes,archive_sha256\n' > "$tmp_manifest"

if [[ -d "$source_root" ]]; then
  while IFS= read -r -d '' source_file; do
    relative_path="${source_file#"$repo_root/"}"
    archive_path="$archive_root/${relative_path#logs/}.gz"
    mkdir -p "$(dirname "$archive_path")"

    tmp_archive="${archive_path}.tmp"
    gzip -n -9 -c "$source_file" > "$tmp_archive"
    mv "$tmp_archive" "$archive_path"

    source_bytes="$(stat -c '%s' "$source_file")"
    archive_bytes="$(stat -c '%s' "$archive_path")"
    source_sha256="$(sha256sum "$source_file" | cut -d ' ' -f 1)"
    archive_sha256="$(sha256sum "$archive_path" | cut -d ' ' -f 1)"
    printf '"%s",%s,%s,"%s",%s,%s\n' \
      "$relative_path" \
      "$source_bytes" \
      "$source_sha256" \
      "${archive_path#"$repo_root/"}" \
      "$archive_bytes" \
      "$archive_sha256" >> "$tmp_manifest"
  done < <(find "$source_root" -type f -name '*.log' -print0 | LC_ALL=C sort -z)
fi

mv "$tmp_manifest" "$manifest"
trap - EXIT

printf 'Wrote %s\n' "$manifest"

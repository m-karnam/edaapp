set -euo pipefail

target="$(pwd)/bottom_toolbar"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

commit="4584f841538310a71b318afd83762184e62c66c3"
archive_dir="$tmp/bottom-toolbar-app-$commit"

curl -fsSL "https://github.com/eda-labs/bottom-toolbar-app/archive/$commit.tar.gz" \
-o "$tmp/repo.tar.gz"

tar -xzf "$tmp/repo.tar.gz" -C "$tmp"

source="$archive_dir/bottom_toolbar"

rm -rf "$target/api" "$target/intents" "$target/manifest.yaml"
cp -a "$source/api" "$target/api"
cp -a "$source/intents" "$target/intents"
cp -a "$source/manifest.yaml" "$target/manifest.yaml"

manifest_tmp="$tmp/manifest.yaml"
sed 's/author: eda-labs/author: demo/' \
    "$target/manifest.yaml" > "$manifest_tmp"
mv "$manifest_tmp" "$target/manifest.yaml"

printf 'Downloaded files into %s\n' "$target"
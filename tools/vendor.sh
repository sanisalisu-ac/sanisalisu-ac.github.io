#!/usr/bin/env bash
# Copies KaTeX and the two web fonts from npm into assets/vendor/ so the site
# loads no third-party scripts or fonts. Run by the build workflow; safe to run locally.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"
( cd "$tmp" && npm pack --silent katex@0.16 @fontsource/spectral@5 @fontsource/public-sans@5 >/dev/null )
for t in "$tmp"/*.tgz; do mkdir -p "${t%.tgz}" && tar -xzf "$t" -C "${t%.tgz}"; done
K="$(ls -d "$tmp"/katex-*/package)"
mkdir -p assets/vendor/katex/fonts assets/vendor/fonts
cp "$K/dist/katex.min.css" "$K/dist/katex.min.js" assets/vendor/katex/
cp "$K/dist/contrib/auto-render.min.js" assets/vendor/katex/
cp "$K"/dist/fonts/*.woff2 assets/vendor/katex/fonts/
for pkg in spectral public-sans; do
  P="$(ls -d "$tmp"/fontsource-$pkg-*/package)"
  cp "$P"/files/$pkg-latin-*.woff2 "$P"/files/$pkg-latin-ext-*.woff2 assets/vendor/fonts/ 2>/dev/null || true
done
rm -rf "$tmp"
echo "vendored: $(ls assets/vendor/katex | wc -l) KaTeX files, $(ls assets/vendor/fonts | wc -l) font files"

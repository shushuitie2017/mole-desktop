#!/usr/bin/env bash
# SEO 闸：对公网 URL 跑 seo.bluecatbot.com 体检，打印逐项清单；分数 < 阈值或有 fail → 退非零。
# 用法: seo-check.sh <url|subdomain> [min_score]
#   例: seo-check.sh learn.bluecatbot.com
#       seo-check.sh https://learn.bluecatbot.com/ 95
# 上线/更新既有站后必跑（bluecat-deploy §5）。体检 API 不可达时 fail-open（退 0 不挡活）。
set -u
URL="${1:-}"
MIN="${2:-90}"
if [ -z "$URL" ]; then echo "用法: seo-check.sh <url|subdomain> [min_score]"; exit 2; fi
case "$URL" in http*) ;; *) URL="https://$URL" ;; esac

PY="$(command -v python3 || command -v python)"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/seocheck.$$.json")"

if ! curl -s --max-time 25 "https://seo.bluecatbot.com/api/audit?url=${URL}" -o "$TMP"; then
  echo "[seo-check] 体检 API 不可达，跳过（fail-open）"; rm -f "$TMP"; exit 0
fi
"$PY" "$HERE/_seo_check.py" "$TMP" "$MIN" "$URL"; rc=$?
rm -f "$TMP"
exit $rc

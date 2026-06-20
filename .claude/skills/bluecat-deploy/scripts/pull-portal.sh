#!/usr/bin/env bash
# 拉服务器门户 index.html 到本地固定文件夹。
# 改门户卡片【之前】必跑：服务器是权威（可能被直接改过/被 seo_inject 改过），先拉再改避免覆盖最新版。
#
#   bash pull-portal.sh [本地目标 index.html 路径]
#   默认目标：C:/Users/1/Desktop/note/server-projects/website-main/index.html
#   连接默认 chi，可用环境变量覆盖：BLUECAT_KEY / BLUECAT_SRV / BLUECAT_PORTAL
set -e
KEY="${BLUECAT_KEY:-C:/Users/1/Downloads/Polymarketchi.pem}"
SRV="${BLUECAT_SRV:-ubuntu@57.181.215.147}"
REMOTE="${BLUECAT_PORTAL:-/home/ubuntu/website-main/index.html}"
LOCAL="${1:-C:/Users/1/Desktop/note/server-projects/website-main/index.html}"

mkdir -p "$(dirname "$LOCAL")"
scp -i "$KEY" "$SRV:$REMOTE" "$LOCAL"
echo "✓ 已拉取服务器 live 版 → $LOCAL"
echo "  现在编辑它（在 .grid 末尾加卡片 + 三个 i18n 字典加 <key>），改完跑 push-portal.sh 回推。"

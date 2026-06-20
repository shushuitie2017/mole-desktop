#!/usr/bin/env bash
# 备份服务器旧版 + 回推本地 index.html。改完门户卡片【之后】跑。
#
#   bash push-portal.sh [本地 index.html 路径] [备份标签/卡片key]
#   默认本地：C:/Users/1/Desktop/note/server-projects/website-main/index.html
#   默认标签：update（建议传卡片 key，如 seoaudit，便于回滚定位）
#   连接默认 chi，可用 BLUECAT_KEY / BLUECAT_SRV / BLUECAT_PORTAL 覆盖
set -e
KEY="${BLUECAT_KEY:-C:/Users/1/Downloads/Polymarketchi.pem}"
SRV="${BLUECAT_SRV:-ubuntu@57.181.215.147}"
REMOTE="${BLUECAT_PORTAL:-/home/ubuntu/website-main/index.html}"
LOCAL="${1:-C:/Users/1/Desktop/note/server-projects/website-main/index.html}"
TAG="${2:-update}"

[ -f "$LOCAL" ] || { echo "✗ 找不到本地文件：$LOCAL"; exit 1; }
TS=$(date +%Y%m%d_%H%M%S)
ssh -i "$KEY" "$SRV" "cp '$REMOTE' '${REMOTE}.bak.before-${TAG}-${TS}' && echo '✓ 服务器已备份: ${REMOTE}.bak.before-${TAG}-${TS}'"
scp -i "$KEY" "$LOCAL" "$SRV:$REMOTE"
echo "✓ 已回推 $LOCAL → 服务器"
echo "  线上验证：curl -s https://bluecatbot.com | grep -E '$TAG'"

---
name: bluecat-deploy
description: >-
  把一个新站点部署上线到 bluecatbot 服务器（chi）并自动接入门户导航：选子域名/端口 →
  tar+build+systemd（动态站）或静态产物→nginx root（静态站）→ nginx 子域名 + certbot SSL →
  拉门户 website-main/index.html、加一张三语卡片、备份回推 → 自检 SEO → 验证 → 提交。
  当用户要「发布/部署一个新站」「上 *.bluecatbot.com 新子域名」「给门户/主站加卡片」
  「让新站走这套上线流程」时使用。务必遵守安全不变量（连接信息读 servers.json、
  门户先拉后改先备份再推、只动本站服务+新增 nginx 站、绝不把 servers.json/.env/.pem/HANDOFF 推公开仓库）。
metadata:
  tier: opt-in
  cost: medium
  side_effects: write
---

# bluecat-deploy — 新站上线 + 门户接入 全流程

逐阶段照做。目标：把一个本地项目部署到 chi 服务器、绑一个 `<sub>.bluecatbot.com` 子域名+HTTPS、
并在门户 `bluecatbot.com` 自动加一张三语卡片。**连接信息一律读项目根的 `servers.json`，本文件不写明文密钥。**

## 0. 关键不变量（务必遵守）
- **连接信息**：读项目根 `servers.json`（`host/user/key/remote_dir`）。统一服务器 = **chi**。本文件/仓库不写 IP/key。
- **门户改动三步铁律**：**先拉**服务器 live `index.html` → 改 → **先备份**服务器旧版 → **再回推**。绝不用可能过期的本地副本直接覆盖。
- **只动本站**：只 `systemctl restart` 新站自己的服务、只**新增**一个 nginx 站点；不碰其它站/证书/nginx 全局。
- **绝不进公开仓库**：`servers.json`/`.env*`/`*.pem`/`HANDOFF.md`/`credentials.*`。私有仓库经用户同意可含 `servers.json`/`HANDOFF.md`（先用 GitHub API 核 `private`，public 则排除）。
- git 提交/PR **无任何 Claude/AI 署名**。

## 1. 准备（DNS + 端口）
- **子域名**：`<sub>.bluecatbot.com`。`*.bluecatbot.com` 已解析到 chi（实测新子域直接可用），用前确认：
  `python -c "import socket;print(socket.gethostbyname('<sub>.bluecatbot.com'))"` 应回服务器 IP。
- **空闲端口**（动态站需要）：`ssh chi 'sudo ss -tlnp | grep :<port>'`，空则用。已占用示例：3010/8360(trending+waline)、3005(seo)、3002/3003/3900/2567/4444/8001/8002/8085/8090/5003/5005/5006/5013/8877/8888 等。新站常用 3006/3007/3015…。
- **仓库**（可选）：要同步远程则确认 `shushuitie2017/<repo>` 存在（GitHub API 404=private/新建）。

## 2. 部署代码
**A. 动态站（Next.js/Node）**
```
# 本地打 tar（排除产物与机密）
tar czf <tmp>.tgz --force-local --exclude=./node_modules --exclude=./.next --exclude=./.git \
  --exclude=./servers.json --exclude='./.env*' .
scp -i <key> <tmp>.tgz <user>@<host>:/tmp/   # 连接读 servers.json
# 服务器：解压 → 安装 → 构建
ssh chi 'mkdir -p <remote_dir>; cd <remote_dir>; tar xzf /tmp/<tmp>.tgz; npm install --no-audit --no-fund; npm run build'
```
建 systemd（`/etc/systemd/system/<name>.service`，端口 <port>）：
```
[Unit]
Description=<Name> (Next.js)
After=network.target
[Service]
WorkingDirectory=<remote_dir>
Environment=NODE_ENV=production
EnvironmentFile=-<remote_dir>/.env          # 有则加载, 无则忽略(前缀 -)
ExecStart=/usr/bin/node node_modules/.bin/next start -p <port>
Restart=always
RestartSec=5
User=ubuntu
[Install]
WantedBy=multi-user.target
```
`sudo systemctl daemon-reload && sudo systemctl enable --now <name>.service`，`curl 127.0.0.1:<port>` 探活。

**B. 纯静态站**：本地 build → `scp` 产物到 nginx root（如 `/home/ubuntu/<name>`）。SEO 注入参考 `_seo_static/seo_inject.py`（日语优先 head）。

## 3. nginx 子域名 + SSL
建 `/etc/nginx/sites-available/<sub>.bluecatbot.com`：
```
server {
  listen 80;
  server_name <sub>.bluecatbot.com;
  client_max_body_size 8m;
  location / {                      # 静态站改为: root <nginx_root>; index index.html;
    proxy_pass http://127.0.0.1:<port>;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";
    proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme; proxy_read_timeout 60s;
  }
}
```
```
sudo ln -sf /etc/nginx/sites-available/<sub>.bluecatbot.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d <sub>.bluecatbot.com --non-interactive --agree-tos -m chiangbao2020@gmail.com --redirect
```
certbot 会自动加 443 块 + http→https 跳转。**只对新子域，不动别的。**

## 4. 门户卡片（自动接入主站）— 先拉后改先备份再推
> ⚠️ **门户是三套独立静态页，不是 JS 切换**（旧 `data-i18n`+字典写法已废弃，别再找 translations 字典）：
> 中文 `chi:/home/ubuntu/website-main/index.html`、英文 `…/en/index.html`、日文 `…/ja/index.html`
> （对应 bluecatbot.com/ 、/en/ 、/ja/）。**三个文件都要改，漏一个就缺那门语言的卡片。**
> 本地固定文件夹：`server-projects/website-main/{index.html, en/index.html, ja/index.html}`。
> 版式 = **时间轴卡片**：按一天时段分 7 个 `<section id=dawn|morning|noon|afternoon|dusk|night|latenight>`，各含一个 `.grid`。

1. **先拉**三个文件：`scp` 三个 `index.html` 到本地对应位置。
2. **选区**：按站点用途挑最贴合的时段 section（如阅读/内容类→`dusk` 黄昏「把想读的书先翻开」）；在该 section 的 `.grid` 末尾（`</div>` 前）加卡片。**与现有卡片同格式**：
   ```html
   <a class="card" href="https://<sub>.bluecatbot.com" target="_blank" rel="noopener">
     <div class="card-top"><div class="card-glyph"><svg class="icon"><use href="#i-<icon>"/></svg></div><div><div class="card-name"><Name></div><div class="card-tag"><Cat · Sub></div></div></div>
     <p class="card-act"><一句话描述></p>
     <div class="card-url"><span><sub>.bluecatbot.com</span><span class="arr">→</span></div>
   </a>
   ```
   - **三个文件加同一张卡片**：`card-name`/`card-tag`/icon/href 三语一致，**只有 `<p class="card-act">` 按 zh/en/ja 各自翻译**（参照同区现有卡片的本地化风格）。
   - 图标 `#i-<icon>` 用门户已有的 symbol（`grep -oE 'id="i-[a-z]+"' index.html`，如 i-bookopen/i-scroll/i-globe/i-news…），别造新 id。
   - **不动 `<head>`**（门户 SEO 已完整：canonical/hreflang/OG/JSON-LD）。
3. **回推**：每个文件先在服务器 `cp` 备份（`index.html.bak.before-<key>`）再 `scp` 回，三个都推。
4. **线上验证三语**：`for p in / /en/ /ja/; do echo -n "$p "; curl -s https://bluecatbot.com$p | grep -c '<sub>.bluecatbot.com'; done`（各应 = 2）。

## 5. SEO 自检（**必跑 gate**，不只新站——既有站每次结构/内容更新如加多语言也要重跑）
**上线/更新后必跑这道闸，过了才算 done**（别凭记忆只补 canonical+OG 就过）：
```bash
bash ~/.claude/skills/bluecat-deploy/scripts/seo-check.sh <sub>.bluecatbot.com   # score<90 或有 fail → 退非零=未过闸
```
它调 `https://seo.bluecatbot.com/api/audit?url=` 拿分并逐项打印。**整张清单都要到位**：
`favicon`、`<title>`(10–60)、`description`(50–160)、`canonical`、Open Graph、**`og:image`**（真生成，非死链；无图像工具时用 chrome-devtools 渲染品牌卡 1200×630 截图）、**`hreflang`**（多语言站；且页面要真按 `?lang=` 渲染，否则 URL 是死的）、**`robots.txt`**、**`sitemap.xml`**、**JSON-LD**、`viewport` **不能有 `maximum-scale`**（禁缩放扣移动端分）。
- **Flask 静态站**：`robots.txt`/`sitemap.xml`/`og-cover.png` 放 `static/` + `app.py` 加根路由（带正确 MIME）。
- **Next.js**：`app/layout.tsx`/`app/sitemap.ts`/`app/robots.ts` + 各 page `generateMetadata`（参考 `seo-audit` 项目的三语+hreflang）。
> 手动 tar/scp 部署会绕过本 skill 的注入/遥测——`hooks/seo-deploy-reminder.py`（PreToolUse）在检测到往 chi 的部署命令时会非阻塞提醒跑上面这道闸，别忽略。实证：learn.bluecatbot.com 漏了 og:image/hreflang/robots/sitemap/JSON-LD + viewport 禁缩放，外部体检只 74 分；补齐后 97（详见本 skill LESSONS.md）。

## 6. 验证清单
- `curl -o /dev/null -w '%{http_code}'` 对 `https://<sub>.bluecatbot.com/` = 200；`http://` = 301→https；`openssl s_client` 证书 CN 对。
- `systemctl is-active <name>.service` = active。
- 门户 `https://bluecatbot.com` 出现新卡片（三语切换正常）。

## 7. 提交远程（如有仓库）
`git add -A`（确认 `servers.json`/`.env`/`.pem`/`HANDOFF.md` 未暂存）→ `git commit -m "<type(scope): 描述>"`（无 AI 署名）→ `git push`。

## 相关文件
- `scripts/pull-portal.sh` / `scripts/push-portal.sh`：门户「先拉 / 备份+回推」一键脚本（连接默认 chi，可用 `BLUECAT_KEY`/`BLUECAT_SRV`/`BLUECAT_PORTAL` 环境变量覆盖）。
- `references/card-template.html`：门户卡片 + 三语 i18n 模板。
- 连接信息：各项目根 `servers.json`（gitignored）。
- 同生态参考流程：`gh-trending-archive` 项目的 `trending-pipeline` skill（数据/部署）、`_seo_static/seo_inject.py`（静态站 SEO 注入）。

---
name: mole-desktop-site
description: Mole 官网 mole.bluecatbot.com 部署（chi 静态站）+ GitHub Release/发布流程
metadata: 
  node_type: memory
  type: project
  originSessionId: 4bb8120e-c0db-4cf6-bea9-2c8ff7ef94e9
---

[[mole-desktop]] 的官网与发布渠道已上线。

- **官网**：https://mole.bluecatbot.com （暗色 trading-terminal 落地页，突出六合一/零依赖/安全护栏，含 App 截图 + 下载按钮）。源码在 repo 的 `site/`（index.html + assets/shot-*.png）。
- **下载链接**：https://mole.bluecatbot.com/downloads/Mole-Setup-1.0.0.exe （94MB，nginx `/downloads/` 强制 Content-Disposition attachment）。
- **GitHub Release**：https://github.com/shushuitie2017/mole-desktop/releases/tag/v1.0.0 含 Mole-Setup-1.0.0.exe + .blockmap + latest.yml（electron-updater 自动更新可用；注意 electron-builder 把空格名转连字符 `Mole-Setup-1.0.0.exe`，资产名须与 latest.yml 一致）。

**部署模式（chi = 57.181.215.147，bluecatbot 服务器）：**
- SSH：`ssh -i C:/Users/1/Downloads/Polymarketchi.pem ubuntu@57.181.215.147`（servers.json 记录，含密钥路径，已 gitignore 不进仓库）。
- `*.bluecatbot.com` 已泛解析到本机，新子域 DNS 无需手动加。
- 静态站模式：文件放 `/home/ubuntu/<site>/`，nginx server block `root` 该目录 + `try_files`，`/downloads/` 加 `add_header Content-Disposition attachment`；HTTPS 用 `sudo certbot --nginx -d <子域> --non-interactive --agree-tos --redirect`（每子域独立证书，ubuntu 有免密 sudo）。
- 站点目录：`/home/ubuntu/mole-site/`（index.html + assets/ + downloads/）。

**发 Release/上传资产**（无 gh CLI，用 token + API）：token 在 `~/.git-credentials`（`ghp_...`）；建 release 用 PowerShell `Invoke-RestMethod`（curl 的 `--data @/tmp` 在 Git Bash 路径不通）；传资产 POST 到 `https://uploads.github.com/repos/<o>/<r>/releases/<id>/assets?name=<f>` 带 `-InFile`。

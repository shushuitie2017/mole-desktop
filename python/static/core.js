// Mole Web Console - 核心框架 (i18n / 导航 / 工具)
"use strict";

const MOLE = {
    lang: "zh",
    LANG: { zh: {}, en: {}, ja: {} },
    views: {},
    current: null,

    // ---- i18n ----
    addStrings(obj) {
        for (const lg of ["zh", "en", "ja"]) {
            Object.assign(this.LANG[lg], obj[lg] || {});
        }
    },
    t(key) {
        const v = this.LANG[this.lang][key];
        return v != null ? v : key;
    },

    // ---- 工具 ----
    $(id) { return document.getElementById(id); },
    escapeHtml(s) {
        const d = document.createElement("div");
        d.textContent = s == null ? "" : String(s);
        return d.innerHTML;
    },
    fmtSize(bytes) {
        if (!bytes || bytes <= 0) return "0";
        const u = ["B", "KB", "MB", "GB", "TB"];
        let i = 0, n = bytes;
        while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
        return (n >= 100 || i === 0 ? n.toFixed(0) : n.toFixed(1)) + u[i];
    },
    fmtRate(bps) { return MOLE.fmtSize(bps) + "/s"; },

    // 统一的 SSE 封装: onItem/onDone/onMsg
    sse(url, { onMsg, onDone, onError } = {}) {
        if (this._es) { try { this._es.close(); } catch (e) {} }
        const es = new EventSource(url);
        this._es = es;
        es.onmessage = ev => {
            const m = JSON.parse(ev.data);
            if (m.type === "done") { es.close(); if (onDone) onDone(m); }
            else if (onMsg) onMsg(m);
        };
        es.onerror = () => { es.close(); if (onError) onError(); };
        return es;
    },
    closeSse() { if (this._es) { try { this._es.close(); } catch (e) {} this._es = null; } },

    // ---- 视图注册 / 切换 ----
    registerView(name, obj) { this.views[name] = obj; },

    switchTo(name) {
        if (this.current === name) return;
        if (this.current && this.views[this.current] && this.views[this.current].hide) {
            this.views[this.current].hide();
        }
        document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.view === name));
        document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + name));
        this.current = name;
        const view = this.views[name];
        const el = this.$("view-" + name);
        if (view) {
            if (!view._inited) { view.render(el); view._inited = true; }
            if (view.show) view.show();
        }
    },

    applyStaticI18n() {
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const k = el.getAttribute("data-i18n");
            const v = this.LANG[this.lang][k];
            if (typeof v === "string") el.textContent = v;
        });
        document.documentElement.lang = this.lang;
    },

    setLang(lg) {
        this.lang = lg;
        document.querySelectorAll("#langSwitch button").forEach(b =>
            b.classList.toggle("active", b.dataset.lang === lg));
        this.applyStaticI18n();
        // 重新渲染当前视图 (各视图自行保留状态)
        for (const name in this.views) {
            const v = this.views[name];
            if (v._inited) v.render(this.$("view-" + name));
        }
        const cur = this.views[this.current];
        if (cur && cur.show) cur.show();
    },

    async start() {
        // 顶层静态文案
        this.addStrings({
            zh: { tagline: "Windows 维护可视化控制台",
                  tab_clean: "清理", tab_purge: "项目产物", tab_status: "系统监控",
                  tab_analyze: "磁盘浏览", tab_optimize: "系统优化", tab_uninstall: "应用卸载",
                  scan: "扫描", scanning: "扫描中…", refresh: "刷新",
                  preview: "仅预览（不删除）", admin: "管理员", noAdmin: "非管理员",
                  empty: "无数据", loading: "加载中…" },
            en: { tagline: "Windows maintenance console",
                  tab_clean: "Clean", tab_purge: "Artifacts", tab_status: "Monitor",
                  tab_analyze: "Disk", tab_optimize: "Optimize", tab_uninstall: "Uninstall",
                  scan: "Scan", scanning: "Scanning…", refresh: "Refresh",
                  preview: "Preview only (no delete)", admin: "Admin", noAdmin: "Not admin",
                  empty: "No data", loading: "Loading…" },
            ja: { tagline: "Windows メンテナンスコンソール",
                  tab_clean: "クリーン", tab_purge: "成果物", tab_status: "モニター",
                  tab_analyze: "ディスク", tab_optimize: "最適化", tab_uninstall: "アンインストール",
                  scan: "スキャン", scanning: "スキャン中…", refresh: "更新",
                  preview: "プレビューのみ（削除なし）", admin: "管理者", noAdmin: "非管理者",
                  empty: "データなし", loading: "読込中…" },
        });
        this.applyStaticI18n();

        // 版本
        try {
            const v = await (await fetch("/api/version")).json();
            const badge = v.is_admin ? "" : "";
            this.$("version").textContent = "v" + v.version;
        } catch (e) {}

        // 更新相关文案
        this.addStrings({
            zh: { upd_check: "检查更新", upd_checking: "检查中…", upd_latest: "已是最新版本",
                  upd_found: "发现新版本", upd_download: "下载更新", upd_downloading: "下载中",
                  upd_downloaded: "下载完成，点击重启安装", upd_restart: "重启安装",
                  upd_error: "检查失败", upd_dev: "开发模式不检查更新" },
            en: { upd_check: "Check update", upd_checking: "Checking…", upd_latest: "Up to date",
                  upd_found: "Update available", upd_download: "Download", upd_downloading: "Downloading",
                  upd_downloaded: "Downloaded — click to restart & install", upd_restart: "Restart & install",
                  upd_error: "Check failed", upd_dev: "Dev mode (no update check)" },
            ja: { upd_check: "更新確認", upd_checking: "確認中…", upd_latest: "最新です",
                  upd_found: "新バージョンあり", upd_download: "ダウンロード", upd_downloading: "ダウンロード中",
                  upd_downloaded: "完了。クリックで再起動してインストール", upd_restart: "再起動して更新",
                  upd_error: "確認失敗", upd_dev: "開発モード" },
        });

        // 事件
        this.$("tabs").addEventListener("click", e => {
            const b = e.target.closest(".tab");
            if (b) this.switchTo(b.dataset.view);
        });
        this.$("langSwitch").addEventListener("click", e => {
            const b = e.target.closest("button");
            if (b) this.setLang(b.dataset.lang);
        });

        this.setupUpdates();

        // 默认视图
        this.switchTo("clean");
    },

    // ---- 更新检查 UI (仅 Electron 桌面版有 electronAPI) ----
    setupUpdates() {
        const A = window.electronAPI;
        if (!A || !A.checkForUpdate) return;   // 纯 web 版无此能力, 不显示按钮

        const right = document.querySelector(".topbar-right");
        const btn = document.createElement("button");
        btn.id = "checkUpdate";
        btn.className = "upd-btn";
        btn.setAttribute("data-i18n", "upd_check");
        btn.textContent = this.t("upd_check");
        right.insertBefore(btn, this.$("langSwitch"));

        const toast = document.createElement("div");
        toast.id = "updToast";
        toast.className = "upd-toast";
        document.body.appendChild(toast);

        const reset = () => { btn.disabled = false; btn.textContent = MOLE.t("upd_check"); };
        const msg = (text, ms) => {
            toast.innerHTML = `<span>${MOLE.escapeHtml(text)}</span>`;
            toast.classList.add("show");
            if (ms) setTimeout(() => toast.classList.remove("show"), ms);
        };

        btn.addEventListener("click", async () => {
            btn.disabled = true; btn.textContent = MOLE.t("upd_checking");
            msg(MOLE.t("upd_checking"));
            let r;
            try { r = await A.checkForUpdate(); } catch (e) { r = { ok: false, error: String(e) }; }
            if (r && r.dev) { msg(MOLE.t("upd_dev"), 3000); reset(); }
            else if (r && r.ok === false) { msg(MOLE.t("upd_error") + (r.error ? ": " + r.error : ""), 6000); reset(); }
            // r.ok === true → 由 update:available / update:none 事件接管
        });

        A.onUpdateNone(() => { msg(MOLE.t("upd_latest"), 4000); reset(); });
        A.onUpdateError(d => { msg(MOLE.t("upd_error") + (d && d.msg ? ": " + d.msg : ""), 6000); reset(); });
        A.onUpdateAvailable(d => {
            reset();
            toast.innerHTML = `<span>${MOLE.t("upd_found")} v${MOLE.escapeHtml(d.version)}</span>` +
                `<button class="upd-act" id="updDl">${MOLE.t("upd_download")}</button>`;
            toast.classList.add("show");
            toast.querySelector("#updDl").addEventListener("click", () => { A.downloadUpdate(); msg(MOLE.t("upd_downloading") + " 0%"); });
        });
        A.onUpdateProgress(d => { msg(MOLE.t("upd_downloading") + " " + Math.round(d.percent || 0) + "%"); });
        A.onUpdateDownloaded(d => {
            toast.innerHTML = `<span>v${MOLE.escapeHtml(d.version)} ${MOLE.t("upd_downloaded")}</span>` +
                `<button class="upd-act" id="updInst">${MOLE.t("upd_restart")}</button>`;
            toast.classList.add("show");
            toast.querySelector("#updInst").addEventListener("click", () => A.installUpdate());
        });
    },
};

window.MOLE = MOLE;

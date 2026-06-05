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

        // 事件
        this.$("tabs").addEventListener("click", e => {
            const b = e.target.closest(".tab");
            if (b) this.switchTo(b.dataset.view);
        });
        this.$("langSwitch").addEventListener("click", e => {
            const b = e.target.closest("button");
            if (b) this.setLang(b.dataset.lang);
        });

        // 默认视图
        this.switchTo("clean");
    },
};

window.MOLE = MOLE;

// Uninstall 视图 - 应用清单 + 卸载
(function () {
"use strict";
const M = window.MOLE;

M.addStrings({
    zh: { u_title: "已安装应用清单", u_refresh: "刷新清单", u_search: "搜索应用…",
          u_count: n => `共 ${n} 个应用`, u_uninstall: "卸载",
          u_confirm: n => `将启动「${n}」自带的卸载程序，请在弹出的原生界面中确认。继续？`,
          u_started: "已启动卸载程序", u_size: "大小", u_unknown: "未知",
          u_note: "卸载会调用应用自带的卸载器（非静默），由你在原生窗口确认；系统组件/驱动已自动过滤。" },
    en: { u_title: "Installed applications", u_refresh: "Refresh", u_search: "Search apps…",
          u_count: n => `${n} apps`, u_uninstall: "Uninstall",
          u_confirm: n => `Launch the native uninstaller for "${n}". Confirm in its window. Continue?`,
          u_started: "Uninstaller launched", u_size: "Size", u_unknown: "unknown",
          u_note: "Uninstall launches the app's own (non-silent) uninstaller; system components/drivers are filtered out." },
    ja: { u_title: "インストール済みアプリ", u_refresh: "更新", u_search: "アプリ検索…",
          u_count: n => `${n} 個`, u_uninstall: "削除",
          u_confirm: n => `「${n}」の標準アンインストーラを起動します。表示される画面で確認してください。続行？`,
          u_started: "アンインストーラ起動", u_size: "サイズ", u_unknown: "不明",
          u_note: "アプリ標準の（非サイレント）アンインストーラを起動します。システム部品/ドライバは除外。" },
});

let apps = [], loaded = false, filter = "";

function render(el) {
    el.innerHTML = `
      <h2 class="view-title">${M.t("u_title")}</h2>
      <div class="actionbar">
        <button class="btn btn-primary" id="un-refresh">${M.t("u_refresh")}</button>
        <input class="path-input" id="un-search" placeholder="${M.t("u_search")}" value="${M.escapeHtml(filter)}">
        <div class="spacer"></div>
        <span class="totals-label" id="un-count"></span>
      </div>
      <p class="hint">${M.t("u_note")}</p>
      <div class="app-list" id="un-list">${loaded ? "" : `<p class="placeholder">${M.t("loading")}</p>`}</div>`;
    el.querySelector("#un-refresh").addEventListener("click", () => loadList(true));
    el.querySelector("#un-search").addEventListener("input", e => { filter = e.target.value.toLowerCase(); paint(); });
    if (!loaded) loadList(false); else paint();
}

function loadList(force) {
    const list = M.$("un-list"); if (list) list.innerHTML = `<p class="placeholder">${M.t("loading")}</p>`;
    fetch("/api/uninstall/list").then(r => r.json()).then(d => {
        apps = d.apps || []; loaded = true; paint();
    }).catch(() => { if (list) list.innerHTML = `<p class="placeholder">⚠ error</p>`; });
}

function paint() {
    const list = M.$("un-list"); if (!list) return;
    const shown = apps.filter(a => !filter || a.name.toLowerCase().includes(filter)
        || (a.publisher || "").toLowerCase().includes(filter));
    M.$("un-count").textContent = M.t("u_count")(shown.length);
    if (!shown.length) { list.innerHTML = `<p class="placeholder">${M.t("empty")}</p>`; return; }
    list.innerHTML = "";
    shown.forEach(a => {
        const row = document.createElement("div");
        row.className = "app-row";
        row.innerHTML =
            `<span class="app-main">
               <span class="app-name">${M.escapeHtml(a.name)}</span>
               <span class="app-meta">${M.escapeHtml(a.publisher || "")}${a.version ? " · " + M.escapeHtml(a.version) : ""}</span>
             </span>
             <span class="app-size">${a.size > 0 ? M.fmtSize(a.size) : "—"}</span>
             <button class="btn btn-danger sm" data-act="un">${M.t("u_uninstall")}</button>`;
        row.querySelector('[data-act="un"]').addEventListener("click", () => {
            if (!confirm(M.t("u_confirm")(a.name))) return;
            fetch("/api/uninstall/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ uninstall: a.uninstall }) })
                .then(r => r.json()).then(res => { alert(res.ok ? M.t("u_started") : (res.error || "failed")); });
        });
        list.appendChild(row);
    });
}

M.registerView("uninstall", { render });
})();

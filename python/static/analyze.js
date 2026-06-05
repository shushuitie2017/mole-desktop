// Analyze 视图 - 磁盘空间浏览器
(function () {
"use strict";
const M = window.MOLE;

M.addStrings({
    zh: { a_title: "磁盘空间浏览器", a_go: "前往", a_up: "上级", a_open: "在资源管理器打开",
          a_del: "删除", a_total: "合计", a_cleanable: "可清理",
          a_confirm: p => `确定永久删除：\n${p}\n此操作不可撤销。`, a_loading: "测量中…" },
    en: { a_title: "Disk space explorer", a_go: "Go", a_up: "Up", a_open: "Open in Explorer",
          a_del: "Delete", a_total: "Total", a_cleanable: "cleanable",
          a_confirm: p => `Permanently delete:\n${p}\nThis cannot be undone.`, a_loading: "Measuring…" },
    ja: { a_title: "ディスク容量エクスプローラー", a_go: "移動", a_up: "上へ", a_open: "エクスプローラーで開く",
          a_del: "削除", a_total: "合計", a_cleanable: "削除可", a_confirm: p => `削除しますか：\n${p}\n元に戻せません。`, a_loading: "計測中…" },
});

let cur = null;   // current path
let data = null;

function render(el) {
    el.innerHTML = `
      <h2 class="view-title">${M.t("a_title")}</h2>
      <div class="actionbar">
        <button class="btn" id="az-up">↑ ${M.t("a_up")}</button>
        <input class="path-input" id="az-path" placeholder="C:\\Users\\...">
        <button class="btn btn-primary" id="az-go">${M.t("a_go")}</button>
        <div class="spacer"></div>
        <div class="totals"><span class="totals-label">${M.t("a_total")}</span><span class="totals-val" id="az-tot">—</span></div>
      </div>
      <div class="az-list" id="az-list"><p class="placeholder">${M.t("loading")}</p></div>`;
    el.querySelector("#az-go").addEventListener("click", () => load(M.$("az-path").value));
    el.querySelector("#az-up").addEventListener("click", () => { if (data && data.parent) load(data.parent); });
    el.querySelector("#az-path").addEventListener("keydown", e => { if (e.key === "Enter") load(e.target.value); });
    load(cur);  // null -> 默认 USERPROFILE
}

function load(path) {
    const list = M.$("az-list"); if (!list) return;
    list.innerHTML = `<p class="placeholder">${M.t("a_loading")}</p>`;
    const url = "/api/analyze" + (path ? "?path=" + encodeURIComponent(path) : "");
    fetch(url).then(r => r.json()).then(d => {
        if (d.error) { list.innerHTML = `<p class="placeholder">⚠ ${M.escapeHtml(d.error)}</p>`; return; }
        data = d; cur = d.path;
        M.$("az-path").value = d.path;
        M.$("az-tot").textContent = M.fmtSize(d.total);
        M.$("az-up").disabled = !d.parent;
        paint(d);
    }).catch(() => { list.innerHTML = `<p class="placeholder">⚠ error</p>`; });
}

function paint(d) {
    const list = M.$("az-list");
    if (!d.entries.length) { list.innerHTML = `<p class="placeholder">${M.t("empty")}</p>`; return; }
    list.innerHTML = "";
    const max = d.entries[0].size || 1;
    d.entries.forEach(e => {
        const pct = d.total ? (e.size / d.total * 100) : 0;
        const barW = (e.size / max * 100);
        const row = document.createElement("div");
        row.className = "az-row" + (e.is_dir ? " dir" : "");
        row.innerHTML =
            `<span class="az-icon">${e.is_dir ? (e.cleanable ? "🧹" : "📁") : "📄"}</span>
             <span class="az-name">${M.escapeHtml(e.name)}</span>
             <span class="az-bar"><span class="az-bar-fill" style="width:${barW}%"></span></span>
             <span class="az-pct">${pct.toFixed(0)}%</span>
             <span class="az-size">${M.fmtSize(e.size)}</span>
             <span class="az-actions">
               <button class="mini" data-act="open" title="${M.t("a_open")}">⧉</button>
               <button class="mini danger" data-act="del" title="${M.t("a_del")}">✕</button>
             </span>`;
        row.querySelector(".az-name").addEventListener("click", () => { if (e.is_dir) load(e.path); });
        row.querySelector(".az-icon").addEventListener("click", () => { if (e.is_dir) load(e.path); });
        row.querySelector('[data-act="open"]').addEventListener("click", ev => {
            ev.stopPropagation();
            fetch("/api/analyze/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: e.path }) });
        });
        row.querySelector('[data-act="del"]').addEventListener("click", ev => {
            ev.stopPropagation();
            if (!confirm(M.t("a_confirm")(e.path))) return;
            fetch("/api/analyze/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: e.path }) })
                .then(r => r.json()).then(res => { if (res.ok) load(cur); else alert(res.error || "failed"); });
        });
        list.appendChild(row);
    });
}

M.registerView("analyze", { render });
})();

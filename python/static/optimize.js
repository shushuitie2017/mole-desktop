// Optimize 视图 - 系统优化
(function () {
"use strict";
const M = window.MOLE;

M.addStrings({
    zh: { o_title: "系统优化与修复", o_run: "运行选中", o_needAdmin: "需管理员",
          o_tweak: "调整", o_repair: "修复", o_check: "检查",
          o_confirm: n => `确定执行选中的 ${n} 项优化吗？部分操作会重启服务/清缓存。`,
          o_done: (ok, f) => `完成：成功 ${ok}，失败/跳过 ${f}`, o_adminHint: "需要管理员的项已置灰。", o_restartAdmin: "以管理员重启（解锁全部）" },
    en: { o_title: "System optimize & repair", o_run: "Run selected", o_needAdmin: "needs admin",
          o_tweak: "tweak", o_repair: "repair", o_check: "check",
          o_confirm: n => `Run the ${n} selected actions? Some restart services / clear caches.`,
          o_done: (ok, f) => `Done: ${ok} ok, ${f} failed/skipped`, o_adminHint: "Admin-only actions are greyed out.", o_restartAdmin: "Restart as admin (unlock all)" },
    ja: { o_title: "システム最適化と修復", o_run: "選択を実行", o_needAdmin: "管理者必要",
          o_tweak: "調整", o_repair: "修復", o_check: "確認",
          o_confirm: n => `選択した ${n} 項目を実行しますか？一部はサービス再起動/キャッシュ削除を行います。`,
          o_done: (ok, f) => `完了：成功 ${ok}、失敗/スキップ ${f}`, o_adminHint: "管理者が必要な項目はグレー表示です。", o_restartAdmin: "管理者で再起動（全機能）" },
});

let actions = [], isAdmin = false, loaded = false;

function kindLabel(k) { return k === "tweak" ? M.t("o_tweak") : k === "repair" ? M.t("o_repair") : M.t("o_check"); }

function render(el) {
    el.innerHTML = `
      <h2 class="view-title">${M.t("o_title")}</h2>
      <div class="actionbar">
        <button class="btn btn-primary" id="op-run" disabled>${M.t("o_run")}</button>
        <label class="chk preview-toggle"><input type="checkbox" id="op-dry" checked><span>${M.t("preview")}</span></label>
        <div class="spacer"></div>
        <span class="badge ${isAdmin ? "" : "warn"}" id="op-admin">${isAdmin ? M.t("admin") : M.t("noAdmin")}</span>
      </div>
      ${isAdmin ? "" : `<p class="hint">${M.t("o_adminHint")}${(window.electronAPI && window.electronAPI.restartAsAdmin) ? ` <a href="#" id="op-restart-admin" style="color:var(--acc);font-weight:600">${M.t("o_restartAdmin")} ↗</a>` : ""}</p>`}
      <div class="opt-list" id="op-list">${loaded ? "" : `<p class="placeholder">${M.t("loading")}</p>`}</div>
      <div class="result-banner" id="op-banner" style="display:none"></div>`;
    el.querySelector("#op-run").addEventListener("click", run);
    const ra = el.querySelector("#op-restart-admin");
    if (ra) ra.addEventListener("click", (e) => { e.preventDefault(); window.electronAPI.restartAsAdmin(); });
    if (!loaded) {
        fetch("/api/optimize/actions").then(r => r.json()).then(d => {
            actions = d.actions; isAdmin = d.is_admin; loaded = true; render(el);
        });
    } else paintList();
}

function paintList() {
    const list = M.$("op-list"); if (!list) return;
    list.innerHTML = "";
    actions.forEach(a => {
        const row = document.createElement("label");
        row.className = "opt-row" + (a.available ? "" : " disabled");
        row.dataset.id = a.id;
        row.innerHTML =
            `<input type="checkbox" class="opt-chk" ${a.available ? "checked" : "disabled"}>
             <span class="opt-body">
               <span class="opt-label">${M.escapeHtml(a.label[M.lang])}</span>
               <span class="opt-tags">
                 <span class="kind kind-${a.kind}">${kindLabel(a.kind)}</span>
                 ${a.admin ? `<span class="kind admin">${M.t("o_needAdmin")}</span>` : ""}
                 ${a.slow ? `<span class="kind slow">slow</span>` : ""}
               </span>
             </span>
             <span class="opt-result" data-result></span>`;
        list.appendChild(row);
    });
    list.querySelectorAll(".opt-chk").forEach(c => c.addEventListener("change", updateRun));
    updateRun();
}

function selected() {
    return [...document.querySelectorAll("#op-list .opt-row")]
        .filter(r => { const c = r.querySelector(".opt-chk"); return c.checked && !c.disabled; })
        .map(r => r.dataset.id);
}
function updateRun() { const b = M.$("op-run"); if (b) b.disabled = selected().length === 0; }

function run() {
    const ids = selected(); if (!ids.length) return;
    const dry = M.$("op-dry").checked;
    if (!dry && !confirm(M.t("o_confirm")(ids.length))) return;
    const btn = M.$("op-run"); btn.disabled = true;
    M.$("op-banner").style.display = "none";
    document.querySelectorAll("#op-list [data-result]").forEach(r => r.textContent = "");
    M.sse(`/api/optimize/run?dry=${dry ? 1 : 0}&ids=${encodeURIComponent(ids.join(","))}`, {
        onMsg: m => {
            if (m.type !== "item") return;
            const row = document.querySelector(`#op-list .opt-row[data-id="${m.id}"] [data-result]`);
            if (row) { row.textContent = (m.ok ? "✓ " : "✕ ") + (m.msg || ""); row.className = "opt-result " + (m.ok ? "ok" : "fail"); }
        },
        onDone: m => {
            btn.disabled = false;
            const b = M.$("op-banner");
            b.className = "result-banner " + (m.dry ? "preview" : "ok");
            b.innerHTML = M.t("o_done")(m.ok, m.fail);
            b.style.display = "";
        },
        onError: () => { btn.disabled = false; },
    });
}

M.registerView("optimize", { render });
})();

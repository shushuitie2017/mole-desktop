// Clean 视图 - 系统缓存清理
(function () {
"use strict";
const M = window.MOLE;

M.addStrings({
    zh: { c_title: "深度清理可再生缓存", c_scan: "扫描可回收空间", c_clean: "清理选中项",
          c_selectAll: "全选", c_selectedTotal: "已选可回收",
          c_confirm: (n, s) => `确定要永久删除选中的 ${n} 个类别（约 ${s}）吗？此操作不可撤销。`,
          c_previewDone: s => `预览完成：选中项可回收约 <b>${s}</b>（未删除任何文件）`,
          c_cleanDone: (s, n) => `清理完成：已释放 <b>${s}</b>，处理 ${n} 项`,
          c_fail: f => ` · ${f} 项失败`,
          free: "可用", used: "已用" },
    en: { c_title: "Deep-clean regenerable caches", c_scan: "Scan reclaimable", c_clean: "Clean selected",
          c_selectAll: "Select all", c_selectedTotal: "Selected reclaimable",
          c_confirm: (n, s) => `Permanently delete the ${n} selected categories (~${s})? Cannot be undone.`,
          c_previewDone: s => `Preview: ~<b>${s}</b> reclaimable (nothing deleted)`,
          c_cleanDone: (s, n) => `Done: freed <b>${s}</b>, ${n} items`,
          c_fail: f => ` · ${f} failed`,
          free: "free", used: "used" },
    ja: { c_title: "再生可能キャッシュを深掃除", c_scan: "回収可能をスキャン", c_clean: "選択項目を削除",
          c_selectAll: "全選択", c_selectedTotal: "選択中の回収可能",
          c_confirm: (n, s) => `選択した ${n} カテゴリ（約 ${s}）を完全に削除しますか？元に戻せません。`,
          c_previewDone: s => `プレビュー：約 <b>${s}</b> 回収可能（削除なし）`,
          c_cleanDone: (s, n) => `完了：<b>${s}</b> 解放、${n} 項目`,
          c_fail: f => ` · ${f} 件失敗`,
          free: "空き", used: "使用" },
});

let DATA = null, sizes = {}, counts = {}, scanned = false, loaded = false;

function fmtSize(b) { return M.fmtSize(b); }

function renderDiskInto(host) {
    if (!DATA) return;
    const pct = DATA.total ? (DATA.used / DATA.total * 100) : 0;
    host.innerHTML =
        `<div class="disk-meta">
           <span class="disk-drive">${M.escapeHtml(DATA.drive)}</span>
           <span class="disk-detail">${fmtSize(DATA.free)} ${M.t("free")} / ${fmtSize(DATA.total)} (${M.t("used")} ${pct.toFixed(0)}%)</span>
         </div>
         <div class="disk-bar"><div class="disk-bar-fill" style="width:${pct}%"></div></div>`;
}

function render(el) {
    el.innerHTML = `
      <h2 class="view-title" data-t="c_title"></h2>
      <div class="disk-card" id="cl-disk"></div>
      <div class="actionbar">
        <button class="btn btn-primary" id="cl-scan"></button>
        <button class="btn btn-danger" id="cl-clean" disabled></button>
        <label class="chk preview-toggle"><input type="checkbox" id="cl-dry" checked><span></span></label>
        <label class="chk"><input type="checkbox" id="cl-all" checked><span></span></label>
        <div class="spacer"></div>
        <div class="totals"><span class="totals-label" id="cl-seltot-lbl"></span><span class="totals-val" id="cl-seltot">—</span></div>
      </div>
      <div class="progress" id="cl-prog" style="display:none"><div class="progress-fill" id="cl-progfill"></div><span class="progress-text" id="cl-progtxt"></span></div>
      <div class="groups" id="cl-groups"></div>
      <div class="result-banner" id="cl-banner" style="display:none"></div>`;

    el.querySelector('[data-t="c_title"]').textContent = M.t("c_title");
    el.querySelector("#cl-scan").textContent = M.t("c_scan");
    el.querySelector("#cl-clean").textContent = M.t("c_clean");
    el.querySelector(".preview-toggle span").textContent = M.t("preview");
    el.querySelector("#cl-all").parentElement.querySelector("span").textContent = M.t("c_selectAll");
    el.querySelector("#cl-seltot-lbl").textContent = M.t("c_selectedTotal");

    if (DATA) { renderDiskInto(el.querySelector("#cl-disk")); renderGroups(el); }

    el.querySelector("#cl-scan").addEventListener("click", startScan);
    el.querySelector("#cl-clean").addEventListener("click", startClean);
    el.querySelector("#cl-dry").checked = true;
    el.querySelector("#cl-all").addEventListener("change", e => {
        document.querySelectorAll("#cl-groups .item-chk, #cl-groups .group-chk").forEach(c => { c.checked = e.target.checked; c.indeterminate = false; });
        updateTotal();
    });
}

function renderGroups(el) {
    const root = el.querySelector("#cl-groups");
    root.innerHTML = "";
    DATA.groups.forEach(g => {
        const gEl = document.createElement("section");
        gEl.className = "group"; gEl.dataset.group = g.group;
        gEl.innerHTML =
            `<div class="group-head">
               <input type="checkbox" class="group-chk" checked>
               <span class="gname">${M.escapeHtml(g.group_label[M.lang])}</span>
               <span class="gsize" data-gsize>—</span><span class="gcount" data-gcount></span>
               <span class="spacer"></span><span class="caret">▼</span>
             </div><div class="items"></div>`;
        const items = gEl.querySelector(".items");
        g.items.forEach(it => {
            const row = document.createElement("label");
            row.className = "item"; row.dataset.id = it.id;
            const v = sizes[it.id] || 0;
            const szCls = scanned ? (v > 0 ? "has" : "empty") : "empty";
            const szTxt = scanned ? fmtSize(v) : "—";
            row.innerHTML =
                `<input type="checkbox" class="item-chk" checked>
                 <span class="item-body"><span class="item-label">${M.escapeHtml(it.label[M.lang])}</span>
                 <span class="item-desc">${M.escapeHtml(it.desc[M.lang])}</span></span>
                 <span class="item-size ${szCls}" data-size>${szTxt}</span>`;
            items.appendChild(row);
        });
        root.appendChild(gEl);
    });
    bindGroups(el);
    if (scanned) { updateGroupSizes(); sortGroups(); }
    updateTotal();
}

function bindGroups(el) {
    el.querySelectorAll(".group-head").forEach(h => h.addEventListener("click", e => {
        if (e.target.classList.contains("group-chk")) return;
        h.parentElement.classList.toggle("collapsed");
    }));
    el.querySelectorAll(".group-chk").forEach(chk => {
        chk.addEventListener("click", e => e.stopPropagation());
        chk.addEventListener("change", () => {
            chk.closest(".group").querySelectorAll(".item-chk").forEach(c => c.checked = chk.checked);
            updateTotal();
        });
    });
    el.querySelectorAll(".item-chk").forEach(chk => chk.addEventListener("change", () => { syncGroup(); updateTotal(); }));
}

function syncGroup() {
    document.querySelectorAll("#cl-groups .group").forEach(g => {
        const items = [...g.querySelectorAll(".item-chk")];
        const gc = g.querySelector(".group-chk");
        gc.checked = items.every(c => c.checked);
        gc.indeterminate = !gc.checked && items.some(c => c.checked);
    });
}

function selectedIds() {
    return [...document.querySelectorAll("#cl-groups .item")]
        .filter(r => r.querySelector(".item-chk").checked).map(r => r.dataset.id);
}

function updateTotal() {
    let total = 0;
    selectedIds().forEach(id => total += sizes[id] || 0);
    const elT = M.$("cl-seltot"); if (elT) elT.textContent = scanned ? fmtSize(total) : "—";
    const btn = M.$("cl-clean"); if (btn) btn.disabled = !scanned || selectedIds().length === 0;
}

function updateGroupSizes() {
    document.querySelectorAll("#cl-groups .group").forEach(g => {
        let gs = 0, gc = 0;
        g.querySelectorAll(".item").forEach(r => { gs += sizes[r.dataset.id] || 0; gc += counts[r.dataset.id] || 0; });
        g.querySelector("[data-gsize]").textContent = fmtSize(gs);
        g.querySelector("[data-gcount]").textContent = gc ? `(${gc})` : "";
    });
}

function sortGroups() {
    document.querySelectorAll("#cl-groups .items").forEach(items => {
        [...items.children].sort((a, b) => (sizes[b.dataset.id] || 0) - (sizes[a.dataset.id] || 0))
            .forEach(r => items.appendChild(r));
    });
}

function prog(pct, txt) { M.$("cl-prog").style.display = ""; M.$("cl-progfill").style.width = pct + "%"; M.$("cl-progtxt").textContent = txt; }
function progHide() { const p = M.$("cl-prog"); if (p) p.style.display = "none"; }

function startScan() {
    scanned = false;
    const btn = M.$("cl-scan"); btn.disabled = true; btn.textContent = M.t("scanning");
    M.$("cl-clean").disabled = true; M.$("cl-banner").style.display = "none";
    document.querySelectorAll("#cl-groups .item").forEach(r => {
        r.classList.remove("cleaned");
        const s = r.querySelector("[data-size]"); s.textContent = "…"; s.className = "item-size";
    });
    const total = document.querySelectorAll("#cl-groups .item").length; let done = 0;
    prog(0, M.t("scanning"));
    M.sse("/api/scan", {
        onMsg: m => {
            if (m.type !== "item") return;
            sizes[m.id] = m.size; counts[m.id] = m.count;
            const row = document.querySelector(`#cl-groups .item[data-id="${m.id}"]`);
            if (row) { const s = row.querySelector("[data-size]"); s.textContent = fmtSize(m.size); s.className = "item-size " + (m.size > 0 ? "has" : "empty"); }
            done++; prog(done / total * 100, `${M.t("scanning")} ${done}/${total}`);
            updateGroupSizes(); updateTotal();
        },
        onDone: () => { scanned = true; progHide(); btn.disabled = false; btn.textContent = M.t("c_scan"); updateGroupSizes(); updateTotal(); sortGroups(); },
        onError: () => { btn.disabled = false; btn.textContent = M.t("c_scan"); progHide(); },
    });
}

function startClean() {
    const ids = selectedIds(); if (!ids.length) return;
    const dry = M.$("cl-dry").checked;
    let sel = 0; ids.forEach(id => sel += sizes[id] || 0);
    if (!dry && !confirm(M.t("c_confirm")(ids.length, fmtSize(sel)))) return;
    const clean = M.$("cl-clean"); clean.disabled = true; M.$("cl-scan").disabled = true;
    M.$("cl-banner").style.display = "none";
    const total = ids.length; let done = 0; prog(0, M.t("c_clean"));
    M.sse(`/api/clean?dry=${dry ? 1 : 0}&ids=${encodeURIComponent(ids.join(","))}`, {
        onMsg: m => {
            if (m.type !== "item") return;
            const row = document.querySelector(`#cl-groups .item[data-id="${m.id}"]`);
            if (row && !m.dry) { row.classList.add("cleaned"); row.querySelector("[data-size]").textContent = "✓ " + fmtSize(m.freed); sizes[m.id] = 0; }
            done++; prog(done / total * 100, `${M.t("c_clean")} ${done}/${total}`);
        },
        onDone: m => {
            progHide(); M.$("cl-scan").disabled = false; clean.textContent = M.t("c_clean");
            const b = M.$("cl-banner");
            if (m.dry) { b.className = "result-banner preview"; b.innerHTML = M.t("c_previewDone")(fmtSize(m.total_freed)); }
            else {
                b.className = "result-banner ok";
                let msg = M.t("c_cleanDone")(fmtSize(m.total_freed), m.total_removed);
                if (m.total_failed) msg += M.t("c_fail")(m.total_failed);
                b.innerHTML = msg;
                if (DATA && m.free) { DATA.free = m.free; DATA.used = DATA.total - m.free; renderDiskInto(M.$("cl-disk")); }
                updateGroupSizes();
            }
            b.style.display = ""; updateTotal();
        },
        onError: () => { progHide(); M.$("cl-scan").disabled = false; clean.textContent = M.t("c_clean"); updateTotal(); },
    });
}

M.registerView("clean", {
    render(el) {
        if (!loaded) {
            el.innerHTML = `<p class="placeholder">${M.t("loading")}</p>`;
            fetch("/api/info").then(r => r.json()).then(d => { DATA = d; loaded = true; render(el); });
        } else render(el);
    },
});
})();

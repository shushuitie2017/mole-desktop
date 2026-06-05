// Status 视图 - 实时系统监控 (psutil)
(function () {
"use strict";
const M = window.MOLE;

M.addStrings({
    zh: { s_health: "健康评分", s_cpu: "处理器", s_mem: "内存", s_swap: "交换", s_disk: "磁盘",
          s_net: "网络", s_proc: "进程占用", s_up: "上行", s_down: "下行", s_uptime: "运行",
          s_cores: "核心", s_total: "总占用", s_noissue: "运行良好" },
    en: { s_health: "Health", s_cpu: "CPU", s_mem: "Memory", s_swap: "Swap", s_disk: "Disk",
          s_net: "Network", s_proc: "Top processes", s_up: "Up", s_down: "Down", s_uptime: "Uptime",
          s_cores: "cores", s_total: "Total", s_noissue: "All good" },
    ja: { s_health: "健康度", s_cpu: "CPU", s_mem: "メモリ", s_swap: "スワップ", s_disk: "ディスク",
          s_net: "ネットワーク", s_proc: "プロセス", s_up: "上り", s_down: "下り", s_uptime: "稼働",
          s_cores: "コア", s_total: "合計", s_noissue: "良好" },
});

let timer = null;

function bar(pct, cls) {
    const p = Math.max(0, Math.min(100, pct));
    return `<div class="meter"><div class="meter-fill ${cls || ""}" style="width:${p}%"></div></div>`;
}
function barClass(pct) { return pct > 90 ? "crit" : pct > 70 ? "warn" : "ok"; }

function render(el) {
    el.innerHTML = `
      <div class="status-grid" id="st-grid"><p class="placeholder">${M.t("loading")}</p></div>`;
}

function paint(d) {
    const grid = M.$("st-grid"); if (!grid) return;
    const fs = M.fmtSize, fr = M.fmtRate;

    const healthColor = d.health >= 90 ? "ok" : d.health >= 70 ? "good" : d.health >= 50 ? "warn" : "crit";
    const issues = (d.issues && d.issues.length) ? d.issues.join(" · ") : M.t("s_noissue");

    let cores = "";
    d.cpu_cores.forEach((c, i) => {
        cores += `<div class="core"><span class="core-lbl">#${i}</span>${bar(c, barClass(c))}<span class="core-val">${c.toFixed(0)}%</span></div>`;
    });

    let disks = "";
    d.disks.forEach(dk => {
        disks += `<div class="kv"><span class="k">${M.escapeHtml(dk.device)}</span>${bar(dk.pct, barClass(dk.pct))}
                  <span class="v">${fs(dk.used)} / ${fs(dk.total)} · ${dk.pct.toFixed(0)}%</span></div>`;
    });

    let procs = "";
    d.procs.forEach(p => {
        procs += `<div class="proc"><span class="proc-name">${M.escapeHtml(p.name)}</span>
                  <span class="proc-cpu">${p.cpu.toFixed(1)}%</span>
                  <span class="proc-mem">${p.mem.toFixed(1)}%</span></div>`;
    });

    grid.innerHTML = `
      <div class="card card-wide health ${healthColor}">
        <div class="health-score">${d.health}</div>
        <div class="health-meta">
          <div class="health-msg">${M.escapeHtml(d.health_msg)}</div>
          <div class="health-issues">${M.escapeHtml(issues)}</div>
          <div class="health-host">${M.escapeHtml(d.host)} · ${M.t("s_uptime")} ${M.escapeHtml(d.uptime)}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-h">${M.t("s_cpu")} <span class="card-sub">${d.cpu_count} ${M.t("s_cores")}</span></div>
        <div class="kv big"><span class="k">${M.t("s_total")}</span>${bar(d.cpu_total, barClass(d.cpu_total))}<span class="v">${d.cpu_total.toFixed(0)}%</span></div>
        <div class="cores">${cores}</div>
      </div>

      <div class="card">
        <div class="card-h">${M.t("s_mem")}</div>
        <div class="kv big"><span class="k">RAM</span>${bar(d.mem.pct, barClass(d.mem.pct))}<span class="v">${fs(d.mem.used)} / ${fs(d.mem.total)} · ${d.mem.pct.toFixed(0)}%</span></div>
        ${d.swap.total > 0 ? `<div class="kv"><span class="k">${M.t("s_swap")}</span>${bar(d.swap.pct, barClass(d.swap.pct))}<span class="v">${fs(d.swap.used)} / ${fs(d.swap.total)}</span></div>` : ""}
      </div>

      <div class="card">
        <div class="card-h">${M.t("s_disk")}</div>
        ${disks || `<p class="placeholder">${M.t("empty")}</p>`}
      </div>

      <div class="card">
        <div class="card-h">${M.t("s_net")}</div>
        <div class="net-row"><span class="net-lbl">▼ ${M.t("s_down")}</span><span class="net-val down">${fr(d.net.down)}</span></div>
        <div class="net-row"><span class="net-lbl">▲ ${M.t("s_up")}</span><span class="net-val up">${fr(d.net.up)}</span></div>
      </div>

      <div class="card">
        <div class="card-h">${M.t("s_proc")} <span class="card-sub">CPU / ${M.t("s_mem")}</span></div>
        <div class="procs">${procs || `<p class="placeholder">${M.t("empty")}</p>`}</div>
      </div>`;
}

async function tick() {
    try {
        const d = await (await fetch("/api/status")).json();
        if (!d.error) paint(d);
    } catch (e) {}
}

M.registerView("status", {
    render,
    show() { tick(); timer = window.setInterval(tick, 2000); },
    hide() { if (timer) { window.clearInterval(timer); timer = null; } },
});
})();

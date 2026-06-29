const STATUS_LABEL = {
  created: "產腳本中…",
  script_ready: "腳本完成，待做 avatar",
  processing: "影片合成中…",
  done: "完成 ✓",
  failed: "失敗",
};

async function loadConfig() {
  const cfg = await fetch("/api/config").then((r) => r.json());
  const pillarSel = document.getElementById("pillar");
  pillarSel.innerHTML =
    `<option value="">🎲 隨機（AI 決定）</option>` +
    (cfg.pillars || []).map((p) => `<option value="${p}">${p}</option>`).join("");
  const topicSel = document.getElementById("topic");
  topicSel.innerHTML =
    `<option value="">🎲 自動生成（AI 出題）</option>` +
    (cfg.topics || []).map((t) => `<option value="${t}">${t}</option>`).join("");
  // 指南頁：填入人設與內容線
  const persona = document.getElementById("guide-persona");
  if (persona) persona.textContent = (cfg.persona && cfg.persona.style) || "";
  const pillars = document.getElementById("guide-pillars");
  if (pillars)
    pillars.innerHTML = (cfg.pillars || [])
      .map((p) => `<span class="chip">${esc(p)}</span>`)
      .join("");
}

// 分頁切換
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const view = btn.dataset.view;
    document.getElementById("view-make").hidden = view !== "make";
    document.getElementById("view-guide").hidden = view !== "guide";
  });
});

document.getElementById("job-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const btn = e.target.querySelector("button");
  btn.disabled = true;
  btn.textContent = "送出中…";
  try {
    await fetch("/api/jobs", { method: "POST", body: fd });
    e.target.reset();
    await loadConfig();
    refresh();
  } finally {
    btn.disabled = false;
    btn.textContent = "產生腳本 →";
  }
});

function esc(s) {
  return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

function scriptBlock(job) {
  const s = job.script || {};
  const heygen = s.heygen_script || "";
  const full = [
    s.title ? `標題：${s.title}` : "",
    s.question_text ? `開場字卡（藏鏡人提問）：${s.question_text}` : "",
    s.hook ? `Hook：${s.hook}` : "",
    (s.voiceover_lines || []).length
      ? `口播：\n${(s.voiceover_lines || []).map((l) => "・" + l).join("\n")}`
      : "",
    s.outro ? `收尾：${s.outro}` : "",
    s.scene_notes ? `畫面建議：${s.scene_notes}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  return `
    <div class="script-box">
      <div class="q">🙋 開場字卡問題：${esc(s.question_text)}</div>
      <div><b>${esc(s.title || "")}</b></div>
      <div style="margin-top:6px">${esc(s.hook)}</div>
      <div>${(s.voiceover_lines || []).map(esc).join("<br>")}</div>
      <div style="margin-top:6px;color:#9aa3af">${esc(s.outro)}</div>
      <div class="hint">🎥 畫面建議：${esc(s.scene_notes)}</div>
    </div>
    <div class="copybar">
      <button class="ghost" onclick='copyText(${JSON.stringify(heygen)}, this)'>📋 複製口播逐字稿（貼 Kling）</button>
      <button class="ghost" onclick='copyText(${JSON.stringify(full)}, this)'>📋 複製完整腳本</button>
      <code>來源：${esc(s._provider || "")}</code>
    </div>
    <div class="hint">💡 開場字卡與畫面建議「不用」貼到 Kling：字卡工具會自動疊上畫面，畫面建議是給你拍攝/運鏡參考。</div>`;
}

function regenBlock(job) {
  return `<button class="ghost" onclick="retryScript('${job.id}')">🔄 重新生成腳本</button>`;
}

function uploadBlock(job) {
  return `
    <div class="upload">
      <div class="hint">在 Kling 用上面的逐字稿/語音做好 avatar 影片後，把 mp4 丟回來：</div>
      <input type="file" accept="video/mp4,video/quicktime" onchange="uploadVideo('${job.id}', this)" />
    </div>`;
}

function doneBlock(job) {
  return `
    <video src="${job.output}" controls></video>
    <a class="dl" href="${job.output}" download>⬇ 下載成品</a>`;
}

function render(jobs) {
  const box = document.getElementById("jobs");
  if (!jobs.length) {
    box.innerHTML = '<p class="empty">還沒有任務。上面選個方向（或全部留自動）按「產生腳本」就開始。</p>';
    return;
  }
  box.innerHTML = jobs
    .map((job) => {
      let body = "";
      if (job.status === "failed") {
        body = `<div class="err">⚠ ${esc(job.error)}</div>
          <div class="actions"><button class="ghost" onclick="retryScript('${job.id}')">🔄 重試生成腳本</button></div>`;
        if (job.script) body = scriptBlock(job) + uploadBlock(job) + body;
      } else if (job.status === "script_ready") {
        body =
          scriptBlock(job) +
          `<div class="actions">${regenBlock(job)}</div>` +
          uploadBlock(job);
      } else if (job.status === "done") {
        body =
          scriptBlock(job) +
          doneBlock(job) +
          `<div class="actions">${regenBlock(job)}</div>` +
          `<details class="redo"><summary>↻ 換一支影片重做</summary>${uploadBlock(job)}</details>`;
      } else {
        body = '<div class="hint">處理中，請稍候…</div>';
      }
      return `
        <div class="job">
          <div class="job-head">
            <span class="job-title">${esc(job.topic)}</span>
            <span class="head-right">
              <span class="badge ${job.status}">${STATUS_LABEL[job.status] || job.status}</span>
              <button class="del" title="刪除這個腳本" onclick='deleteJob(${JSON.stringify(job.id)}, ${JSON.stringify(job.topic || "")})'>🗑</button>
            </span>
          </div>
          <div class="meta">${esc(job.pillar)}${job.notes ? " · " + esc(job.notes) : ""}</div>
          ${body}
        </div>`;
    })
    .join("");
}

async function refresh() {
  const jobs = await fetch("/api/jobs").then((r) => r.json());
  render(jobs);
}

async function uploadVideo(jobId, input) {
  if (!input.files.length) return;
  const fd = new FormData();
  fd.append("file", input.files[0]);
  input.disabled = true;
  await fetch(`/api/jobs/${jobId}/video`, { method: "POST", body: fd });
  refresh();
}

async function retryScript(jobId) {
  await fetch(`/api/jobs/${jobId}/retry-script`, { method: "POST" });
  refresh();
}

async function deleteJob(jobId, topic) {
  if (!confirm(`確定刪除「${topic || "這個腳本"}」？\n腳本、上傳的影片與成品都會一起刪掉，無法復原。`))
    return;
  await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
  refresh();
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text);
  if (btn) {
    const old = btn.textContent;
    btn.textContent = "已複製 ✓";
    setTimeout(() => {
      btn.textContent = old;
    }, 1500);
  }
}

loadConfig();
refresh();
setInterval(refresh, 3000);

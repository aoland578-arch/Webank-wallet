const BLOCK_LABELS = {
  system_rules: "系统行为规则",
  client_terminal: "客户终端提示",
  knowledge_rag: "本地知识库 RAG",
  image_history: "历史图档召回",
  audio_signals: "语音情绪/语种信号",
  enterprise_info: "当前登录企业",
  profile_digest: "风控画像摘要",
  wallet_facts: "经营流水事实",
  offtopic_steer: "回归主航道",
  wallet_pending: "钱包提案状态",
  transcript: "历史对话召回",
  user_input: "客户最新输入",
  assistant_output: "模型回复",
  thinking: "推理链",
  tool_call: "工具调用",
  hermes_soul: "Hermes SOUL.md",
  hermes_config: "Hermes config.yaml",
  hermes_memory: "Hermes MEMORY.md",
  hermes_user: "Hermes USER.md",
  profile_prompt: "画像更新提示词",
  loan_estimate_prompt: "贷款估算提示词",
  voicecall_system: "视频通话 System",
  voicecall_memory: "视频通话记忆",
  realtime_instructions: "实时语音人设",
  realtime_memory: "实时语音记忆",
  realtime_vision_context: "实时语音·画面上下文注入",
  vision_prompt: "视觉帧描述提示词",
};

const RECORD_TYPE_LABELS = {
  chat_main: "文字聊天",
  chat_hermes_system: "Hermes System",
  profile_update: "画像更新",
  loan_estimate: "贷款估算",
  asr: "语音转写 ASR",
  voicecall_turn: "视频通话回合",
  voicecall_realtime: "实时语音会话",
  vision_frame: "视觉帧描述",
  thinking: "推理链",
  tool_call: "工具调用",
};

const state = {
  authenticated: false,
  users: [],
  records: [],
  selectedUserId: "",
  selectedRecordId: "",
};

const loginScreen = document.getElementById("loginScreen");
const appShell = document.getElementById("appShell");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const loginPassword = document.getElementById("loginPassword");
const userSelect = document.getElementById("userSelect");
const userMeta = document.getElementById("userMeta");
const recordItems = document.getElementById("recordItems");
const recordCount = document.getElementById("recordCount");
const detailEmpty = document.getElementById("detailEmpty");
const detailContent = document.getElementById("detailContent");
const refreshBtn = document.getElementById("refreshBtn");
const logoutBtn = document.getElementById("logoutBtn");

function blockColor(type) {
  const key = `--block-${type}`;
  const value = getComputedStyle(document.documentElement).getPropertyValue(key).trim();
  return value || getComputedStyle(document.documentElement).getPropertyValue("--block-default").trim();
}

function blockLabel(type) {
  if (BLOCK_LABELS[type]) return BLOCK_LABELS[type];
  if (type.startsWith("hermes_skill_")) return `Hermes Skill: ${type.slice("hermes_skill_".length)}`;
  return type;
}

function recordTypeLabel(type) {
  return RECORD_TYPE_LABELS[type] || type;
}

function formatLlmInfo(llm) {
  if (!llm || typeof llm !== "object") return "未记录";
  const head = [llm.provider, llm.model].filter(Boolean).join(" · ");
  const tail = [llm.route, llm.endpoint, llm.extra].filter(Boolean).join(" · ");
  if (!head && !tail) return "未记录";
  return tail ? `${head || "模型"}（${tail}）` : head;
}

function formatLlmShort(llm) {
  if (!llm || typeof llm !== "object") return "未记录";
  const head = [llm.provider, llm.model].filter(Boolean).join(" · ");
  return head || "未记录";
}

function modelDirectionLabel(direction) {
  return direction === "input" ? "输入模型" : "输出模型";
}

function formatDirectionLlm(direction, llm) {
  const side = modelDirectionLabel(direction);
  const detail = formatLlmShort(llm);
  return detail === "未记录" ? `${side}：未记录` : `${side}：${detail}`;
}

function formatDirectionLlmFull(direction, llm) {
  const side = modelDirectionLabel(direction);
  const detail = formatLlmInfo(llm);
  return detail === "未记录" ? `${side}：未记录` : `${side}：${detail}`;
}

function renderAuxiliaryLlms(auxiliaryLlms) {
  if (!Array.isArray(auxiliaryLlms) || !auxiliaryLlms.length) return "";
  return auxiliaryLlms
    .map((item) => {
      const role = item.role || "辅助模型";
      const detail = formatLlmInfo(item);
      return `<span class="aux-llm-chip">${escapeHtml(`${role}：${detail}`)}</span>`;
    })
    .join("");
}

function formatTime(ts) {
  if (!ts) return "";
  const date = new Date(Number(ts) * 1000);
  if (Number.isNaN(date.getTime())) return String(ts);
  return date.toLocaleString("zh-CN", { hour12: false });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || `HTTP ${response.status}`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

function showLogin() {
  loginScreen.classList.remove("hidden");
  appShell.classList.add("hidden");
}

function showApp() {
  loginScreen.classList.add("hidden");
  appShell.classList.remove("hidden");
}

async function checkAuth() {
  try {
    const payload = await api("/api/monitor/auth/me");
    state.authenticated = Boolean(payload.authenticated);
    if (state.authenticated) {
      showApp();
      await loadUsers();
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

async function login(username, password) {
  await api("/api/monitor/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  state.authenticated = true;
  showApp();
  await loadUsers();
}

async function logout() {
  try {
    await api("/api/monitor/auth/logout", { method: "POST", body: "{}" });
  } catch {
    // ignore
  }
  state.authenticated = false;
  state.users = [];
  state.records = [];
  state.selectedUserId = "";
  state.selectedRecordId = "";
  showLogin();
}

async function loadUsers() {
  const payload = await api("/api/monitor/users");
  state.users = payload.users || [];
  userSelect.innerHTML = '<option value="">选择用户…</option>';
  for (const user of state.users) {
    const option = document.createElement("option");
    option.value = user.user_id;
    option.textContent = `${user.phone_masked} · ${user.enterprise_name || "未命名企业"}`;
    userSelect.appendChild(option);
  }
  if (state.selectedUserId) {
    userSelect.value = state.selectedUserId;
  }
}

async function loadRecords() {
  if (!state.selectedUserId) {
    state.records = [];
    renderRecordList();
    renderDetailEmpty();
    return;
  }
  const payload = await api(`/api/monitor/records?user_id=${encodeURIComponent(state.selectedUserId)}&limit=500`);
  state.records = payload.records || [];
  renderRecordList();
  if (state.selectedRecordId && state.records.some((item) => item.id === state.selectedRecordId)) {
    await loadRecordDetail(state.selectedRecordId);
  } else {
    state.selectedRecordId = "";
    renderDetailEmpty();
  }
}

function renderRecordList() {
  recordItems.innerHTML = "";
  recordCount.textContent = String(state.records.length);
  if (!state.records.length) {
    recordItems.innerHTML = '<p class="record-preview">暂无记录。用户开始对话后会实时写入。</p>';
    return;
  }

  let lastTurnId = "";
  for (const record of state.records) {
    if (record.turn_id !== lastTurnId) {
      lastTurnId = record.turn_id;
      const divider = document.createElement("div");
      divider.className = "turn-divider";
      divider.textContent = `Turn #${record.turn_index || "?"} · ${record.turn_preview || record.turn_channel || ""}`;
      recordItems.appendChild(divider);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = `record-item${record.id === state.selectedRecordId ? " active" : ""}`;
    button.dataset.recordId = record.id;
    const metadata = record.metadata || {};
    const direction = record.direction || metadata.llm_direction || "output";
    const llmLabel = formatDirectionLlm(direction, metadata.llm);
    button.innerHTML = `
      <div class="record-item-head">
        <span class="record-type">${recordTypeLabel(record.record_type)}</span>
        <span class="record-time">${formatTime(record.created_ts)}</span>
      </div>
      <span class="record-direction ${direction}">${direction === "input" ? "输入" : "输出"} · ${record.role}</span>
      <span class="record-model record-model-${direction}">${escapeHtml(llmLabel)}</span>
      <p class="record-preview">${escapeHtml(record.preview || "")}</p>
    `;
    button.addEventListener("click", () => selectRecord(record.id));
    recordItems.appendChild(button);
  }
}

function renderDetailEmpty() {
  detailEmpty.classList.remove("hidden");
  detailContent.classList.add("hidden");
  detailContent.innerHTML = "";
}

async function selectRecord(recordId) {
  state.selectedRecordId = recordId;
  renderRecordList();
  await loadRecordDetail(recordId);
}

async function loadRecordDetail(recordId) {
  const payload = await api(`/api/monitor/records/${encodeURIComponent(recordId)}`);
  const record = payload.record;
  detailEmpty.classList.add("hidden");
  detailContent.classList.remove("hidden");

  const metadata = record.metadata || {};
  const direction = record.direction || metadata.llm_direction || "output";
  const llmFull = formatDirectionLlmFull(direction, metadata.llm);
  const metaChips = [
    formatTime(record.created_ts),
    recordTypeLabel(record.record_type),
    `${direction === "input" ? "输入" : "输出"} / ${record.role}`,
    record.turn_preview ? `Turn: ${record.turn_preview}` : "",
  ].filter(Boolean);

  let bodyHtml = "";
  if (record.blocks && record.blocks.length) {
    bodyHtml = `<div class="prompt-blocks">${record.blocks.map((block) => renderBlock(block, direction, metadata.llm)).join("")}</div>`;
  } else {
    bodyHtml = renderOutputBody(record);
  }

  const auxHtml = renderAuxiliaryLlms(metadata.auxiliary_llms);

  detailContent.innerHTML = `
    <div class="detail-header">
      <h2>${recordTypeLabel(record.record_type)}</h2>
      <div class="detail-meta">
        ${metaChips.map((chip) => `<span class="meta-chip">${escapeHtml(chip)}</span>`).join("")}
        ${metadata.note ? `<span class="meta-chip">${escapeHtml(metadata.note)}</span>` : ""}
      </div>
      <p class="detail-llm detail-llm-${direction}">${escapeHtml(llmFull)}</p>
      ${auxHtml ? `<div class="detail-aux-llms">${auxHtml}</div>` : ""}
    </div>
    ${bodyHtml}
  `;

  detailContent.querySelectorAll(".toggle-block-btn").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      const block = btn.closest(".prompt-block");
      if (!block) return;
      const collapsed = block.classList.toggle("collapsed");
      btn.textContent = collapsed ? "展开" : "收起";
    });
  });
}

function renderBlock(block, direction, llm) {
  const type = block.block_type || "default";
  const color = blockColor(type);
  const long = (block.content || "").length > 4000;
  const side = modelDirectionLabel(direction);
  const modelHint = formatLlmShort(llm);
  return `
    <section class="prompt-block${long ? " collapsed" : ""}">
      <div class="prompt-block-head" style="background:${color}">
        <div class="prompt-block-title">
          <span>${escapeHtml(blockLabel(type))}</span>
          <span class="prompt-block-model prompt-block-model-${direction}">${escapeHtml(side)} → ${escapeHtml(modelHint)}</span>
        </div>
        ${long ? '<button type="button" class="toggle-block-btn">展开</button>' : ""}
      </div>
      <pre class="prompt-block-body">${escapeHtml(block.content || "")}</pre>
    </section>
  `;
}

function renderOutputBody(record) {
  return `<pre class="raw-content">${escapeHtml(displayContent(record))}</pre>`;
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function normalizeThinkingText(text) {
  if (!text) return "";
  const parts = text.split(/\n\n+/);
  const shortParts = parts.filter((part) => part.length <= 40 && !part.includes("\n"));
  // 旧版 gateway 把每个 reasoning.delta token 用 \n\n 拼接，还原为连续文本。
  if (parts.length >= 6 && shortParts.length >= parts.length * 0.6) {
    return parts.join("");
  }
  return text;
}

function displayContent(record) {
  const content = record.content || "";
  if (record.record_type === "thinking") {
    return normalizeThinkingText(content);
  }
  return content;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.classList.add("hidden");
  try {
    await login(
      document.getElementById("loginUsername").value.trim(),
      loginPassword.value,
    );
  } catch (error) {
    loginError.textContent = error.payload?.error || error.message || "登录失败";
    loginError.classList.remove("hidden");
  }
});

userSelect.addEventListener("change", async () => {
  state.selectedUserId = userSelect.value;
  state.selectedRecordId = "";
  const user = state.users.find((item) => item.user_id === state.selectedUserId);
  userMeta.textContent = user
    ? `${user.phone_masked} · ${user.enterprise_name} · ${user.record_count || 0} 条记录`
    : "";
  await loadRecords();
});

refreshBtn.addEventListener("click", async () => {
  await loadUsers();
  await loadRecords();
});

logoutBtn.addEventListener("click", logout);

checkAuth();

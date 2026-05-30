const state = {
  messages: [],
  attachments: [],
  busy: false,
  recorder: null,
  recordingChunks: [],
  voiceMeter: null,
  auth: null,
  loginMode: "password",
  accountProfile: null,
  wallet: null,
  walletPeriod: "day",
  walletChartMode: "bar",
  walletPending: [],
  walletPendingBusyIds: new Set(),
  profilePollTimer: null,
  profileLastUpdatedAt: "",
};

const SHOW_INTERNAL_PANELS = localStorage.getItem("wewallet.showInternalPanels") === "1";
const appShell = document.querySelector(".app-shell");
const messageList = document.getElementById("messageList");
const composerForm = document.getElementById("composerForm");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const imageButton = document.getElementById("imageButton");
const attachmentPopover = document.getElementById("attachmentPopover");
const pickImageButton = document.getElementById("pickImageButton");
const pickFileButton = document.getElementById("pickFileButton");
const pickVideoButton = document.getElementById("pickVideoButton");
const imageInput = document.getElementById("imageInput");
const fileInput = document.getElementById("fileInput");
const videoInput = document.getElementById("videoInput");
const micButton = document.getElementById("micButton");
const attachmentPreview = document.getElementById("attachmentPreview");
const messageTemplate = document.getElementById("messageTemplate");
const walletPendingBar = document.getElementById("walletPendingBar");
const walletPendingList = document.getElementById("walletPendingList");
const walletPendingCount = document.getElementById("walletPendingCount");
const openProfileButton = document.getElementById("openProfileButton");
const openWalletButton = document.getElementById("openWalletButton");
const openLoanButton = document.getElementById("openLoanButton");
const openVideoCallButton = document.getElementById("openVideoCallButton");
const mobileMenuButton = document.getElementById("mobileMenuButton");
const closeVideoCallButton = document.getElementById("closeVideoCallButton");
const videoCallBackdrop = document.getElementById("videoCallBackdrop");
const videoCallModal = document.getElementById("videoCallModal");
const videoCallSelf = document.getElementById("videoCallSelf");
const videoCallSelfPlaceholder = document.getElementById("videoCallSelfPlaceholder");
const videoCallStatus = document.getElementById("videoCallStatus");
const videoCallStartButton = document.getElementById("videoCallStartButton");
const videoCallMuteButton = document.getElementById("videoCallMuteButton");
const videoCallEndButton = document.getElementById("videoCallEndButton");
const closeProfileButton = document.getElementById("closeProfileButton");
const refreshProfileButton = document.getElementById("refreshProfileButton");
const profileBackdrop = document.getElementById("profileBackdrop");
const profileDrawer = document.getElementById("profileDrawer");
const profileMarkdown = document.getElementById("profileMarkdown");
const profileSummary = document.getElementById("profileSummary");
const profileDiffDetails = document.getElementById("profileDiffDetails");
const profileDiff = document.getElementById("profileDiff");
const walletBackdrop = document.getElementById("walletBackdrop");
const walletDrawer = document.getElementById("walletDrawer");
const closeWalletButton = document.getElementById("closeWalletButton");
const importWalletButton = document.getElementById("importWalletButton");
const addWalletEntryButton = document.getElementById("addWalletEntryButton");
const walletCsvInput = document.getElementById("walletCsvInput");
const walletEntryForm = document.getElementById("walletEntryForm");
const walletDate = document.getElementById("walletDate");
const walletType = document.getElementById("walletType");
const walletAmount = document.getElementById("walletAmount");
const walletCategory = document.getElementById("walletCategory");
const walletDescription = document.getElementById("walletDescription");
const walletPeriodTabs = Array.from(document.querySelectorAll(".wallet-period-tab"));
const walletChartModeButtons = Array.from(document.querySelectorAll(".wallet-chart-mode"));
const walletSummary = document.getElementById("walletSummary");
const walletChart = document.getElementById("walletChart");
const walletPlan = document.getElementById("walletPlan");
const walletTransactions = document.getElementById("walletTransactions");
const walletMessage = document.getElementById("walletMessage");
const loanBackdrop = document.getElementById("loanBackdrop");
const loanModal = document.getElementById("loanModal");
const closeLoanButton = document.getElementById("closeLoanButton");
const refreshLoanButton = document.getElementById("refreshLoanButton");
const loanUpdatedAt = document.getElementById("loanUpdatedAt");
const loanBody = document.getElementById("loanBody");
const loanMessage = document.getElementById("loanMessage");
const sidebarToggleButton = document.getElementById("sidebarToggleButton");
const authScreen = document.getElementById("authScreen");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const enterpriseForm = document.getElementById("enterpriseForm");
const loginPhone = document.getElementById("loginPhone");
const loginPassword = document.getElementById("loginPassword");
const loginCode = document.getElementById("loginCode");
const loginPasswordField = document.getElementById("loginPasswordField");
const loginSmsField = document.getElementById("loginSmsField");
const passwordLoginTab = document.getElementById("passwordLoginTab");
const smsLoginTab = document.getElementById("smsLoginTab");
const sendLoginCodeButton = document.getElementById("sendLoginCodeButton");
const openRegisterButton = document.getElementById("openRegisterButton");
const backToLoginButton = document.getElementById("backToLoginButton");
const registerPhone = document.getElementById("registerPhone");
const registerPassword = document.getElementById("registerPassword");
const registerCode = document.getElementById("registerCode");
const sendRegisterCodeButton = document.getElementById("sendRegisterCodeButton");
const enterpriseName = document.getElementById("enterpriseName");
const enterpriseCreditCode = document.getElementById("enterpriseCreditCode");
const authMessage = document.getElementById("authMessage");
const accountButton = document.getElementById("accountButton");
const accountAvatar = document.getElementById("accountAvatar");
const accountLabel = document.getElementById("accountLabel");
const sessionStatus = document.getElementById("sessionStatus");
const accountBackdrop = document.getElementById("accountBackdrop");
const accountModal = document.getElementById("accountModal");
const closeAccountButton = document.getElementById("closeAccountButton");
const avatarUploadButton = document.getElementById("avatarUploadButton");
const avatarInput = document.getElementById("avatarInput");
const profileAvatarPreview = document.getElementById("profileAvatarPreview");
const accountTabUser = document.getElementById("accountTabUser");
const accountTabEnterprise = document.getElementById("accountTabEnterprise");
const accountUserPanel = document.getElementById("accountUserPanel");
const accountEnterprisePanel = document.getElementById("accountEnterprisePanel");
const accountProfileForm = document.getElementById("accountProfileForm");
const accountProfileMessage = document.getElementById("accountProfileMessage");
const logoutButton = document.getElementById("logoutButton");
const profilePhone = document.getElementById("profilePhone");
const profileNickname = document.getElementById("profileNickname");
const profileRole = document.getElementById("profileRole");
const accountEnterpriseFields = {
  name: document.getElementById("profileEnterpriseName"),
  credit_code: document.getElementById("profileCreditCode"),
  legal_representative: document.getElementById("profileLegalRepresentative"),
  city: document.getElementById("profileCity"),
  address: document.getElementById("profileAddress"),
  industry: document.getElementById("profileIndustry"),
  main_business: document.getElementById("profileMainBusiness"),
  established_at: document.getElementById("profileEstablishedAt"),
  business_years: document.getElementById("profileBusinessYears"),
  enterprise_type: document.getElementById("profileEnterpriseType"),
  annual_revenue: document.getElementById("profileAnnualRevenue"),
  employee_count: document.getElementById("profileEmployeeCount"),
  monthly_cashflow: document.getElementById("profileMonthlyCashflow"),
  has_corporate_account: document.getElementById("profileHasCorporateAccount"),
  payment_channels: document.getElementById("profilePaymentChannels"),
  has_tax_record: document.getElementById("profileHasTaxRecord"),
  has_social_security: document.getElementById("profileHasSocialSecurity"),
  funding_purpose: document.getElementById("profileFundingPurpose"),
  expected_amount: document.getElementById("profileExpectedAmount"),
  expected_term: document.getElementById("profileExpectedTerm"),
};
const DEFAULT_MESSAGE_PLACEHOLDER = "请输入您的经营情况、资金需求或材料问题";
const MOBILE_MESSAGE_PLACEHOLDER = "输入消息";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
}

function renderInlineMarkdown(value) {
  let text = escapeHtml(value);
  const codeSpans = [];
  text = text.replace(/`([^`]+)`/g, (_match, code) => {
    const token = `\u0000CODE${codeSpans.length}\u0000`;
    codeSpans.push(`<code>${code}</code>`);
    return token;
  });
  text = text
    .replace(/\*\*([^*\n][\s\S]*?[^*\n])\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_\n][\s\S]*?[^_\n])__/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>")
    .replace(/_([^_\n]+)_/g, "<em>$1</em>");
  return text.replace(/\u0000CODE(\d+)\u0000/g, (_match, index) => codeSpans[Number(index)] || "");
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isTableDivider(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let listType = "";
  let tableRows = [];
  let inCode = false;
  let codeLang = "";
  let codeLines = [];

  function flushParagraph() {
    if (!paragraph.length) return;
    html.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`);
    paragraph = [];
  }

  function flushList() {
    if (!listType) return;
    html.push(`</${listType}>`);
    listType = "";
  }

  function flushTable() {
    if (!tableRows.length) return;
    const [head, ...body] = tableRows;
    html.push('<div class="markdown-table-wrap"><table><thead><tr>');
    for (const cell of head) html.push(`<th>${renderInlineMarkdown(cell)}</th>`);
    html.push("</tr></thead>");
    if (body.length) {
      html.push("<tbody>");
      for (const row of body) {
        html.push("<tr>");
        for (const cell of row) html.push(`<td>${renderInlineMarkdown(cell)}</td>`);
        html.push("</tr>");
      }
      html.push("</tbody>");
    }
    html.push("</table></div>");
    tableRows = [];
  }

  function flushCode() {
    if (!inCode) return;
    const langClass = codeLang ? ` class="language-${escapeAttribute(codeLang)}"` : "";
    html.push(`<pre><code${langClass}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    inCode = false;
    codeLang = "";
    codeLines = [];
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      if (inCode) {
        flushCode();
      } else {
        flushParagraph();
        flushList();
        flushTable();
        inCode = true;
        codeLang = trimmed.slice(3).trim().split(/\s+/)[0] || "";
      }
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      continue;
    }

    if (!trimmed) {
      flushParagraph();
      flushList();
      flushTable();
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      flushTable();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    if (line.includes("|") && index + 1 < lines.length && isTableDivider(lines[index + 1])) {
      flushParagraph();
      flushList();
      flushTable();
      tableRows.push(splitTableRow(line));
      index += 1;
      continue;
    }

    if (tableRows.length && line.includes("|")) {
      tableRows.push(splitTableRow(line));
      continue;
    }

    const unordered = trimmed.match(/^[-*+]\s+(.+)$/);
    if (unordered) {
      flushParagraph();
      flushTable();
      if (listType !== "ul") {
        flushList();
        listType = "ul";
        html.push("<ul>");
      }
      html.push(`<li>${renderInlineMarkdown(unordered[1])}</li>`);
      continue;
    }

    const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (ordered) {
      flushParagraph();
      flushTable();
      if (listType !== "ol") {
        flushList();
        listType = "ol";
        html.push("<ol>");
      }
      html.push(`<li>${renderInlineMarkdown(ordered[1])}</li>`);
      continue;
    }

    const quote = trimmed.match(/^>\s?(.+)$/);
    if (quote) {
      flushParagraph();
      flushList();
      flushTable();
      html.push(`<blockquote>${renderInlineMarkdown(quote[1])}</blockquote>`);
      continue;
    }

    flushTable();
    flushList();
    paragraph.push(trimmed);
  }

  flushCode();
  flushParagraph();
  flushList();
  flushTable();
  return html.join("");
}

function renderMarkdownInto(element, text) {
  const cleanText = sanitizeVisibleText(text);
  element.classList.add("markdown-body");
  element.innerHTML = cleanText ? renderMarkdown(cleanText) : "";
}

function stripUploadRequestFence(value) {
  return String(value || "").replace(/```upload_request\s*\n[\s\S]*?\n```\s*/g, "").trim();
}

function renderUploadRequestCard(message) {
  const request = message?.upload_request;
  if (!request || message.uploadRequestDismissed) return null;
  const card = document.createElement("div");
  card.className = "upload-request-card";
  const header = document.createElement("div");
  header.className = "upload-request-header";
  const icon = document.createElement("span");
  icon.className = "upload-request-icon";
  icon.textContent = "📎";
  const title = document.createElement("span");
  title.className = "upload-request-title";
  title.textContent = "请补充资料";
  header.append(icon, title);
  card.appendChild(header);
  const reason = String(request.reason || "").trim();
  if (reason) {
    const body = document.createElement("div");
    body.className = "upload-request-reason";
    body.textContent = reason;
    card.appendChild(body);
  }
  const items = Array.isArray(request.items) ? request.items : [];
  if (items.length) {
    const list = document.createElement("ul");
    list.className = "upload-request-items";
    for (const item of items) {
      const li = document.createElement("li");
      const name = document.createElement("strong");
      name.textContent = String(item?.name || "").trim() || "材料";
      li.appendChild(name);
      const hint = String(item?.hint || "").trim();
      if (hint) {
        const small = document.createElement("span");
        small.className = "upload-request-hint";
        small.textContent = `· ${hint}`;
        li.appendChild(small);
      }
      list.appendChild(li);
    }
    card.appendChild(list);
  }
  const controls = document.createElement("div");
  controls.className = "upload-request-controls";
  const pickImage = document.createElement("button");
  pickImage.type = "button";
  pickImage.className = "upload-request-button primary";
  pickImage.textContent = "上传图片";
  pickImage.onclick = () => triggerUploadFromCard(message, "image");
  const pickFile = document.createElement("button");
  pickFile.type = "button";
  pickFile.className = "upload-request-button";
  pickFile.textContent = "上传文件";
  pickFile.onclick = () => triggerUploadFromCard(message, "file");
  const later = document.createElement("button");
  later.type = "button";
  later.className = "upload-request-button ghost";
  later.textContent = "稍后再传";
  later.onclick = () => {
    message.uploadRequestDismissed = true;
    renderMessages();
  };
  controls.append(pickImage, pickFile, later);
  card.appendChild(controls);
  return card;
}

function renderSuggestions(message) {
  const suggestions = Array.isArray(message?.suggestions) ? message.suggestions : [];
  const items = suggestions
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .slice(0, 4);
  if (!items.length) return null;
  const wrap = document.createElement("div");
  wrap.className = "suggestion-chips";
  wrap.setAttribute("aria-label", "推荐问题");
  for (const item of items) {
    const button = document.createElement("button");
    button.className = "suggestion-chip";
    button.type = "button";
    button.textContent = item;
    button.addEventListener("click", () => {
      messageInput.value = item;
      messageInput.style.height = "auto";
      messageInput.style.height = `${Math.min(messageInput.scrollHeight, 180)}px`;
      syncComposerTextState();
      messageInput.focus();
    });
    wrap.appendChild(button);
  }
  return wrap;
}

function triggerUploadFromCard(message, kind) {
  if (state.busy) return;
  message.uploadRequestDismissed = true;
  renderMessages();
  if (kind === "image") {
    imageInput.click();
  } else {
    fileInput.click();
  }
  messageInput.focus();
}

function sanitizeVisibleText(value) {
  let text = String(value || "").trim();
  while (text.includes("<think>") && text.includes("</think>")) {
    const start = text.indexOf("<think>");
    const end = text.indexOf("</think>", start);
    text = `${text.slice(0, start)}${text.slice(end + "</think>".length)}`.trim();
  }
  const prefixes = ["Chain of thought", "Thought process"];
  const lines = text.split("\n");
  const kept = [];
  let skipping = false;
  for (const line of lines) {
    const stripped = line.trim();
    if (prefixes.some((prefix) => stripped.startsWith(prefix))) {
      skipping = true;
      continue;
    }
    if (skipping && (!stripped || stripped.startsWith("最终") || stripped.startsWith("回复") || stripped.startsWith("答案"))) {
      skipping = false;
      const visible = stripped.replace(/^最终回复[:：]?/, "").replace(/^回复[:：]?/, "").replace(/^答案[:：]?/, "").trim();
      if (visible) kept.push(visible);
      continue;
    }
    if (!skipping) kept.push(line);
  }
  return kept.join("\n").trim();
}

function visibleAttachmentText(value, attachments) {
  const text = sanitizeVisibleText(value);
  const items = Array.isArray(attachments) ? attachments.filter(Boolean) : [];
  if (!items.length) return text;
  if (/^\[(图片|视频|文件)附件\]$/.test(text)) return "";
  if (/^\[语音附件[^\]]*\]$/.test(text)) return "";
  const voiceOnly = text.match(/^\[语音\]\s*([\s\S]+)$/);
  if (voiceOnly) return voiceOnly[1].trim();
  return text;
}

const REASONING_TAGS = ["think", "reasoning", "thinking", "thought", "REASONING_SCRATCHPAD"];

function splitReasoning(value) {
  let text = String(value || "");
  const reasoning = [];
  for (const tag of REASONING_TAGS) {
    const paired = new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>\\s*`, "gi");
    text = text.replace(paired, (_match, inner) => {
      const trimmed = String(inner || "").trim();
      if (trimmed) reasoning.push(trimmed);
      return "";
    });

    const unclosed = new RegExp(`<${tag}>([\\s\\S]*)$`, "i");
    text = text.replace(unclosed, (_match, inner) => {
      const trimmed = String(inner || "").trim();
      if (trimmed) reasoning.push(trimmed);
      return "";
    });
  }
  return {
    text: text.trim(),
    reasoning: reasoning.join("\n\n").trim(),
  };
}

function appendDetails(container, className, title, bodyText, open = false) {
  const text = sanitizeVisibleText(bodyText);
  if (!text) return;
  const details = document.createElement("details");
  details.className = className;
  details.open = open;
  const summary = document.createElement("summary");
  summary.textContent = title;
  const body = document.createElement("div");
  body.innerHTML = escapeHtml(text).replaceAll("\n", "<br>");
  details.append(summary, body);
  container.appendChild(details);
}

// 处理过程的线性图标（与界面其余 SVG 风格一致）
const PROC_ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  chart: '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-6"/><path d="M3 20h18"/>',
  book: '<path d="M5 4h13v16H6a2 2 0 0 1 0-4h12"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="m21 16-5-5L5 20"/>',
  bulb: '<path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10c.7.7 1 1.6 1 2h6c0-.4.3-1.3 1-2a6 6 0 0 0-4-10Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12 5 5L20 6"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6"/><path d="M12 16.5v.01"/>',
};

function procSvg(key) {
  const inner = PROC_ICONS[key] || PROC_ICONS.clock;
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}

// 步骤类型图标用 emoji（彩色更直观），底色由 tone chip 提供
const PROC_EMOJI = {
  bulb: "💡",
  book: "📚",
  chart: "📊",
  edit: "✏️",
  search: "🔍",
  image: "🖼️",
  mic: "🎙️",
  doc: "📄",
  reply: "💬",
  clock: "⚙️",
};

function procEmoji(key) {
  return PROC_EMOJI[key] || PROC_EMOJI.clock;
}

// 把工具调用翻译成面向小微企业主的业务语言 + 图标
function describeProcStep(item) {
  const tid = String(item.tool_id || "").toLowerCase();
  const name = String(item.name || "");
  const lower = name.toLowerCase();
  const has = (...kw) => kw.some((k) => tid.includes(k) || lower.includes(k));
  if (has("asr") || name.includes("语音")) return { icon: "mic", tone: "orange", label: "识别你的语音" };
  if (has("knowledge") || name.includes("知识库")) return { icon: "book", tone: "indigo", label: "查阅贷款知识库" };
  if (has("image", "图档", "图片")) return { icon: "image", tone: "rose", label: "翻阅历史图档" };
  if (has("profile") || name.includes("画像")) return { icon: "edit", tone: "teal", label: "更新你的经营画像" };
  if (has("wallet") || name.includes("钱包") || name.includes("流水")) return { icon: "chart", tone: "green", label: "分析钱包流水" };
  if (has("write", "edit", "update") || name.includes("更新") || name.includes("写")) return { icon: "edit", tone: "teal", label: "更新你的资料" };
  if (has("search", "grep", "rg") || name.includes("检索") || name.includes("搜索")) return { icon: "search", tone: "blue", label: "检索相关信息" };
  if (has("read", "fetch", "get") || name.includes("查阅") || name.includes("查看") || name.includes("读取")) return { icon: "doc", tone: "blue", label: "查阅资料" };
  // 兜底：中文工具名直接用，否则给通用文案
  const friendly = /[一-龥]/.test(name) ? name : "处理中";
  return { icon: "clock", tone: "gray", label: friendly };
}

// 每条事件 = 一个时间线节点，保留事件原始文本（细粒度，不做工具合并）
function buildProcSteps(items) {
  const steps = [];
  for (const item of items) {
    const data = typeof item === "object" ? item : { text: item };
    const type = String(data.type || "");
    const isThink = /think|reason/i.test(type);
    let label = sanitizeVisibleText(data.text || data.preview || data.name || "");
    if (!label && !isThink) continue;

    // 连续的思考增量合并成同一个“思考”节点，只保留最新的实时状态
    if (isThink) {
      const prev = steps[steps.length - 1];
      if (prev && prev.kind === "think") {
        if (label) prev.live = label;
        continue;
      }
      steps.push({ kind: "think", icon: "bulb", tone: "amber", live: label, label: "", status: "step", dur: "" });
      continue;
    }

    // 工具/其它事件：把结尾的耗时（如 "... 0.8s"）抽出来单独右侧展示
    let dur = "";
    const durMatch = label.match(/\s(\d+(?:\.\d+)?)\s*s$/);
    if (durMatch) {
      const seconds = parseFloat(durMatch[1]);
      dur = seconds < 0.1 ? "<0.1s" : `${durMatch[1]}s`;
      label = label.slice(0, durMatch.index).trim();
    }
    // 把后端的英文前缀换成中文友好表达
    label = label
      .replace(/^started\s+/i, "开始")
      .replace(/^complete\s+/i, "完成")
      .replace(/^preparing\s+/i, "准备")
      .replace(/^generating\s+/i, "准备")
      .replace(/^error\s+/i, "失败 · ")
      .replace(/\.{3}$/, "…");
    let status = "step";
    if (data.status === "error" || type === "error") status = "error";
    else if (type === "tool.complete") status = "done";
    const desc = describeProcStep(data);
    steps.push({ icon: desc.icon, tone: desc.tone, label, status, dur });
  }
  return steps;
}

function appendProgress(container, progress, streaming = false) {
  const items = Array.isArray(progress) ? progress.filter(Boolean) : [];
  if (!items.length) return;
  const steps = buildProcSteps(items);
  if (!steps.length) return;
  // 思考节点默认都显示“思考完成”
  for (const step of steps) {
    if (step.kind === "think") {
      step.label = "思考完成";
      step.status = "done";
    }
  }
  if (streaming) {
    const tail = steps[steps.length - 1];
    if (tail && tail.kind === "think") {
      // 还在思考：显示实时状态，并在其后补“正在回复…”，让 analyzing 落到倒数第二
      tail.label = tail.live || "思考中…";
      tail.status = "step";
      steps.push({ kind: "reply", icon: "reply", tone: "teal", label: "正在回复…", status: "running", dur: "" });
    } else if (tail && tail.status === "step") {
      // 工具仍在进行，给脉冲反馈
      tail.status = "running";
    }
  }
  const lastLabel = steps[steps.length - 1].label;

  const details = document.createElement("details");
  details.className = "proc";
  details.open = streaming;

  const summary = document.createElement("summary");
  summary.className = "proc-summary";
  summary.innerHTML =
    `<span class="proc-chevron"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg></span>` +
    `<span class="proc-title">小微的思考</span>` +
    `<span class="proc-badge">${steps.length} 步</span>` +
    `<span class="proc-last">${escapeHtml(lastLabel)}</span>`;

  const list = document.createElement("ol");
  list.className = "proc-timeline";
  for (const step of steps) {
    const li = document.createElement("li");
    li.className = `proc-step is-${step.status}`;
    const nodeIcon = step.status === "done" ? procSvg("check") : step.status === "error" ? procSvg("alert") : "";
    const dur = step.dur ? `<span class="proc-dur">${escapeHtml(step.dur)}</span>` : "";
    li.innerHTML =
      `<span class="proc-node">${nodeIcon}</span>` +
      `<span class="proc-ico tone-${step.tone || "gray"}">${procEmoji(step.icon)}</span>` +
      `<span class="proc-label">${escapeHtml(step.label)}</span>${dur}`;
    list.appendChild(li);
  }

  details.append(summary, list);
  container.appendChild(details);
}

function isThinkingStatus(text) {
  const value = String(text || "").trim();
  return Boolean(value) && value.length <= 80 && !value.includes("\n");
}

function appendDiffPanels(container, diffs, open = false) {
  const items = Array.isArray(diffs) ? diffs.filter(Boolean) : [];
  if (!items.length) return;
  const details = document.createElement("details");
  details.className = "risk-reasoning diff-details";
  details.open = open;
  const summary = document.createElement("summary");
  summary.textContent = "变更记录";
  details.appendChild(summary);
  for (const diff of items) {
    const pre = document.createElement("pre");
    pre.className = "diff-panel";
    pre.textContent = String(diff || "");
    details.appendChild(pre);
  }
  container.appendChild(details);
}

function fileSizeLabel(size) {
  const value = Number(size || 0);
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  if (value >= 1024) return `${Math.ceil(value / 1024)} KB`;
  return `${value} B`;
}

function moneyLabel(value) {
  return `¥${Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`;
}

function parseWalletDate(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

function walletPeriodLabel(period) {
  return period === "week" ? "周" : period === "month" ? "月" : "日";
}

function walletAnchorDate(transactions) {
  const dates = transactions.map((item) => parseWalletDate(item.date)).filter(Boolean);
  if (!dates.length) return new Date();
  return new Date(Math.max(...dates.map((date) => date.getTime())));
}

function sameWalletDay(left, right) {
  return left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate();
}

function walletWeekStart(date) {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const day = copy.getDay() || 7;
  copy.setDate(copy.getDate() - day + 1);
  return copy;
}

function walletDateKey(date, period) {
  if (period === "month") {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  }
  if (period === "week") {
    const start = walletWeekStart(date);
    return `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(start.getDate()).padStart(2, "0")}`;
  }
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function walletBucketLabel(date, period) {
  if (period === "month") return `${date.getMonth() + 1}月`;
  if (period === "week") {
    const start = walletWeekStart(date);
    return `${start.getMonth() + 1}/${start.getDate()}周`;
  }
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function shiftWalletDate(date, period, offset) {
  const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  if (period === "month") {
    copy.setMonth(copy.getMonth() + offset, 1);
    return copy;
  }
  copy.setDate(copy.getDate() + offset * (period === "week" ? 7 : 1));
  return period === "week" ? walletWeekStart(copy) : copy;
}

function walletTrendBuckets(transactions, period) {
  const anchor = period === "week" ? walletWeekStart(walletAnchorDate(transactions)) : walletAnchorDate(transactions);
  const count = period === "day" ? 7 : 6;
  const buckets = Array.from({ length: count }, (_item, index) => {
    const date = shiftWalletDate(anchor, period, index - count + 1);
    return {
      key: walletDateKey(date, period),
      label: walletBucketLabel(date, period),
      income: 0,
      expense: 0,
      net: 0,
    };
  });
  const byKey = new Map(buckets.map((bucket) => [bucket.key, bucket]));
  for (const item of transactions) {
    const date = parseWalletDate(item.date);
    if (!date) continue;
    const bucket = byKey.get(walletDateKey(date, period));
    if (!bucket) continue;
    const amount = Number(item.amount || 0);
    if (item.type === "income") bucket.income += amount;
    if (item.type === "expense") bucket.expense += amount;
  }
  for (const bucket of buckets) bucket.net = bucket.income - bucket.expense;
  return buckets;
}

function walletPeriodStats(transactions, period) {
  const anchor = walletAnchorDate(transactions);
  const weekStart = walletWeekStart(anchor);
  const items = transactions.filter((item) => {
    const date = parseWalletDate(item.date);
    if (!date) return false;
    if (period === "month") {
      return date.getFullYear() === anchor.getFullYear() && date.getMonth() === anchor.getMonth();
    }
    if (period === "week") {
      const diffDays = Math.floor((date - weekStart) / 86400000);
      return diffDays >= 0 && diffDays < 7;
    }
    return sameWalletDay(date, anchor);
  });
  const income = items.reduce((sum, item) => sum + (item.type === "income" ? Number(item.amount || 0) : 0), 0);
  const expense = items.reduce((sum, item) => sum + (item.type === "expense" ? Number(item.amount || 0) : 0), 0);
  return {
    income,
    expense,
    net: income - expense,
    count: items.length,
    anchor,
    items,
  };
}

function walletCategoriesByType(items, type) {
  const totals = new Map();
  for (const item of items) {
    if (item.type !== type) continue;
    const key = String(item.category || "未分类").trim() || "未分类";
    totals.set(key, (totals.get(key) || 0) + Number(item.amount || 0));
  }
  return [...totals.entries()]
    .map(([category, amount]) => ({ category, amount }))
    .sort((left, right) => right.amount - left.amount);
}

function renderWalletBarChart(buckets) {
  const maxValue = Math.max(1, ...buckets.flatMap((item) => [item.income || 0, item.expense || 0]));
  return buckets.map((item) => `
    <div class="wallet-month">
      <div class="wallet-bars">
        <span class="income" style="height:${Math.max(6, (item.income / maxValue) * 100)}%"></span>
        <span class="expense" style="height:${Math.max(6, (item.expense / maxValue) * 100)}%"></span>
      </div>
      <div>${escapeHtml(item.label)}</div>
      <small>${moneyLabel(item.net)}</small>
    </div>
  `).join("");
}

function walletLinePoints(values, maxValue, height) {
  const width = 100;
  const step = values.length > 1 ? width / (values.length - 1) : width;
  return values.map((value, index) => {
    const x = index * step;
    const y = height - (Number(value || 0) / maxValue) * (height - 8) - 4;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function renderWalletLineChart(buckets) {
  const maxValue = Math.max(1, ...buckets.flatMap((item) => [item.income || 0, item.expense || 0]));
  const incomePoints = walletLinePoints(buckets.map((item) => item.income), maxValue, 120);
  const expensePoints = walletLinePoints(buckets.map((item) => item.expense), maxValue, 120);
  return `
    <div class="wallet-line-chart">
      <svg viewBox="0 0 100 120" preserveAspectRatio="none" aria-hidden="true">
        <polyline class="income" points="${incomePoints}"></polyline>
        <polyline class="expense" points="${expensePoints}"></polyline>
      </svg>
      <div class="wallet-line-labels">${buckets.map((item) => `<span>${escapeHtml(item.label)}</span>`).join("")}</div>
    </div>
  `;
}

function renderWalletPieGroup(title, categories, tone) {
  const total = categories.reduce((sum, item) => sum + item.amount, 0);
  if (!total) {
    return `
      <div class="wallet-pie-panel">
        <h4>${title}</h4>
        <div class="wallet-empty compact">当前周期暂无${title}。</div>
      </div>
    `;
  }
  const colors = tone === "income"
    ? ["#00a6b4", "#4aa3a2", "#6b8ed6", "#8fbc8f", "#9b7cc1", "#5fb3d9"]
    : ["#d56f55", "#f2a65a", "#c98273", "#b79a72", "#9b7cc1", "#6b8ed6"];
  let cursor = 0;
  const stops = categories.map((item, index) => {
    const start = cursor;
    cursor += (item.amount / total) * 100;
    return `${colors[index % colors.length]} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
  }).join(", ");
  return `
    <div class="wallet-pie-panel">
      <h4>${title}</h4>
      <div class="wallet-pie" style="background: conic-gradient(${stops})"></div>
      <div class="wallet-pie-list">
        ${categories.map((item, index) => `
          <div class="wallet-pie-row">
            <span style="background:${colors[index % colors.length]}"></span>
            <strong>${escapeHtml(item.category)}</strong>
            <b>${moneyLabel(item.amount)}</b>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function renderWalletPieChart(items) {
  const incomeCategories = walletCategoriesByType(items, "income");
  const expenseCategories = walletCategoriesByType(items, "expense");
  return `
    <div class="wallet-pie-layout">
      ${renderWalletPieGroup("收入分类", incomeCategories, "income")}
      ${renderWalletPieGroup("支出分类", expenseCategories, "expense")}
    </div>
  `;
}

function attachmentKind(attachment) {
  const type = String(attachment.type || attachment.mime || "");
  if (type.startsWith("image/")) return "image";
  if (type.startsWith("audio/")) return "audio";
  if (type.startsWith("video/")) return "video";
  return "file";
}

function addAttachment(file) {
  const kind = attachmentKind(file);
  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  state.attachments.push({
    id,
    file,
    kind,
    name: file.name || (kind === "audio" ? "voice.webm" : kind),
    size: file.size || 0,
    type: file.type || "",
    url: URL.createObjectURL(file),
  });
  renderAttachmentPreview();
}

function attachmentIcon(kind) {
  if (kind === "image") return "图";
  if (kind === "video") return "视";
  if (kind === "audio") return "音";
  return "文";
}

function attachmentLabel(kind) {
  if (kind === "image") return "图片";
  if (kind === "video") return "视频";
  if (kind === "audio") return "语音";
  return "文件";
}

function clearAttachments() {
  for (const attachment of state.attachments) {
    if (attachment.url && attachment.url.startsWith("blob:")) URL.revokeObjectURL(attachment.url);
  }
  state.attachments = [];
  renderAttachmentPreview();
}

function removeAttachment(id) {
  const attachment = state.attachments.find((item) => item.id === id);
  if (attachment?.url?.startsWith("blob:")) URL.revokeObjectURL(attachment.url);
  state.attachments = state.attachments.filter((item) => item.id !== id);
  renderAttachmentPreview();
}

function renderAttachmentPreview() {
  attachmentPreview.innerHTML = "";
  attachmentPreview.hidden = state.attachments.length === 0;
  for (const attachment of state.attachments) {
    const chip = document.createElement("div");
    chip.className = `attachment-chip ${attachment.kind === "image" ? "image-chip" : ""} ${attachment.kind === "video" ? "video-chip" : ""}`;
    if (attachment.kind === "image") {
      const img = document.createElement("img");
      img.src = attachment.url;
      img.alt = attachment.name;
      chip.appendChild(img);
    } else if (attachment.kind === "video") {
      const video = document.createElement("video");
      video.src = attachment.url;
      video.muted = true;
      video.playsInline = true;
      chip.appendChild(video);
      const badge = document.createElement("span");
      badge.className = "attachment-kind-badge";
      badge.textContent = attachmentIcon(attachment.kind);
      chip.appendChild(badge);
    } else {
      const icon = document.createElement("div");
      icon.className = `attachment-file-icon ${attachment.kind}`;
      icon.textContent = attachmentIcon(attachment.kind);
      const body = document.createElement("div");
      body.className = "attachment-body";
      const title = document.createElement("div");
      title.className = "attachment-title";
      title.textContent = attachment.name || "附件";
      const meta = document.createElement("div");
      meta.className = "attachment-meta";
      meta.textContent = fileSizeLabel(attachment.size);
      body.append(title, meta);
      chip.append(icon, body);
      if (attachment.kind === "audio") {
        const audio = document.createElement("audio");
        audio.src = attachment.url;
        audio.controls = true;
        chip.appendChild(audio);
      }
    }
    const remove = document.createElement("button");
    remove.className = "remove-attachment";
    remove.type = "button";
    remove.setAttribute("aria-label", "删除附件");
    remove.textContent = "×";
    remove.onclick = () => removeAttachment(attachment.id);
    chip.appendChild(remove);
    attachmentPreview.appendChild(chip);
  }
}

function renderMessageAttachments(container, attachments) {
  const items = Array.isArray(attachments) ? attachments.filter(Boolean) : [];
  if (!items.length) return;
  const grid = document.createElement("div");
  grid.className = `bubble-media-grid media-count-${Math.min(items.length, 4)}`;
  for (const attachment of items) {
    const kind = attachment.kind || attachmentKind(attachment);
    const url = attachment.url || attachment.preview_url || "";
    if (!url) continue;
    const card = document.createElement("div");
    card.className = "bubble-media-card";
    if (kind === "image") {
      const img = document.createElement("img");
      img.src = url;
      img.alt = attachment.name || "图片附件";
      card.appendChild(img);
    } else if (kind === "audio") {
      card.classList.add("audio-card");
      const audio = document.createElement("audio");
      audio.src = url;
      audio.preload = "metadata";
      card.appendChild(audio);
      const voice = document.createElement("button");
      voice.className = "voice-message";
      voice.type = "button";
      voice.setAttribute("aria-label", "播放语音消息");
      voice.innerHTML = `
        <span class="voice-message-play" aria-hidden="true"></span>
        <span class="voice-message-wave" aria-hidden="true"><i></i><i></i><i></i></span>
        <span class="voice-message-label">语音</span>
      `;
      voice.onclick = () => {
        if (audio.paused) {
          document.querySelectorAll(".bubble-media-card audio").forEach((item) => {
            if (item !== audio) item.pause();
          });
          audio.play().catch(() => {});
        } else {
          audio.pause();
        }
      };
      audio.onplay = () => {
        voice.classList.add("is-playing");
        voice.setAttribute("aria-label", "暂停语音消息");
      };
      audio.onpause = () => {
        voice.classList.remove("is-playing");
        voice.setAttribute("aria-label", "播放语音消息");
      };
      audio.onended = () => {
        voice.classList.remove("is-playing");
        voice.setAttribute("aria-label", "播放语音消息");
      };
      card.appendChild(voice);
    } else if (kind === "video") {
      const video = document.createElement("video");
      video.src = url;
      video.controls = true;
      card.appendChild(video);
      const caption = document.createElement("div");
      caption.className = "attachment-caption";
      caption.textContent = attachment.name || "视频附件";
      card.appendChild(caption);
    } else {
      const file = document.createElement("a");
      file.className = "bubble-file-link";
      file.href = url;
      file.target = "_blank";
      file.rel = "noreferrer";
      file.textContent = `${attachmentIcon(kind)} ${attachment.name || "文件附件"} · ${fileSizeLabel(attachment.size)}`;
      card.appendChild(file);
    }
    grid.appendChild(card);
  }
  if (grid.children.length) container.appendChild(grid);
}

function renderEmpty() {
  messageList.innerHTML = `
    <div class="empty-state">
      <div class="empty-mascot" aria-hidden="true">
        <video class="mascot-video" autoplay muted loop playsinline preload="metadata" poster="/static/assets/mascot-smile.png">
          <source src="/static/assets/character-loop.webm" type="video/webm" />
          <img src="/static/assets/mascot-smile.png" alt="" />
        </video>
      </div>
      <h1>聊聊您的生意和资金需求</h1>
      <div class="prompt-chips" aria-label="快捷指令">
        <button class="prompt-chip" type="button">我想了解贷款额度</button>
        <button class="prompt-chip" type="button">最近需要资金周转</button>
        <button class="prompt-chip" type="button">想看看适合的贷款方案</button>
        <button class="prompt-chip" type="button">开厂买设备需要一笔钱</button>
      </div>
    </div>
  `;
  bindPromptChips();
}

function renderMessages() {
  if (!state.messages.length) {
    renderEmpty();
    return;
  }
  messageList.innerHTML = "";
  for (const message of state.messages) {
    const node = messageTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.role = message.role;
    const attachments = Array.isArray(message.attachments) ? message.attachments : [];
    if (attachments.length) node.classList.add("has-media");
    node.querySelector(".message-role").textContent = message.role === "user" ? "我" : "小微";
    const split = splitReasoning(message.content);
    const rawVisible = split.text || message.content;
    const visibleContent = message.role === "assistant" ? stripUploadRequestFence(rawVisible) : rawVisible;
    const bubble = node.querySelector(".bubble");
    if (attachments.length) {
      const text = document.createElement("div");
      text.className = "bubble-text";
      const cleanText = visibleAttachmentText(visibleContent, attachments);
      if (cleanText) {
        if (message.role === "assistant") {
          renderMarkdownInto(text, cleanText);
        } else {
          text.innerHTML = escapeHtml(cleanText).replaceAll("\n", "<br>");
        }
      } else {
        text.hidden = true;
      }
      bubble.appendChild(text);
      renderMessageAttachments(bubble, attachments);
    } else if (message.role === "assistant") {
      renderMarkdownInto(bubble, visibleContent);
    } else {
      bubble.innerHTML = escapeHtml(sanitizeVisibleText(visibleContent)).replaceAll("\n", "<br>");
    }
    if (message.role === "assistant") {
      node.querySelector(".avatar").style.backgroundImage = 'url("/static/assets/xiaowei-avatar-pro.png")';
      node.querySelector(".avatar").classList.add("has-image");
      const uploadCard = renderUploadRequestCard(message);
      if (uploadCard) bubble.appendChild(uploadCard);
      const bubbleWrap = node.querySelector(".bubble-wrap");
      appendProgress(bubbleWrap, message.progress, Boolean(message.streaming));
      if (!message.streaming) {
        const suggestions = renderSuggestions(message);
        if (suggestions) bubbleWrap.appendChild(suggestions);
      }
      if (SHOW_INTERNAL_PANELS) {
        const thinking = message.thinking || message.reasoning_summary || split.reasoning;
        appendDiffPanels(bubbleWrap, message.inline_diffs, Boolean(message.streaming));
        appendDetails(bubbleWrap, "risk-reasoning reasoning-details", "内部过程", thinking, Boolean(message.streaming));
      }
    } else {
      node.querySelector(".avatar").textContent = "";
    }
    messageList.appendChild(node);
  }
  messageList.scrollTop = messageList.scrollHeight;
}

function setBusy(value) {
  state.busy = value;
  sendButton.disabled = value;
  imageButton.disabled = value;
  micButton.disabled = value;
  messageInput.disabled = value;
}

async function postJson(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

async function getJson(path) {
  const response = await fetch(path);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

function setSidebarCollapsed(collapsed) {
  appShell.classList.toggle("sidebar-collapsed", Boolean(collapsed));
  sidebarToggleButton.setAttribute("aria-label", collapsed ? "展开侧栏" : "收起侧栏");
  sidebarToggleButton.title = collapsed ? "展开侧栏" : "收起侧栏";
  sidebarToggleButton.textContent = collapsed ? "›" : "‹";
  localStorage.setItem("wewallet.sidebarCollapsed", collapsed ? "1" : "0");
}

function isMobileLayout() {
  return window.matchMedia("(max-width: 980px)").matches;
}

function setMobileSidebarOpen(open) {
  appShell.classList.toggle("sidebar-open", Boolean(open));
  mobileMenuButton?.setAttribute("aria-expanded", open ? "true" : "false");
}

function syncResponsiveCopy() {
  messageInput.placeholder = isMobileLayout() ? MOBILE_MESSAGE_PLACEHOLDER : DEFAULT_MESSAGE_PLACEHOLDER;
}

function syncComposerTextState() {
  const hasText = Boolean(messageInput.value.trim());
  messageInput.closest(".composer-inner")?.classList.toggle("has-text", hasText);
}

function showComingSoon(feature) {
  attachmentPopover.hidden = true;
  alert(`${feature}开发中，敬请期待`);
}

function initials(value) {
  const text = String(value || "").trim();
  return text ? text.slice(0, 1) : "企";
}

function setAvatarElement(element, url, fallback) {
  element.textContent = initials(fallback);
  if (url) {
    element.style.backgroundImage = `url("${url}")`;
    element.classList.add("has-image");
  } else {
    element.style.backgroundImage = "";
    element.classList.remove("has-image");
  }
}

function showAuthMessage(text, isError = false) {
  authMessage.textContent = text || "";
  authMessage.classList.toggle("is-error", Boolean(isError));
}

function showAccountMessage(text, isError = false) {
  accountProfileMessage.textContent = text || "";
  accountProfileMessage.classList.toggle("is-error", Boolean(isError));
}

function setLoginMode(mode) {
  state.loginMode = mode === "sms" ? "sms" : "password";
  const smsMode = state.loginMode === "sms";
  loginPasswordField.hidden = smsMode;
  loginSmsField.hidden = !smsMode;
  passwordLoginTab.classList.toggle("is-active", !smsMode);
  smsLoginTab.classList.toggle("is-active", smsMode);
  showAuthMessage("");
}

function showRegister(show) {
  loginForm.hidden = Boolean(show);
  registerForm.hidden = !show;
  enterpriseForm.hidden = true;
  showAuthMessage("");
}

function applyAuthState(auth) {
  state.auth = auth || { authenticated: false };
  const authenticated = Boolean(state.auth.authenticated) && !state.auth.needs_enterprise;
  authScreen.hidden = authenticated;
  if (!state.auth.authenticated) {
    loginForm.hidden = false;
    registerForm.hidden = true;
    enterpriseForm.hidden = true;
  } else {
    loginForm.hidden = true;
    registerForm.hidden = true;
    enterpriseForm.hidden = !state.auth.needs_enterprise;
  }
  const label = state.accountProfile?.nickname || state.auth.enterprise?.name || state.auth.user?.phone || "未登录";
  accountLabel.textContent = label;
  sessionStatus.textContent = state.auth.enterprise ? "企业专属档案" : "等待绑定企业";
  setAvatarElement(accountAvatar, state.accountProfile?.avatar_url || "", label);
  composerForm.hidden = !authenticated;
  openProfileButton.disabled = !authenticated;
  openWalletButton.disabled = !authenticated;
  openLoanButton.disabled = !authenticated;
}

function renderWallet(payload) {
  state.wallet = payload || state.wallet || { transactions: [], summary: {} };
  walletPeriodTabs.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.walletPeriod === state.walletPeriod);
  });
  walletChartModeButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.walletChart === state.walletChartMode);
  });
  const transactionsForPeriod = state.wallet.transactions || [];
  const periodStats = walletPeriodStats(transactionsForPeriod, state.walletPeriod);
  const periodName = walletPeriodLabel(state.walletPeriod);
  const anchorText = periodStats.anchor.toLocaleDateString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  });
  const summary = state.wallet.summary || {};
  const plan = summary.plan || {};
  walletSummary.innerHTML = `
    <div class="wallet-card"><span>${periodName}收入 · ${anchorText}</span><strong>${moneyLabel(periodStats.income)}</strong></div>
    <div class="wallet-card"><span>${periodName}支出 · ${anchorText}</span><strong>${moneyLabel(periodStats.expense)}</strong></div>
    <div class="wallet-card"><span>${periodName}净现金流</span><strong class="${periodStats.net >= 0 ? "income" : "expense"}">${moneyLabel(periodStats.net)}</strong></div>
    <div class="wallet-card"><span>${periodName}流水笔数</span><strong>${periodStats.count} 笔</strong></div>
  `;

  const buckets = walletTrendBuckets(transactionsForPeriod, state.walletPeriod);
  if (state.walletChartMode === "pie") {
    walletChart.className = "wallet-chart wallet-chart-pie";
    walletChart.innerHTML = renderWalletPieChart(periodStats.items);
  } else if (state.walletChartMode === "line") {
    walletChart.className = "wallet-chart wallet-chart-line";
    walletChart.innerHTML = renderWalletLineChart(buckets);
  } else {
    walletChart.className = "wallet-chart";
    walletChart.innerHTML = renderWalletBarChart(buckets);
  }

  walletPlan.innerHTML = `
    <div class="wallet-plan-row"><span>月均收入</span><strong>${moneyLabel(plan.avg_monthly_income)}</strong></div>
    <div class="wallet-plan-row"><span>月均支出</span><strong>${moneyLabel(plan.avg_monthly_expense)}</strong></div>
    <div class="wallet-plan-row"><span>3 个月备用金</span><strong>${moneyLabel(plan.suggested_reserve)}</strong></div>
    <div class="wallet-plan-row"><span>增长预算</span><strong>${moneyLabel(plan.suggested_reinvestment)}</strong></div>
  `;

  const transactions = [...(state.wallet.transactions || [])].slice(-8).reverse();
  walletTransactions.innerHTML = transactions.length ? transactions.map((item) => `
    <div class="wallet-row">
      <div>
        <strong>${escapeHtml(item.description || "流水")}</strong>
        <span>${escapeHtml(item.date || "")} · ${escapeHtml(item.category || "未分类")}</span>
      </div>
      <b class="${item.type === "income" ? "income" : "expense"}">${item.type === "income" ? "+" : "-"}${moneyLabel(item.amount)}</b>
    </div>
  `).join("") : '<div class="wallet-empty">暂无流水。</div>';
  walletMessage.textContent = plan.suggested_reinvestment
    ? `规划建议：可把月均净现金流中的 ${moneyLabel(plan.suggested_reinvestment)} 作为备货、投流或设备更新预算。`
    : "规划建议会在录入更多流水后生成。";
}

async function loadWallet() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return;
  renderWallet(await getJson("/api/wallet"));
}

async function openWallet() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return;
  walletBackdrop.hidden = false;
  walletDrawer.hidden = false;
  walletDrawer.setAttribute("aria-hidden", "false");
  walletEntryForm.hidden = true;
  walletDate.value = new Date().toISOString().slice(0, 10);
  try {
    await loadWallet();
  } catch (error) {
    walletMessage.textContent = `读取失败：${error.message}`;
  }
}

function closeWallet() {
  walletBackdrop.hidden = true;
  walletDrawer.hidden = true;
  walletDrawer.setAttribute("aria-hidden", "true");
}

function formatLoanAmount(value) {
  const num = Number(value) || 0;
  return Number.isInteger(num) ? String(num) : num.toFixed(1);
}

function formatLoanRate(value) {
  const num = Number(value) || 0;
  return Number.isInteger(num) ? String(num) : num.toFixed(2).replace(/0$/, "");
}

function renderLoanLoading() {
  loanBody.innerHTML = `
    <div class="loan-loading">
      <span class="loan-spinner" aria-hidden="true"></span>
      <span>正在根据您的风控画像和经营流水预估额度...</span>
    </div>`;
}

function formatLoanTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function setLoanUpdatedAt(estimate) {
  loanUpdatedAt.textContent = estimate && estimate.generated_at
    ? `评估于 ${formatLoanTimestamp(estimate.generated_at)}`
    : "";
}

function renderLoanEstimate(estimate) {
  setLoanUpdatedAt(estimate);
  if (!estimate) {
    loanBody.innerHTML = `
      <div class="loan-empty">
        <div class="loan-empty-icon" aria-hidden="true">¥</div>
        <p>还没有评估记录，点右上角「更新评估额度」即可根据当前风控画像和经营流水生成。</p>
      </div>`;
    return;
  }
  if (estimate.insufficient) {
    loanBody.innerHTML = `
      <div class="loan-empty">
        <div class="loan-empty-icon" aria-hidden="true">¥</div>
        <p>${escapeHtml(estimate.insufficient_hint || "暂时还不够给出额度，先和小微多聊聊经营情况吧。")}</p>
      </div>`;
    return;
  }

  const grade = String(estimate.grade || "C");
  const reasons = Array.isArray(estimate.reasons) ? estimate.reasons : [];
  const materials = Array.isArray(estimate.missing_materials) ? estimate.missing_materials : [];

  const reasonsHtml = reasons.length
    ? `<ul class="loan-reasons">${reasons.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<p class="loan-section-empty">暂无更多说明。</p>`;

  const materialsHtml = materials.length
    ? `<div class="loan-section">
         <h3>补齐这些可提额 / 降息</h3>
         <ul class="loan-materials">
           ${materials.map((item) => `
             <li>
               <span class="loan-material-name">${escapeHtml(item.name || "")}</span>
               ${item.impact ? `<span class="loan-material-impact">${escapeHtml(item.impact)}</span>` : ""}
             </li>`).join("")}
         </ul>
       </div>`
    : "";

  loanBody.innerHTML = `
    <div class="loan-card">
      <div class="loan-card-top">
        <div class="loan-amount-label">预估可贷额度</div>
        <div class="loan-amount-value">
          <span class="loan-amount-symbol">¥</span>
          ${escapeHtml(formatLoanAmount(estimate.amount_min))} ~ ${escapeHtml(formatLoanAmount(estimate.amount_max))}
          <span class="loan-amount-unit">万</span>
        </div>
        <div class="loan-grade loan-grade-${escapeAttribute(grade)}">授信评级 ${escapeHtml(grade)} · ${escapeHtml(estimate.grade_label || "")}</div>
        <div class="loan-meta">
          <div class="loan-meta-item">
            <span>年化利率</span>
            <strong>${escapeHtml(formatLoanRate(estimate.rate_min))}% ~ ${escapeHtml(formatLoanRate(estimate.rate_max))}%</strong>
          </div>
          <div class="loan-meta-item">
            <span>最长期限</span>
            <strong>${escapeHtml(String(estimate.term_max_months || 0))} 个月</strong>
          </div>
        </div>
      </div>
      <div class="loan-section">
        <h3>评估依据</h3>
        ${reasonsHtml}
      </div>
      ${materialsHtml}
      <p class="loan-disclaimer">${escapeHtml(estimate.disclaimer || "预估结果，最终以实际审批为准。")}</p>
    </div>`;
}

// Open → show the last saved record (GET, no LLM call). Empty until the
// customer hits 更新评估额度 at least once.
async function loadSavedLoanEstimate() {
  loanMessage.textContent = "";
  renderLoanLoading();
  try {
    const payload = await getJson("/api/loan/estimate");
    renderLoanEstimate(payload.estimate);
  } catch (error) {
    loanUpdatedAt.textContent = "";
    loanBody.innerHTML = `<div class="loan-empty">读取失败：${escapeHtml(error.message)}</div>`;
  }
}

// 更新评估额度 → recompute via the gateway (POST), overwrite the saved record.
async function recomputeLoanEstimate() {
  loanMessage.textContent = "";
  renderLoanLoading();
  refreshLoanButton.disabled = true;
  try {
    const response = await fetch("/api/loan/estimate", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "评估失败");
    renderLoanEstimate(payload.estimate);
  } catch (error) {
    loanBody.innerHTML = `<div class="loan-empty">评估失败：${escapeHtml(error.message)}</div>`;
  } finally {
    refreshLoanButton.disabled = false;
  }
}

function openLoan() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return;
  loanBackdrop.hidden = false;
  loanModal.hidden = false;
  loanModal.setAttribute("aria-hidden", "false");
  loadSavedLoanEstimate();
}

function closeLoan() {
  loanBackdrop.hidden = true;
  loanModal.hidden = true;
  loanModal.setAttribute("aria-hidden", "true");
}

const videoCallState = { stream: null, muted: false };

function setVideoCallStatus(text) {
  if (videoCallStatus) videoCallStatus.textContent = text;
}

function showVideoCallSelfPlaceholder(visible) {
  if (videoCallSelfPlaceholder) videoCallSelfPlaceholder.hidden = !visible;
  if (videoCallSelf) videoCallSelf.hidden = visible;
}

function openVideoCall() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return;
  videoCallBackdrop.hidden = false;
  videoCallModal.hidden = false;
  videoCallModal.setAttribute("aria-hidden", "false");
  showVideoCallSelfPlaceholder(!videoCallState.stream);
  if (!videoCallState.stream) {
    setVideoCallStatus("演示版：尚未接入信令，可先开启本地摄像头预览。");
  }
}

function stopVideoCallStream() {
  if (videoCallState.stream) {
    videoCallState.stream.getTracks().forEach((track) => track.stop());
    videoCallState.stream = null;
  }
  if (videoCallSelf) videoCallSelf.srcObject = null;
  videoCallState.muted = false;
  if (videoCallMuteButton) {
    videoCallMuteButton.disabled = true;
    videoCallMuteButton.textContent = "静音";
  }
  if (videoCallEndButton) videoCallEndButton.disabled = true;
  if (videoCallStartButton) videoCallStartButton.disabled = false;
  showVideoCallSelfPlaceholder(true);
}

function closeVideoCall() {
  videoCallBackdrop.hidden = true;
  videoCallModal.hidden = true;
  videoCallModal.setAttribute("aria-hidden", "true");
  stopVideoCallStream();
}

async function startVideoCallPreview() {
  if (videoCallState.stream) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    setVideoCallStatus("当前浏览器不支持 getUserMedia，无法预览摄像头。");
    return;
  }
  videoCallStartButton.disabled = true;
  setVideoCallStatus("正在请求摄像头与麦克风权限...");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    videoCallState.stream = stream;
    if (videoCallSelf) videoCallSelf.srcObject = stream;
    showVideoCallSelfPlaceholder(false);
    if (videoCallMuteButton) videoCallMuteButton.disabled = false;
    if (videoCallEndButton) videoCallEndButton.disabled = false;
    setVideoCallStatus("本地预览已开启。远端连接尚未接入，挂断仅关闭本地预览。");
  } catch (error) {
    videoCallStartButton.disabled = false;
    setVideoCallStatus(`无法开启摄像头：${error.message || error.name || "未知错误"}`);
  }
}

function toggleVideoCallMute() {
  if (!videoCallState.stream) return;
  videoCallState.muted = !videoCallState.muted;
  videoCallState.stream.getAudioTracks().forEach((track) => {
    track.enabled = !videoCallState.muted;
  });
  if (videoCallMuteButton) videoCallMuteButton.textContent = videoCallState.muted ? "取消静音" : "静音";
}

function setAccountTab(tab) {
  const enterprise = tab === "enterprise";
  accountTabUser.classList.toggle("is-active", !enterprise);
  accountTabEnterprise.classList.toggle("is-active", enterprise);
  accountUserPanel.hidden = enterprise;
  accountEnterprisePanel.hidden = !enterprise;
}

function fillAccountForm(profile) {
  const enterprise = profile?.enterprise || {};
  profilePhone.value = profile?.phone || "";
  profileNickname.value = profile?.nickname || "";
  profileRole.value = profile?.role || "";
  for (const [field, input] of Object.entries(accountEnterpriseFields)) {
    input.value = enterprise[field] || "";
  }
  const label = profile?.nickname || enterprise.name || state.auth?.user?.phone || "企";
  setAvatarElement(profileAvatarPreview, profile?.avatar_url || "", label);
  setAvatarElement(accountAvatar, profile?.avatar_url || "", label);
  accountLabel.textContent = label;
}

function collectAccountProfilePayload() {
  const enterprise = {};
  for (const [field, input] of Object.entries(accountEnterpriseFields)) {
    enterprise[field] = input.value.trim();
  }
  return {
    nickname: profileNickname.value.trim(),
    role: profileRole.value.trim(),
    enterprise,
  };
}

async function loadAccountProfile() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return null;
  const payload = await getJson("/api/account/profile");
  state.accountProfile = payload.profile || null;
  if (state.accountProfile) fillAccountForm(state.accountProfile);
  applyAuthState(state.auth);
  return state.accountProfile;
}

async function openAccountModal() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return;
  accountBackdrop.hidden = false;
  accountModal.hidden = false;
  accountModal.setAttribute("aria-hidden", "false");
  showAccountMessage("");
  setAccountTab("user");
  try {
    await loadAccountProfile();
  } catch (error) {
    showAccountMessage(`读取失败：${error.message}`, true);
  }
}

function closeAccountModal() {
  accountBackdrop.hidden = true;
  accountModal.hidden = true;
  accountModal.setAttribute("aria-hidden", "true");
}

async function loadMessages() {
  const payload = await getJson("/api/messages");
  state.messages = payload.messages || [];
  renderMessages();
  void ensureLatestSuggestions();
}

async function ensureLatestSuggestions() {
  if (state.busy || !state.messages.length) return;
  const latestAssistant = [...state.messages].reverse().find((message) => (
    message.role === "assistant" &&
    String(message.content || "").trim() &&
    !Array.isArray(message.suggestions)
  ));
  if (!latestAssistant) return;
  try {
    const payload = await postJson("/api/messages/suggestions");
    if (Array.isArray(payload.messages)) {
      state.messages = payload.messages;
      renderMessages();
    }
  } catch (error) {
    // Recommendation chips are helpful, but chat history should still render normally.
  }
}

async function bootstrapApp() {
  try {
    const auth = await getJson("/api/auth/me");
    applyAuthState(auth);
    if (auth.authenticated && !auth.needs_enterprise) {
      await loadAccountProfile();
      await loadMessages();
      await loadProfile();
      await loadWalletPending();
      if (window.location.hash === "#wallet") {
        await openWallet();
      }
    } else {
      renderMessages();
    }
  } catch (error) {
    applyAuthState({ authenticated: false });
    showAuthMessage(error.message, true);
    renderMessages();
  }
}

function lastAssistantMessage() {
  return state.messages[state.messages.length - 1];
}

function appendUniqueProgress(message, text) {
  if (!message) return;
  const value = typeof text === "object" ? text : sanitizeVisibleText(text);
  if (!value) return;
  message.progress = Array.isArray(message.progress) ? message.progress : [];
  const previous = message.progress[message.progress.length - 1];
  const previousText = typeof previous === "object" ? previous.text : previous;
  const nextText = typeof value === "object" ? value.text : value;
  if (previousText !== nextText) {
    message.progress.push(value);
  }
}

function applyChatStreamEvent(event) {
  const message = lastAssistantMessage();
  if (!message || message.role !== "assistant") return;
  const payload = event.payload || {};
  if (event.type === "assistant.start") {
    message.content = payload.content || message.content || "正在分析客户需求...";
  } else if (event.type === "progress.delta") {
    appendUniqueProgress(message, payload.text || "");
  } else if (event.type === "tool.generating") {
    appendUniqueProgress(message, { type: event.type, name: payload.name || "", text: `preparing ${payload.name || "tool"}...` });
  } else if (event.type === "tool.progress") {
    appendUniqueProgress(message, { type: event.type, name: payload.name || "", text: payload.preview || payload.text || payload.name || "" });
  } else if (event.type === "tool.start") {
    appendUniqueProgress(message, { type: event.type, name: payload.name || "", text: `started ${payload.name || "tool"}` });
  } else if (event.type === "tool.complete") {
    const duration = typeof payload.duration_s === "number" ? ` ${payload.duration_s.toFixed(1)}s` : "";
    const status = payload.error ? "error" : "complete";
    const text = payload.error
      ? `${status} ${payload.name || "tool"}${duration}: ${payload.error}`
      : `${status} ${payload.name || "tool"}${duration}`;
    appendUniqueProgress(message, { type: event.type, name: payload.name || "", status, text });
    if (payload.inline_diff) {
      message.inline_diffs = Array.isArray(message.inline_diffs) ? message.inline_diffs : [];
      message.inline_diffs.push(payload.inline_diff);
    }
  } else if (event.type === "status.update") {
    appendUniqueProgress(message, { type: event.type, status: payload.kind || "", text: payload.text || "" });
  } else if (event.type === "thinking.delta" || event.type === "reasoning.delta") {
    const text = String(payload.text || "");
    if (text) {
      message.thinking = `${message.thinking || ""}${text}`;
      if (isThinkingStatus(text)) {
        appendUniqueProgress(message, { type: event.type, name: "Hermes", text });
      }
    }
  } else if (event.type === "reasoning.available") {
    return;
  } else if (event.type === "message.delta") {
    const text = String(payload.text || "");
    if (text) {
      if (message.content === "正在分析客户需求...") message.content = "";
      message.content = `${message.content || ""}${text}`;
    }
  } else if (event.type === "message.complete") {
    state.messages = payload.messages || state.messages;
    if (Array.isArray(payload.wallet_pending)) {
      state.walletPending = payload.wallet_pending;
      renderWalletPending();
    }
    if (payload.auto_profile?.scheduled && profileSummary) {
      profileSummary.textContent = `已自动开始更新风控画像（第 ${payload.auto_profile.user_turn_count} 轮），稍后会自动刷新...`;
      startProfilePolling();
    } else if (payload.auto_profile?.in_progress && profileSummary) {
      startProfilePolling();
    }
  } else if (event.type === "error") {
    throw new Error(payload.error || payload.message || "调用失败");
  }
}

async function postStreamingChat(message, attachments = []) {
  const body = new FormData();
  body.append("message", message);
  for (const attachment of attachments) {
    if (attachment.file) body.append("attachments", attachment.file, attachment.name || attachment.file.name);
  }
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    body,
  });
  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || "请求失败");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      applyChatStreamEvent(event);
      if (event.type === "message.complete") completed = true;
      renderMessages();
    }
  }

  const tail = buffer.trim();
  if (tail) {
    const event = JSON.parse(tail);
    applyChatStreamEvent(event);
    if (event.type === "message.complete") completed = true;
    renderMessages();
  }

  const assistant = lastAssistantMessage();
  if (assistant && assistant.role === "assistant") {
    assistant.streaming = false;
  }
  if (!completed) {
    appendUniqueProgress(assistant, "本轮连接已结束，未收到完成事件。");
  }
}

async function sendMessage(content) {
  const text = content.trim();
  const attachments = [...state.attachments];
  if ((!text && !attachments.length) || state.busy) return;
  const optimisticText = text;
  const optimisticAttachments = attachments.map((item) => ({
    kind: item.kind,
    name: item.name,
    size: item.size,
    type: item.type,
    url: item.url,
  }));
  state.messages.push({ role: "user", content: optimisticText, attachments: optimisticAttachments });
  state.messages.push({ role: "assistant", content: "正在分析客户需求...", thinking: "", progress: [], inline_diffs: [], streaming: true });
  renderMessages();
  messageInput.value = "";
  messageInput.style.height = "";
  syncComposerTextState();
  state.attachments = [];
  renderAttachmentPreview();
  setBusy(true);
  try {
    await postStreamingChat(text, attachments);
    renderMessages();
  } catch (error) {
    state.messages[state.messages.length - 1] = {
      role: "assistant",
      content: `调用失败：${error.message}`,
    };
    renderMessages();
  } finally {
    for (const attachment of attachments) {
      if (attachment.url && attachment.url.startsWith("blob:")) URL.revokeObjectURL(attachment.url);
    }
    setBusy(false);
  }
}

async function loadProfile() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return null;
  try {
    const response = await fetch("/api/profile");
    const payload = await response.json();
    renderMarkdownInto(profileMarkdown, payload.markdown || "暂无画像。");
    const profileState = payload.state || {};
    state.profileLastUpdatedAt = profileState.last_profile_updated_at || state.profileLastUpdatedAt || "";
    if (profileState.in_progress) {
      profileSummary.textContent = "企业画像正在后台更新，稍后会自动刷新...";
      startProfilePolling();
    } else if (profileState.last_error) {
      profileSummary.textContent = `上次更新失败：${profileState.last_error}`;
    } else {
      profileSummary.textContent = "查看当前企业的 MD 档案，画像会随对话自动更新。";
    }
    renderProfileDiff("", false, true);
    return payload;
  } catch (error) {
    profileSummary.textContent = `读取失败：${error.message}`;
    return null;
  }
}

function startProfilePolling() {
  if (state.profilePollTimer) return;
  const baselineUpdatedAt = state.profileLastUpdatedAt || "";
  const startedAt = Date.now();
  const tick = async () => {
    try {
      const response = await fetch("/api/profile");
      const payload = await response.json();
      const profileState = payload.state || {};
      const updatedAt = profileState.last_profile_updated_at || "";
      const finished = !profileState.in_progress && updatedAt && updatedAt !== baselineUpdatedAt;
      if (finished) {
        renderMarkdownInto(profileMarkdown, payload.markdown || "暂无画像。");
        state.profileLastUpdatedAt = updatedAt;
        profileSummary.textContent = profileState.last_profile_changed
          ? "企业画像已更新。"
          : "企业画像本轮无新增变更。";
        stopProfilePolling();
        return;
      }
      if (profileState.last_error && !profileState.in_progress) {
        profileSummary.textContent = `更新失败：${profileState.last_error}`;
        stopProfilePolling();
        return;
      }
      if (Date.now() - startedAt > 5 * 60 * 1000) {
        profileSummary.textContent = "画像更新仍在进行，请稍后手动刷新。";
        stopProfilePolling();
      }
    } catch (error) {
      profileSummary.textContent = `轮询失败：${error.message}`;
      stopProfilePolling();
    }
  };
  state.profilePollTimer = window.setInterval(tick, 3000);
  tick();
}

function formatMoney(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "");
  return number.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function describePendingPayload(item) {
  const action = item.action;
  if (action === "add") {
    const p = item.payload || {};
    const typeLabel = p.type === "income" ? "收入" : "支出";
    return `新增${typeLabel} ¥${formatMoney(p.amount)}（${p.date || "日期未填"} · ${p.description || "无摘要"} · ${p.category || "未分类"}）`;
  }
  if (action === "update") {
    const before = item.before || {};
    const changes = item.payload || {};
    const parts = Object.entries(changes).map(([key, value]) => {
      const label = ({ type: "类型", amount: "金额", date: "日期", description: "摘要", category: "分类" })[key] || key;
      const fromValue = key === "amount" ? `¥${formatMoney(before[key])}` : (before[key] ?? "");
      const toValue = key === "amount" ? `¥${formatMoney(value)}` : value;
      return `${label} ${fromValue} → ${toValue}`;
    });
    return `修改 ${before.date || ""} ${before.description || item.target_id}：${parts.join("、")}`;
  }
  if (action === "delete") {
    const b = item.before || {};
    const typeLabel = b.type === "income" ? "收入" : "支出";
    return `删除一笔${typeLabel}：${b.date || ""} ${b.description || ""} ¥${formatMoney(b.amount)}（${b.category || ""}）`;
  }
  return `${action} ${item.target_id || ""}`;
}

function renderWalletPending() {
  if (!walletPendingBar) return;
  const items = state.walletPending || [];
  if (!items.length) {
    walletPendingBar.hidden = true;
    walletPendingList.innerHTML = "";
    return;
  }
  walletPendingBar.hidden = false;
  walletPendingCount.textContent = `${items.length} 条待你确认`;
  walletPendingList.innerHTML = "";
  for (const item of items) {
    const wrap = document.createElement("div");
    wrap.className = "wallet-pending-item";
    const left = document.createElement("div");
    left.className = "wallet-pending-summary";
    const actionLabel = ({ add: "新增", update: "修改", delete: "删除" })[item.action] || item.action;
    const tag = document.createElement("span");
    tag.className = `wallet-pending-action ${item.action}`;
    tag.textContent = actionLabel;
    left.appendChild(tag);
    left.appendChild(document.createTextNode(describePendingPayload(item)));
    if (item.explanation) {
      const note = document.createElement("span");
      note.className = "wallet-pending-explain";
      note.textContent = `理由：${item.explanation}`;
      left.appendChild(note);
    }
    const controls = document.createElement("div");
    controls.className = "wallet-pending-controls";
    const confirmBtn = document.createElement("button");
    confirmBtn.type = "button";
    confirmBtn.className = "confirm";
    confirmBtn.textContent = "确认";
    confirmBtn.disabled = state.walletPendingBusyIds.has(item.id);
    confirmBtn.onclick = () => resolveWalletPending(item.id, "confirm");
    const rejectBtn = document.createElement("button");
    rejectBtn.type = "button";
    rejectBtn.className = "reject";
    rejectBtn.textContent = "拒绝";
    rejectBtn.disabled = state.walletPendingBusyIds.has(item.id);
    rejectBtn.onclick = () => resolveWalletPending(item.id, "reject");
    controls.appendChild(confirmBtn);
    controls.appendChild(rejectBtn);
    wrap.appendChild(left);
    wrap.appendChild(controls);
    walletPendingList.appendChild(wrap);
  }
}

async function resolveWalletPending(pendingId, action) {
  if (!pendingId || state.walletPendingBusyIds.has(pendingId)) return;
  state.walletPendingBusyIds.add(pendingId);
  renderWalletPending();
  try {
    const response = await fetch(`/api/wallet/pending/${encodeURIComponent(pendingId)}/${action}`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      alert(payload.error || `${action === "confirm" ? "确认" : "拒绝"}失败`);
      state.walletPending = state.walletPending.filter((item) => item.id !== pendingId);
    } else {
      state.walletPending = payload.pending || [];
      if (payload.transactions) {
        state.wallet = { transactions: payload.transactions, summary: payload.summary };
        if (walletDrawer && !walletDrawer.hidden) renderWallet();
      }
    }
  } catch (error) {
    alert(`网络错误：${error.message}`);
  } finally {
    state.walletPendingBusyIds.delete(pendingId);
    renderWalletPending();
  }
}

async function loadWalletPending() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return;
  try {
    const response = await fetch("/api/wallet/pending");
    if (!response.ok) return;
    const payload = await response.json();
    state.walletPending = payload.pending || [];
    renderWalletPending();
  } catch (_) {
    // silent — refreshed on next chat / page load
  }
}

function stopProfilePolling() {
  if (state.profilePollTimer) {
    window.clearInterval(state.profilePollTimer);
    state.profilePollTimer = null;
  }
}

async function refreshProfile() {
  if (!state.auth?.authenticated || state.auth?.needs_enterprise) return;
  if (!refreshProfileButton) return;
  const originalLabel = refreshProfileButton.textContent;
  refreshProfileButton.disabled = true;
  refreshProfileButton.textContent = "刷新中...";
  if (profileSummary) profileSummary.textContent = "正在检查画像状态...";
  try {
    const response = await fetch("/api/profile/refresh", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "刷新失败");
    }
    const message = payload.message || "";
    if (profileSummary) profileSummary.textContent = message;
    const profileState = payload.state || {};
    state.profileLastUpdatedAt = profileState.last_profile_updated_at || state.profileLastUpdatedAt || "";
    if (payload.status === "in_progress") {
      startProfilePolling();
    } else {
      await loadProfile();
      if (profileSummary && message) profileSummary.textContent = message;
    }
  } catch (error) {
    if (profileSummary) profileSummary.textContent = `刷新失败：${error.message}`;
  } finally {
    refreshProfileButton.disabled = false;
    refreshProfileButton.textContent = originalLabel || "刷新";
  }
}

function renderProfileDiff(diff, changed, hidden = false) {
  if (!profileDiffDetails || !profileDiff) return;
  profileDiffDetails.hidden = !SHOW_INTERNAL_PANELS || (hidden && !diff);
  profileDiffDetails.open = SHOW_INTERNAL_PANELS && Boolean(diff);
  profileDiff.textContent = diff || (changed ? "暂无变更记录。" : "本次无新增变更。");
}

function openProfile(load = true) {
  profileBackdrop.hidden = false;
  profileDrawer.classList.add("open");
  profileDrawer.setAttribute("aria-hidden", "false");
  if (load) loadProfile();
}

function closeProfile() {
  profileBackdrop.hidden = true;
  profileDrawer.classList.remove("open");
  profileDrawer.setAttribute("aria-hidden", "true");
}

function bindPromptChips() {
  document.querySelectorAll(".prompt-chip").forEach((button) => {
    button.onclick = () => sendMessage(button.textContent || "");
  });
}

composerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(messageInput.value);
});

imageButton.addEventListener("click", () => {
  if (state.busy) return;
  attachmentPopover.hidden = !attachmentPopover.hidden;
});

pickImageButton.addEventListener("click", () => {
  attachmentPopover.hidden = true;
  imageInput.click();
});

pickFileButton.addEventListener("click", () => {
  showComingSoon("上传文件");
});

pickVideoButton.addEventListener("click", () => {
  showComingSoon("上传视频");
});

imageInput.addEventListener("change", () => {
  for (const file of Array.from(imageInput.files || [])) {
    addAttachment(file);
  }
  imageInput.value = "";
});

fileInput.addEventListener("change", () => {
  for (const file of Array.from(fileInput.files || [])) {
    addAttachment(file);
  }
  fileInput.value = "";
});

videoInput.addEventListener("change", () => {
  for (const file of Array.from(videoInput.files || [])) {
    addAttachment(file);
  }
  videoInput.value = "";
});

document.addEventListener("click", (event) => {
  if (!attachmentPopover.hidden && !event.target.closest(".attachment-menu")) {
    attachmentPopover.hidden = true;
  }
});

async function startVoiceInput() {
  if (state.busy || state.recorder) return;
  if (!window.isSecureContext) {
    throw new Error("手机通过局域网 HTTP 打开时，浏览器会禁止麦克风。需要 HTTPS 后才能直接语音输入。");
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("当前浏览器不支持网页麦克风录音。");
  }
  if (!window.MediaRecorder) {
    throw new Error("当前浏览器不支持网页录音。");
  }
  state.recordingChunks = [];

  // Always upload the raw audio so the backend qwen3-asr-flash can
  // transcribe AND read emotion/language. Browser-side SpeechRecognition
  // is intentionally not used — it bypasses our ASR + emotion pipeline.
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  state.recorder = recorder;
  state.voiceMeter = startVoiceMeter(stream);
  micButton.classList.add("is-recording");
  recorder.ondataavailable = (event) => {
    if (event.data.size) state.recordingChunks.push(event.data);
  };
  recorder.onstop = () => {
    stream.getTracks().forEach((track) => track.stop());
    const voicePeak = stopVoiceMeter();
    micButton.classList.remove("is-recording");
    if (state.recordingChunks.length) {
      const blob = new Blob(state.recordingChunks, { type: recorder.mimeType || "audio/webm" });
      if (blob.size > 0 && voicePeak >= 0.0015) {
        addAttachment(new File([blob], `voice-${Date.now()}.webm`, { type: blob.type || "audio/webm" }));
      } else if (blob.size > 0) {
        const sendAnyway = confirm("录音音量很低，可能听不清。要仍然发送这段录音吗？\n\n如果你确定刚才说话了，请先检查浏览器麦克风权限和系统输入设备。");
        if (sendAnyway) {
          addAttachment(new File([blob], `voice-${Date.now()}.webm`, { type: blob.type || "audio/webm" }));
        }
      } else {
        alert("没有录到声音，请确认麦克风已对准并重试。");
      }
    } else {
      alert("没有录到声音，请确认麦克风已对准并重试。");
    }
    state.recorder = null;
    state.recordingChunks = [];
  };
  recorder.start();
}

function startVoiceMeter(stream) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return null;
  try {
    const context = new AudioContextClass();
    if (context.state === "suspended") {
      context.resume().catch(() => {});
    }
    const analyser = context.createAnalyser();
    analyser.fftSize = 1024;
    const source = context.createMediaStreamSource(stream);
    source.connect(analyser);
    const data = new Uint8Array(analyser.fftSize);
    const meter = { context, source, analyser, data, peak: 0, timer: 0 };
    meter.timer = window.setInterval(() => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (const value of data) {
        const centered = (value - 128) / 128;
        sum += centered * centered;
      }
      meter.peak = Math.max(meter.peak, Math.sqrt(sum / data.length));
    }, 120);
    return meter;
  } catch (_error) {
    return null;
  }
}

function stopVoiceMeter() {
  const meter = state.voiceMeter;
  state.voiceMeter = null;
  if (!meter) return Number.POSITIVE_INFINITY;
  window.clearInterval(meter.timer);
  try {
    meter.source.disconnect();
  } catch (_error) {}
  try {
    meter.context.close();
  } catch (_error) {}
  return meter.peak || 0;
}

function stopVoiceInput() {
  if (state.recorder && state.recorder.state !== "inactive") {
    state.recorder.stop();
  }
}

micButton.addEventListener("click", async () => {
  if (state.recorder) {
    stopVoiceInput();
    return;
  }
  try {
    await startVoiceInput();
  } catch (error) {
    micButton.classList.remove("is-recording");
    state.recorder = null;
    stopVoiceMeter();
    let hint = error.message || String(error);
    if (error.name === "NotAllowedError" || error.name === "SecurityError") {
      hint = "浏览器或系统没有授权麦克风。请在浏览器地址栏左侧的锁形图标里允许麦克风，并确认 macOS“系统设置 → 隐私与安全 → 麦克风”里勾上了 Chrome。";
    } else if (error.name === "NotFoundError" || error.name === "OverconstrainedError") {
      hint = "找不到可用的麦克风设备，请检查耳麦/外接麦克风是否插好。";
    } else if (error.name === "NotReadableError") {
      hint = "麦克风被其他应用占用，请关闭 Zoom/腾讯会议等程序后重试。";
    }
    alert(`无法启动语音输入：${hint}`);
  }
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage(messageInput.value);
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 180)}px`;
  syncComposerTextState();
});

async function sendAuthCode(phone, targetInput, button) {
  showAuthMessage("");
  button.disabled = true;
  try {
    const payload = await postJson("/api/auth/sms/send", { phone });
    targetInput.focus();
    showAuthMessage("验证码已发送，请查收短信");
  } catch (error) {
    showAuthMessage(error.message, true);
  } finally {
    button.disabled = false;
  }
}

sendLoginCodeButton.onclick = () => sendAuthCode(loginPhone.value.trim(), loginCode, sendLoginCodeButton);
sendRegisterCodeButton.onclick = () => sendAuthCode(registerPhone.value.trim(), registerCode, sendRegisterCodeButton);

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showAuthMessage("");
  try {
    const auth = state.loginMode === "sms"
      ? await postJson("/api/auth/sms/verify", {
          phone: loginPhone.value.trim(),
          code: loginCode.value.trim(),
        })
      : await postJson("/api/auth/password/login", {
          phone: loginPhone.value.trim(),
          password: loginPassword.value,
        });
    applyAuthState(auth);
    if (auth.needs_enterprise) {
      showAuthMessage("首次登录，请创建企业档案。");
      enterpriseName.focus();
    } else {
      showAuthMessage("");
      await loadAccountProfile();
      await loadMessages();
      await loadProfile();
    }
  } catch (error) {
    showAuthMessage(error.message, true);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showAuthMessage("");
  try {
    const auth = await postJson("/api/auth/register", {
      phone: registerPhone.value.trim(),
      password: registerPassword.value,
      code: registerCode.value.trim(),
    });
    applyAuthState(auth);
    if (auth.needs_enterprise) {
      showAuthMessage("注册成功，请创建企业档案。");
      enterpriseName.focus();
    }
  } catch (error) {
    showAuthMessage(error.message, true);
  }
});

passwordLoginTab.onclick = () => setLoginMode("password");
smsLoginTab.onclick = () => setLoginMode("sms");
openRegisterButton.onclick = () => showRegister(true);
backToLoginButton.onclick = () => showRegister(false);

enterpriseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showAuthMessage("");
  try {
    const payload = await postJson("/api/enterprise/create", {
      name: enterpriseName.value.trim(),
      credit_code: enterpriseCreditCode.value.trim(),
    });
    applyAuthState(payload.auth);
    await loadAccountProfile();
    await loadMessages();
    await loadProfile();
    showAuthMessage("");
  } catch (error) {
    showAuthMessage(error.message, true);
  }
});

openProfileButton.onclick = openProfile;
closeProfileButton.onclick = closeProfile;
profileBackdrop.onclick = closeProfile;
refreshProfileButton.onclick = refreshProfile;
openWalletButton.onclick = openWallet;
closeWalletButton.onclick = closeWallet;
walletBackdrop.onclick = closeWallet;
openLoanButton.onclick = openLoan;
closeLoanButton.onclick = closeLoan;
loanBackdrop.onclick = closeLoan;
refreshLoanButton.onclick = recomputeLoanEstimate;
openVideoCallButton.addEventListener("click", () => {
  showComingSoon("视频通话");
});
closeVideoCallButton.onclick = closeVideoCall;
videoCallBackdrop.onclick = closeVideoCall;
videoCallStartButton.onclick = startVideoCallPreview;
videoCallMuteButton.onclick = toggleVideoCallMute;
videoCallEndButton.onclick = stopVideoCallStream;
importWalletButton.onclick = () => walletCsvInput.click();
addWalletEntryButton.onclick = () => {
  walletEntryForm.hidden = !walletEntryForm.hidden;
  if (!walletEntryForm.hidden) walletAmount.focus();
};
walletPeriodTabs.forEach((button) => {
  button.onclick = () => {
    state.walletPeriod = button.dataset.walletPeriod || "day";
    renderWallet();
  };
});
walletChartModeButtons.forEach((button) => {
  button.onclick = () => {
    state.walletChartMode = button.dataset.walletChart || "bar";
    renderWallet();
  };
});
walletCsvInput.addEventListener("change", async () => {
  const [file] = Array.from(walletCsvInput.files || []);
  walletCsvInput.value = "";
  if (!file) return;
  const body = new FormData();
  body.append("file", file, file.name || "wallet.csv");
  walletMessage.textContent = "正在导入流水...";
  try {
    const response = await fetch("/api/wallet/import", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "导入失败");
    renderWallet(payload);
  } catch (error) {
    walletMessage.textContent = error.message;
  }
});
walletEntryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  walletMessage.textContent = "正在添加流水...";
  try {
    const payload = await postJson("/api/wallet/transaction", {
      date: walletDate.value,
      type: walletType.value,
      amount: walletAmount.value,
      category: walletCategory.value,
      description: walletDescription.value,
    });
    walletAmount.value = "";
    walletCategory.value = "";
    walletDescription.value = "";
    renderWallet(payload);
  } catch (error) {
    walletMessage.textContent = error.message;
  }
});
mobileMenuButton.onclick = () => setMobileSidebarOpen(!appShell.classList.contains("sidebar-open"));
sidebarToggleButton.onclick = () => {
  if (isMobileLayout()) {
    setMobileSidebarOpen(false);
    return;
  }
  setSidebarCollapsed(!appShell.classList.contains("sidebar-collapsed"));
};
openProfileButton.addEventListener("click", () => {
  if (isMobileLayout()) setMobileSidebarOpen(false);
});
openWalletButton.addEventListener("click", () => {
  if (isMobileLayout()) setMobileSidebarOpen(false);
});
openLoanButton.addEventListener("click", () => {
  if (isMobileLayout()) setMobileSidebarOpen(false);
});
document.addEventListener("click", (event) => {
  if (!isMobileLayout() || !appShell.classList.contains("sidebar-open")) return;
  if (event.target.closest(".sidebar") || event.target.closest(".mobile-menu-button")) return;
  setMobileSidebarOpen(false);
});
window.addEventListener("resize", () => {
  if (!isMobileLayout()) setMobileSidebarOpen(false);
  syncResponsiveCopy();
});
accountButton.onclick = () => {
  if (isMobileLayout()) setMobileSidebarOpen(false);
  openAccountModal();
};
closeAccountButton.onclick = closeAccountModal;
accountBackdrop.onclick = closeAccountModal;
accountTabUser.onclick = () => setAccountTab("user");
accountTabEnterprise.onclick = () => setAccountTab("enterprise");
avatarUploadButton.onclick = () => avatarInput.click();

avatarInput.addEventListener("change", async () => {
  const [file] = Array.from(avatarInput.files || []);
  avatarInput.value = "";
  if (!file) return;
  const body = new FormData();
  body.append("avatar", file, file.name || "avatar.png");
  showAccountMessage("正在上传头像...");
  try {
    const response = await fetch("/api/account/avatar", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "上传失败");
    state.accountProfile = payload.profile || state.accountProfile;
    if (payload.auth) state.auth = payload.auth;
    fillAccountForm(state.accountProfile);
    applyAuthState(state.auth);
    showAccountMessage("头像已更新");
  } catch (error) {
    showAccountMessage(error.message, true);
  }
});

accountProfileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showAccountMessage("正在保存...");
  try {
    const payload = await postJson("/api/account/profile", collectAccountProfilePayload());
    state.accountProfile = payload.profile || state.accountProfile;
    if (payload.auth) state.auth = payload.auth;
    fillAccountForm(state.accountProfile);
    applyAuthState(state.auth);
    showAccountMessage("资料已保存");
  } catch (error) {
    showAccountMessage(error.message, true);
  }
});

logoutButton.onclick = async () => {
  await postJson("/api/auth/logout");
  state.auth = { authenticated: false };
  state.accountProfile = null;
  closeAccountModal();
  applyAuthState(state.auth);
};

document.querySelectorAll(".brand-mark").forEach((mark) => {
  mark.style.backgroundImage = 'url("/static/assets/customer-manager-plus.png")';
  mark.classList.add("has-image");
});
setSidebarCollapsed(localStorage.getItem("wewallet.sidebarCollapsed") === "1");
syncResponsiveCopy();
syncComposerTextState();
renderMessages();
bootstrapApp();

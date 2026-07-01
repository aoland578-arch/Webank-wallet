(function () {
  const colors = {
    application: "#0f766e",
    person: "#2563eb",
    enterprise: "#7c3aed",
    claim: "#0891b2",
    document: "#ca8a04",
    video_call: "#db2777",
    risk_signal: "#dc2626",
    transaction: "#16a34a",
  };
  const subScoreNames = ["身份一致性", "经营真实性", "申请逻辑", "材料配合度"];

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function requestJson(url) {
    return fetch(url, { credentials: "same-origin" }).then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.error || "图谱数据加载失败");
      }
      return payload;
    });
  }

  class RiskGraphView {
    constructor() {
      this.openButton = $("openRiskGraphButton");
      this.closeButton = $("closeRiskGraphButton");
      this.backdrop = $("riskGraphBackdrop");
      this.modal = $("riskGraphModal");
      this.canvas = $("riskGraphCanvas");
      this.empty = $("riskGraphEmpty");
      this.score = $("riskGraphScore");
      this.recommendation = $("riskGraphRecommendation");
      this.fraudType = $("riskGraphFraudType");
      this.caseId = $("riskGraphCaseId");
      this.samples = $("riskGraphSamples");
      this.detail = $("riskGraphDetailCard");
      this.bars = $("riskGraphBars");
      this.filterButtons = Array.from(document.querySelectorAll("[data-risk-bucket]"));
      this.nodes = [];
      this.edges = [];
      this.animationFrame = 0;
      this.dragging = null;
      this.selectedNode = null;
      this.activeBucket = "high";
      this.activeCaseId = "";
      this.lastTick = performance.now();
    }

    bind() {
      if (!this.openButton || !this.modal || !this.canvas) return;
      this.openButton.addEventListener("click", () => this.open());
      this.closeButton?.addEventListener("click", () => this.close());
      this.backdrop?.addEventListener("click", () => this.close());
      this.filterButtons.forEach((button) => {
        button.addEventListener("click", () => {
          this.activeBucket = button.dataset.riskBucket || "high";
          this.activeCaseId = "";
          this.load();
        });
      });
      this.canvas.addEventListener("pointerdown", (event) => this.onPointerDown(event));
      this.canvas.addEventListener("pointermove", (event) => this.onPointerMove(event));
      this.canvas.addEventListener("pointerup", () => this.onPointerUp());
      this.canvas.addEventListener("pointercancel", () => this.onPointerUp());
      window.addEventListener("resize", () => this.resize());
    }

    setAuthenticated(authenticated) {
      if (this.openButton) this.openButton.disabled = !authenticated;
    }

    open() {
      this.backdrop.hidden = false;
      this.modal.hidden = false;
      this.modal.setAttribute("aria-hidden", "false");
      this.resize();
      this.load();
    }

    close() {
      this.backdrop.hidden = true;
      this.modal.hidden = true;
      this.modal.setAttribute("aria-hidden", "true");
      cancelAnimationFrame(this.animationFrame);
    }

    async load() {
      this.showLoading("正在加载 GNN 图谱...");
      this.filterButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.riskBucket === this.activeBucket && !this.activeCaseId);
      });
      try {
        const params = new URLSearchParams();
        if (this.activeCaseId) params.set("case_id", this.activeCaseId);
        else params.set("bucket", this.activeBucket);
        const payload = await requestJson(`/api/risk-graph?${params.toString()}`);
        this.renderPayload(payload);
      } catch (error) {
        this.showLoading(error.message || "图谱数据加载失败");
      }
    }

    showLoading(message) {
      this.empty.hidden = false;
      this.empty.textContent = message;
    }

    renderPayload(payload) {
      this.empty.hidden = true;
      this.score.textContent = `${Math.round(payload.risk_score)}%`;
      this.recommendation.textContent = payload.recommendation_label || "-";
      this.fraudType.textContent = payload.fraud_type_label || "-";
      this.caseId.textContent = payload.case_id ? payload.case_id.slice(0, 8) : "-";
      this.renderSamples(payload.samples || [], payload.case_id);
      this.renderBars(payload.sub_scores || []);

      const rect = this.canvas.getBoundingClientRect();
      const cx = rect.width / 2 || 360;
      const cy = rect.height / 2 || 260;
      this.nodes = (payload.nodes || []).map((node, index) => {
        const angle = (index / Math.max(payload.nodes.length, 1)) * Math.PI * 2;
        const radius = 80 + (index % 4) * 28;
        return {
          ...node,
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius,
          vx: 0,
          vy: 0,
        };
      });
      const byId = new Map(this.nodes.map((node) => [node.id, node]));
      this.edges = (payload.edges || [])
        .map((edge) => ({ ...edge, sourceNode: byId.get(edge.source), targetNode: byId.get(edge.target), phase: Math.random() }))
        .filter((edge) => edge.sourceNode && edge.targetNode);
      this.selectedNode = this.nodes.find((node) => node.type === "application") || this.nodes[0] || null;
      this.renderDetail(this.selectedNode);
      this.lastTick = performance.now();
      cancelAnimationFrame(this.animationFrame);
      this.tick();
    }

    renderSamples(samples, activeCaseId) {
      if (!this.samples) return;
      this.samples.innerHTML = samples.slice(0, 8).map((sample) => `
        <button class="risk-graph-sample" type="button" data-case-id="${escapeHtml(sample.case_id)}">
          <strong>${escapeHtml(sample.fraud_type_label)}</strong>
          <span>${escapeHtml(sample.recommendation_label)} · 可信分 ${Math.round(sample.score)}</span>
        </button>
      `).join("");
      this.samples.querySelectorAll("[data-case-id]").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.caseId === activeCaseId);
        button.addEventListener("click", () => {
          this.activeCaseId = button.dataset.caseId || "";
          this.load();
        });
      });
    }

    renderBars(subScores) {
      if (!this.bars) return;
      this.bars.innerHTML = subScoreNames.map((name, index) => {
        const value = Number(subScores[index] || 0);
        return `
          <div class="risk-graph-bar">
            <span><b>${name}</b><em>${Math.round(value * 100)}%</em></span>
            <div class="risk-graph-bar-track"><div class="risk-graph-bar-fill" style="width:${Math.max(4, value * 100)}%"></div></div>
          </div>
        `;
      }).join("");
    }

    renderDetail(node) {
      if (!this.detail) return;
      if (!node) {
        this.detail.innerHTML = "<p>请选择一个节点查看详情。</p>";
        return;
      }
      this.detail.innerHTML = `
        <h4>${escapeHtml(node.label)}</h4>
        <p>${escapeHtml(node.type_label)} · 风险强度 ${Math.round(Number(node.risk || 0) * 100)}%</p>
        <p>${escapeHtml(node.detail || "")}</p>
      `;
    }

    resize() {
      if (!this.canvas) return;
      const rect = this.canvas.getBoundingClientRect();
      this.canvas.setAttribute("viewBox", `0 0 ${Math.max(rect.width, 1)} ${Math.max(rect.height, 1)}`);
    }

    tick() {
      const now = performance.now();
      const dt = Math.min((now - this.lastTick) / 16.67, 2);
      this.lastTick = now;
      this.step(dt);
      this.draw(now);
      this.animationFrame = requestAnimationFrame(() => this.tick());
    }

    step(dt) {
      const rect = this.canvas.getBoundingClientRect();
      const width = rect.width || 720;
      const height = rect.height || 520;
      const centerX = width / 2;
      const centerY = height / 2;

      for (let i = 0; i < this.nodes.length; i += 1) {
        const a = this.nodes[i];
        for (let j = i + 1; j < this.nodes.length; j += 1) {
          const b = this.nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distSq = Math.max(dx * dx + dy * dy, 64);
          const force = 900 / distSq;
          const dist = Math.sqrt(distSq);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx += fx * dt;
          a.vy += fy * dt;
          b.vx -= fx * dt;
          b.vy -= fy * dt;
        }
      }

      this.edges.forEach((edge) => {
        const a = edge.sourceNode;
        const b = edge.targetNode;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const desired = edge.risk_flow ? 104 : 126;
        const force = (dist - desired) * 0.012;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx * dt;
        a.vy += fy * dt;
        b.vx -= fx * dt;
        b.vy -= fy * dt;
      });

      this.nodes.forEach((node) => {
        if (node === this.dragging) return;
        node.vx += (centerX - node.x) * 0.002 * dt;
        node.vy += (centerY - node.y) * 0.002 * dt;
        node.vx *= 0.86;
        node.vy *= 0.86;
        node.x = Math.min(Math.max(node.x + node.vx * dt, 32), width - 32);
        node.y = Math.min(Math.max(node.y + node.vy * dt, 32), height - 32);
      });
    }

    draw(now) {
      const svg = this.canvas;
      const linkMarkup = this.edges.map((edge) => `
        <line class="risk-graph-link ${edge.risk_flow ? "is-risk-flow" : ""}" x1="${edge.sourceNode.x}" y1="${edge.sourceNode.y}" x2="${edge.targetNode.x}" y2="${edge.targetNode.y}" />
      `).join("");
      const pulseMarkup = this.edges.filter((edge) => edge.risk_flow).map((edge) => {
        const t = ((now / 1600) + edge.phase) % 1;
        const x = edge.sourceNode.x + (edge.targetNode.x - edge.sourceNode.x) * t;
        const y = edge.sourceNode.y + (edge.targetNode.y - edge.sourceNode.y) * t;
        return `<circle class="risk-graph-pulse" cx="${x}" cy="${y}" r="4" />`;
      }).join("");
      const nodeMarkup = this.nodes.map((node) => {
        const isSelected = this.selectedNode && this.selectedNode.id === node.id;
        const color = colors[node.type] || "#64748b";
        const riskStroke = Number(node.risk || 0) > 0.55 ? "#ef4444" : "rgba(255,255,255,0.94)";
        return `
          <g class="risk-graph-node" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.x},${node.y})">
            <circle r="${Number(node.size || 22)}" fill="${color}" stroke="${isSelected ? "#111827" : riskStroke}" stroke-width="${isSelected ? 3 : 2}" opacity="${0.74 + Math.min(Number(node.risk || 0), 1) * 0.24}" />
            <text y="${Number(node.size || 22) + 16}" text-anchor="middle">${escapeHtml(node.label)}</text>
          </g>
        `;
      }).join("");
      svg.innerHTML = `${linkMarkup}${pulseMarkup}${nodeMarkup}`;
    }

    pointerPosition(event) {
      const rect = this.canvas.getBoundingClientRect();
      return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    }

    nearestNode(event) {
      const pos = this.pointerPosition(event);
      let best = null;
      let bestDistance = Infinity;
      this.nodes.forEach((node) => {
        const dx = node.x - pos.x;
        const dy = node.y - pos.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < bestDistance && distance < Number(node.size || 22) + 10) {
          best = node;
          bestDistance = distance;
        }
      });
      return best;
    }

    onPointerDown(event) {
      const node = this.nearestNode(event);
      if (!node) return;
      this.dragging = node;
      this.selectedNode = node;
      this.renderDetail(node);
      this.canvas.setPointerCapture?.(event.pointerId);
      const pos = this.pointerPosition(event);
      node.x = pos.x;
      node.y = pos.y;
      node.vx = 0;
      node.vy = 0;
    }

    onPointerMove(event) {
      if (!this.dragging) return;
      const pos = this.pointerPosition(event);
      this.dragging.x = pos.x;
      this.dragging.y = pos.y;
      this.dragging.vx = 0;
      this.dragging.vy = 0;
    }

    onPointerUp() {
      this.dragging = null;
    }
  }

  window.RiskGraphView = RiskGraphView;
})();

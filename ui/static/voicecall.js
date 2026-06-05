/*
 * 视频通话模块（通话版小微）。
 *
 * 独立于 chat.js 主线：只读已有弹窗的 DOM，用 addEventListener 追加监听，
 * 不覆盖 chat.js 已绑定的 onclick。
 *
 * 两套语音引擎，启动时按后端 /api/voicecall/realtime-config 自动选：
 *   1) realtime（首选）：端到端实时语音 stepaudio-2.5-realtime。
 *      麦克风 → PCM16/24kHz → WebSocket 中继(/api/voicecall/realtime-config 给地址) →
 *      StepFun → 回传 PCM16 音频边收边放 + 字幕。server_vad 自动断句、可打断。
 *      看材料：截一帧发 {type:"vision.frame"}，中继调 step-3.7-flash 描述后注入会话，
 *      小微当场"看到并转述"。
 *   2) placeholder（回落）：浏览器原生 Web Speech API 做 STT/TTS（无 STEP_API_KEY 或
 *      浏览器不支持时）。即旧版形态。
 *
 * 仅在 localhost / https 下可用（getUserMedia + WebSocket/AudioContext 安全上下文）。
 */
(function () {
  "use strict";

  const modal = document.getElementById("videoCallModal");
  const selfVideo = document.getElementById("videoCallSelf");
  const caption = document.getElementById("videoCallCaption");
  const statusEl = document.getElementById("videoCallStatus");
  const talkButton = document.getElementById("videoCallTalkButton");
  const startButton = document.getElementById("videoCallStartButton"); // 现作"摄像头开关"
  const muteButton = document.getElementById("videoCallMuteButton");
  const showDocButton = document.getElementById("videoCallShowDocButton");
  const endButton = document.getElementById("videoCallEndButton");
  const closeButton = document.getElementById("closeVideoCallButton");
  const listeningEl = document.getElementById("videoCallListening");
  const backdrop = document.getElementById("videoCallBackdrop");

  if (!talkButton) return; // 没有按钮就不挂（防御）

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const RATE = 24000; // stepaudio-2.5-realtime 的 PCM16 采样率

  const call = {
    active: false,
    engine: null, // 当前引擎实例（realtime 或 placeholder）
    stream: null, // 仅当 chat.js 没开摄像头时我们自己开的流
  };

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function showCaption(text) {
    if (!caption) return;
    caption.textContent = text || "";
    caption.hidden = !text;
  }

  function setShowDocEnabled(on) {
    if (showDocButton) showDocButton.disabled = !on;
  }

  function setListening(on) {
    if (listeningEl) listeningEl.style.visibility = on ? "visible" : "hidden";
  }

  // 当前正在用的媒体流（voicecall 自己开的，或 chat.js 开的）。
  function currentStream() {
    return (selfVideo && selfVideo.srcObject) || call.stream || null;
  }

  function toggleMute() {
    const stream = currentStream();
    if (!stream) return;
    const tracks = stream.getAudioTracks();
    if (!tracks.length) return;
    const muted = tracks[0].enabled; // 现在开着 → 点一下变静音
    tracks.forEach((t) => { t.enabled = !muted; });
    if (muteButton) {
      muteButton.classList.toggle("is-active", muted);
      const label = muteButton.querySelector(".vc-btn-label");
      if (label) label.textContent = muted ? "已静音" : "静音";
    }
  }

  function toggleCamera() {
    const stream = currentStream();
    if (!stream) return;
    const tracks = stream.getVideoTracks();
    if (!tracks.length) return;
    const on = tracks[0].enabled;
    tracks.forEach((t) => { t.enabled = !on; });
    if (startButton) startButton.classList.toggle("is-off", on);
    if (selfVideo) selfVideo.style.opacity = on ? "0" : "1";
  }

  // 复用 chat.js 已开的摄像头流；没有就自己开一路（带麦克风）。
  async function ensureStream() {
    if (selfVideo && selfVideo.srcObject) return selfVideo.srcObject;
    if (!navigator.mediaDevices?.getUserMedia) return null;
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    call.stream = stream;
    if (selfVideo) {
      selfVideo.srcObject = stream;
      selfVideo.hidden = false;
    }
    const ph = document.getElementById("videoCallSelfPlaceholder");
    if (ph) ph.hidden = true;
    return stream;
  }

  // 从摄像头画面截一帧，缩到 640 宽的 jpeg dataURL；画面没准备好返回 ""。
  function captureFrame() {
    if (!selfVideo || !selfVideo.videoWidth) return "";
    const maxW = 640;
    const scale = Math.min(1, maxW / selfVideo.videoWidth);
    const w = Math.round(selfVideo.videoWidth * scale);
    const h = Math.round(selfVideo.videoHeight * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(selfVideo, 0, 0, w, h);
    try {
      return canvas.toDataURL("image/jpeg", 0.6);
    } catch (e) {
      return ""; // 跨域污染等
    }
  }

  // ── PCM16 <-> base64 工具 ───────────────────────────────────────────────
  function floatTo16BitBase64(float32) {
    const out = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    const bytes = new Uint8Array(out.buffer);
    let bin = "";
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  }

  function base64ToFloat32(b64) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const i16 = new Int16Array(bytes.buffer, 0, Math.floor(bytes.length / 2));
    const f32 = new Float32Array(i16.length);
    for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 32768;
    return f32;
  }

  // ════════════════════════════════════════════════════════════════════════
  // 引擎 1：实时语音（stepaudio-2.5-realtime，经本地中继）
  // ════════════════════════════════════════════════════════════════════════
  function RealtimeEngine(wsUrl) {
    let ws = null;
    let audioCtx = null;
    let micSource = null;
    let processor = null;
    let nextPlayTime = 0; // 播放调度游标
    const sources = new Set(); // 已排期的播放节点，便于打断时停掉
    let selfCaption = ""; // 小微当前句子字幕累积
    let lastAutoVision = 0; // 上次自动看画面的时间戳（节流）
    let visionBusy = false; // 一次看画面在途，避免叠发
    const AUTO_VISION_MIN_GAP_MS = 3000; // 每轮看一眼，但最快 3 秒一次

    // 每轮自动看一眼：你一开口就截一帧静默发给中继，等你说完小微回应时已看到当前画面。
    function autoVision() {
      const now = Date.now();
      if (visionBusy || now - lastAutoVision < AUTO_VISION_MIN_GAP_MS) return;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const frame = captureFrame();
      if (!frame) return;
      lastAutoVision = now;
      visionBusy = true;
      ws.send(JSON.stringify({ type: "vision.frame", frame, auto: true }));
    }

    function stopPlayback() {
      for (const s of sources) {
        try { s.stop(); } catch (e) {}
      }
      sources.clear();
      nextPlayTime = 0;
    }

    function playDelta(f32) {
      if (!audioCtx || !f32.length) return;
      const buf = audioCtx.createBuffer(1, f32.length, RATE);
      buf.copyToChannel(f32, 0);
      const src = audioCtx.createBufferSource();
      src.buffer = buf;
      src.connect(audioCtx.destination);
      const now = audioCtx.currentTime;
      if (nextPlayTime < now) nextPlayTime = now;
      src.start(nextPlayTime);
      nextPlayTime += buf.duration;
      sources.add(src);
      src.onended = () => sources.delete(src);
    }

    function handleEvent(ev) {
      switch (ev.type) {
        case "input_audio_buffer.speech_started":
          // 客户开口 → 打断小微正在播的话（barge-in）+ 顺手截一帧让她"看到"当前画面。
          stopPlayback();
          setStatus("在听您说...");
          autoVision();
          break;
        case "response.audio.delta":
          if (ev.delta) playDelta(base64ToFloat32(ev.delta));
          break;
        case "response.audio_transcript.delta":
          selfCaption += ev.delta || "";
          showCaption("小微：" + selfCaption);
          break;
        case "response.audio_transcript.done":
          if (ev.transcript) showCaption("小微：" + ev.transcript);
          selfCaption = "";
          break;
        case "conversation.item.input_audio_transcription.completed":
          if (ev.transcript) setStatus("我：" + ev.transcript);
          break;
        case "vision.described":
          visionBusy = false;
          // 自动看画面是静默的，不打扰字幕/状态；只有手动"看材料"才提示。
          if (!ev.auto) setStatus("小微看了看材料...");
          break;
        case "error":
          setStatus("出错了：" + (ev.error?.message || ev.message || "未知"));
          break;
      }
    }

    async function start() {
      const stream = await ensureStream();
      if (!stream) throw new Error("无法获取摄像头/麦克风");
      audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: RATE });
      if (audioCtx.state === "suspended") await audioCtx.resume();

      ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        setStatus("通话已接通，请直接说话，小微在听...");
        setShowDocEnabled(true);
        // 麦克风采集 → PCM16 → input_audio_buffer.append
        micSource = audioCtx.createMediaStreamSource(stream);
        processor = audioCtx.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (e) => {
          if (!ws || ws.readyState !== WebSocket.OPEN) return;
          const input = e.inputBuffer.getChannelData(0);
          ws.send(JSON.stringify({
            type: "input_audio_buffer.append",
            audio: floatTo16BitBase64(input),
          }));
        };
        micSource.connect(processor);
        processor.connect(audioCtx.destination); // ScriptProcessor 需接入图才触发
      };
      ws.onmessage = (e) => {
        let data;
        try { data = JSON.parse(e.data); } catch (err) { return; }
        handleEvent(data);
      };
      ws.onerror = () => setStatus("连接出错，请稍后重试。");
      ws.onclose = () => { if (call.active) setStatus("连接已断开。"); };
    }

    function showDocument() {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const frame = captureFrame();
      if (!frame) { setStatus("画面还没准备好，请稍等。"); return; }
      setStatus("正在把材料给小微看...");
      ws.send(JSON.stringify({ type: "vision.frame", frame }));
    }

    function stop() {
      stopPlayback();
      try { processor && processor.disconnect(); } catch (e) {}
      try { micSource && micSource.disconnect(); } catch (e) {}
      processor = null;
      micSource = null;
      if (ws) {
        try { ws.close(); } catch (e) {}
        ws = null;
      }
      if (audioCtx) {
        try { audioCtx.close(); } catch (e) {}
        audioCtx = null;
      }
    }

    return { start, stop, showDocument };
  }

  // ════════════════════════════════════════════════════════════════════════
  // 引擎 2：浏览器原生语音占位（回落用，旧版形态）
  // 麦克风 → SpeechRecognition → POST /api/voicecall → Doubao/StepFun 文本 →
  // SpeechSynthesis 念出 + 字幕。看材料随每轮自动截帧。
  // ════════════════════════════════════════════════════════════════════════
  function PlaceholderEngine() {
    const state = { recognition: null, speaking: false, history: [], sending: false };

    function speak(text) {
      return new Promise((resolve) => {
        if (!window.speechSynthesis) { resolve(); return; }
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = "zh-CN";
        utter.rate = 1.05;
        const zh = window.speechSynthesis.getVoices().find((v) => /zh|Chinese/i.test(v.lang || v.name));
        if (zh) utter.voice = zh;
        utter.onend = resolve;
        utter.onerror = resolve;
        window.speechSynthesis.speak(utter);
      });
    }

    async function sendTurn(transcript) {
      if (state.sending) return;
      state.sending = true;
      setStatus("小微正在听...");
      const frame = captureFrame();
      try {
        const resp = await fetch("/api/voicecall", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ transcript, frame, history: state.history.slice(-8) }),
        });
        const data = await resp.json();
        if (!resp.ok || data.error) throw new Error(data.error || `HTTP ${resp.status}`);
        const reply = String(data.reply || "").trim();
        state.history.push({ role: "user", content: transcript });
        state.history.push({ role: "assistant", content: reply });
        showCaption("小微：" + reply);
        state.speaking = true;
        pauseRecognition();
        await speak(reply);
        state.speaking = false;
        if (call.active) { setStatus("请说话，小微在听..."); startRecognition(); }
      } catch (e) {
        setStatus("网络好像有点慢：" + (e.message || e));
      } finally {
        state.sending = false;
      }
    }

    function buildRecognition() {
      const rec = new SpeechRecognition();
      rec.lang = "zh-CN";
      rec.continuous = true;
      rec.interimResults = true;
      rec.onresult = (event) => {
        if (state.speaking) return;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            const text = (result[0].transcript || "").trim();
            if (text) sendTurn(text);
          }
        }
      };
      rec.onend = () => {
        if (call.active && !state.speaking) {
          try { rec.start(); } catch (e) {}
        }
      };
      rec.onerror = (e) => {
        if (e.error === "not-allowed" || e.error === "service-not-allowed") {
          setStatus("麦克风权限被拒绝，无法对话。");
          stopCall();
        }
      };
      return rec;
    }

    function startRecognition() {
      if (!state.recognition) state.recognition = buildRecognition();
      try { state.recognition.start(); } catch (e) {}
    }
    function pauseRecognition() {
      if (state.recognition) { try { state.recognition.stop(); } catch (e) {} }
    }

    async function start() {
      if (!SpeechRecognition) throw new Error("当前浏览器不支持语音识别（建议用 Chrome/Edge）。");
      await ensureStream();
      setShowDocEnabled(false); // 占位模式每轮自动截帧，无需手动按钮
      setStatus("通话已开始，请直接说话，小微在听...");
      sendTurn("（通话刚接通，请用一句话热情地跟客户打招呼并自我介绍）");
      startRecognition();
    }

    function stop() {
      state.speaking = false;
      pauseRecognition();
      state.recognition = null;
      if (window.speechSynthesis) window.speechSynthesis.cancel();
    }

    function showDocument() { /* 占位模式不需要：每轮自动带画面 */ }

    return { start, stop, showDocument };
  }

  // ── 通话生命周期 ─────────────────────────────────────────────────────────
  async function fetchBackend() {
    try {
      const resp = await fetch("/api/voicecall/realtime-config");
      if (!resp.ok) return null;
      return await resp.json();
    } catch (e) {
      return null;
    }
  }

  function resolveWsUrl(cfg) {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    let base;
    if (cfg.ws_url) {
      base = cfg.ws_url; // 1) 完整地址
    } else if (cfg.relay_path) {
      base = `${proto}//${location.host}${cfg.relay_path}`; // 2) 同源路径（http→ws / https→wss）
    } else {
      base = `${proto}//${location.hostname}:${cfg.relay_port}`; // 3) 本地按端口直连
    }
    // 带上中继访问令牌（浏览器 WS 设不了 header，只能走 query）。
    if (cfg.token) base += (base.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(cfg.token);
    return base;
  }

  async function startCall() {
    if (call.active) return;
    call.active = true;
    talkButton.textContent = "结束对话";
    if (muteButton) muteButton.disabled = false;
    showCaption("");
    setStatus("正在接通…");
    setListening(true);

    const cfg = await fetchBackend();
    const useRealtime = cfg && cfg.enabled && "WebSocket" in window &&
      (window.AudioContext || window.webkitAudioContext);

    try {
      call.engine = useRealtime ? RealtimeEngine(resolveWsUrl(cfg)) : PlaceholderEngine();
      await call.engine.start();
    } catch (e) {
      setStatus(e.message || String(e));
      stopCall();
    }
  }

  function stopCall() {
    if (!call.active && !call.stream && !call.engine) return;
    call.active = false;
    setListening(false);
    if (call.engine) { try { call.engine.stop(); } catch (e) {} call.engine = null; }
    // 只关我们自己开的流；chat.js 开的留给它管。
    if (call.stream) {
      call.stream.getTracks().forEach((t) => t.stop());
      call.stream = null;
      if (selfVideo) selfVideo.srcObject = null;
    }
    talkButton.textContent = "和小微对话";
    setShowDocEnabled(false);
    if (muteButton) {
      muteButton.disabled = true;
      muteButton.classList.remove("is-active");
    }
    if (startButton) startButton.classList.remove("is-off");
    if (selfVideo) selfVideo.style.opacity = "1";
  }

  // 微信式体验：打开通话即自动接通（开摄像头+麦克风+连小微）。
  // 监听弹窗的 hidden 变化，由 chat.js 的 openVideoCall() 触发。
  if (modal && "MutationObserver" in window) {
    let wasHidden = modal.hidden;
    new MutationObserver(() => {
      const hidden = modal.hidden;
      if (hidden === wasHidden) return;
      wasHidden = hidden;
      if (!hidden) {
        showCaption("");
        startCall();
      } else {
        stopCall();
      }
    }).observe(modal, { attributes: true, attributeFilter: ["hidden"] });
  }

  // talkButton 已隐藏，仍保留点击=开始/结束，作回落入口。
  talkButton.addEventListener("click", () => {
    if (call.active) stopCall();
    else startCall();
  });

  if (showDocButton) {
    showDocButton.addEventListener("click", () => {
      if (call.active && call.engine) call.engine.showDocument();
    });
  }

  // 接管"摄像头开关"和"静音"（覆盖 chat.js 的 onclick，避免重复开流/空操作）。
  if (startButton) startButton.onclick = toggleCamera;
  if (muteButton) muteButton.onclick = toggleMute;

  // 挂断：收尾对话并关闭整个通话界面。
  if (endButton) {
    endButton.addEventListener("click", () => {
      stopCall();
      if (closeButton) closeButton.click();
    });
  }
  // 关闭按钮/点遮罩：收尾对话（关闭弹窗由 chat.js 负责，observer 也会兜底 stop）。
  if (closeButton) closeButton.addEventListener("click", stopCall);
  if (backdrop) backdrop.addEventListener("click", stopCall);

  // 预热语音列表（部分浏览器首次为空）。
  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {};
    window.speechSynthesis.getVoices();
  }
})();

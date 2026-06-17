const EXPRESSIONS = ["neutral", "happy", "curious", "sleepy", "surprised", "sad", "thinking"];
const MOTIONS = ["idle", "nod", "shake", "look_left", "look_right", "look_up", "bounce", "sleep"];

const els = {
  healthStatus: document.querySelector("#healthStatus"),
  healthButton: document.querySelector("#healthButton"),
  apiBase: document.querySelector("#apiBase"),
  deviceId: document.querySelector("#deviceId"),
  deviceSecret: document.querySelector("#deviceSecret"),
  touchInput: document.querySelector("#touchInput"),
  wakeReason: document.querySelector("#wakeReason"),
  batteryInput: document.querySelector("#batteryInput"),
  batteryValue: document.querySelector("#batteryValue"),
  ambientInput: document.querySelector("#ambientInput"),
  ambientValue: document.querySelector("#ambientValue"),
  faceDetected: document.querySelector("#faceDetected"),
  speechEnabled: document.querySelector("#speechEnabled"),
  speechVoice: document.querySelector("#speechVoice"),
  speechRate: document.querySelector("#speechRate"),
  speechRateValue: document.querySelector("#speechRateValue"),
  batteryLabel: document.querySelector("#batteryLabel"),
  turnForm: document.querySelector("#turnForm"),
  userText: document.querySelector("#userText"),
  sendButton: document.querySelector("#sendButton"),
  device: document.querySelector("#device"),
  face: document.querySelector("#face"),
  expressionLabel: document.querySelector("#expressionLabel"),
  motionLabel: document.querySelector("#motionLabel"),
  durationLabel: document.querySelector("#durationLabel"),
  jsonOutput: document.querySelector("#jsonOutput"),
  copyJsonButton: document.querySelector("#copyJsonButton"),
  recalledList: document.querySelector("#recalledList"),
  savedList: document.querySelector("#savedList"),
  memoryQuery: document.querySelector("#memoryQuery"),
  memorySearchButton: document.querySelector("#memorySearchButton"),
  refreshMemoryButton: document.querySelector("#refreshMemoryButton"),
  memorySearchList: document.querySelector("#memorySearchList"),
  refreshLogsButton: document.querySelector("#refreshLogsButton"),
  logList: document.querySelector("#logList"),
};

const state = {
  latestJson: {},
  sessionLogs: [],
  serverEpisodes: [],
  motionTimer: null,
  audioPlayer: null,
};

function defaultApiBase() {
  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    return window.location.origin;
  }
  return "http://127.0.0.1:8787";
}

function normalizeApiBase() {
  return (els.apiBase.value || defaultApiBase()).trim().replace(/\/+$/, "");
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem("stackchanSimulatorSettings") || "{}");
    els.apiBase.value = saved.apiBase || defaultApiBase();
    els.deviceId.value = saved.deviceId || "web-simulator";
    els.deviceSecret.value = saved.deviceSecret || "";
    els.touchInput.value = saved.touch || "";
    els.wakeReason.value = saved.wakeReason || "keyboard";
    els.batteryInput.value = saved.battery ?? "88";
    els.ambientInput.value = saved.ambient ?? "56";
    els.faceDetected.checked = saved.faceDetected ?? true;
    els.speechEnabled.checked = saved.speechEnabled ?? true;
    els.speechVoice.dataset.selected = saved.speechVoice || "";
    els.speechRate.value = saved.speechRate ?? "1";
  } catch {
    els.apiBase.value = defaultApiBase();
  }
}

function saveSettings() {
  const settings = {
    apiBase: els.apiBase.value,
    deviceId: els.deviceId.value,
    deviceSecret: els.deviceSecret.value,
    touch: els.touchInput.value,
    wakeReason: els.wakeReason.value,
    battery: els.batteryInput.value,
    ambient: els.ambientInput.value,
    faceDetected: els.faceDetected.checked,
    speechEnabled: els.speechEnabled.checked,
    speechVoice: els.speechVoice.value,
    speechRate: els.speechRate.value,
  };
  localStorage.setItem("stackchanSimulatorSettings", JSON.stringify(settings));
}

function setHealth(text, status) {
  els.healthStatus.textContent = text;
  els.healthStatus.classList.toggle("ok", status === "ok");
  els.healthStatus.classList.toggle("error", status === "error");
}

function requestHeaders(includeJson = false) {
  const headers = {};
  const secret = els.deviceSecret.value.trim();
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }
  if (secret) {
    headers["X-Device-Secret"] = secret;
  }
  return headers;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${normalizeApiBase()}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  });
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null ? body.detail || JSON.stringify(body) : body;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return body;
}

function buildPayload(userText) {
  return {
    device_id: els.deviceId.value.trim() || "web-simulator",
    user_text: userText,
    local_time: new Date().toISOString(),
    context: {
      battery_percent: Number(els.batteryInput.value),
      touch: els.touchInput.value || null,
      face_detected: els.faceDetected.checked,
      ambient_light: Number(els.ambientInput.value),
      wake_reason: els.wakeReason.value || "keyboard",
      extra: {
        source: "web-simulator",
        page_url: window.location.href,
      },
    },
  };
}

function updateRangeLabels() {
  els.batteryValue.textContent = `${els.batteryInput.value}%`;
  els.batteryLabel.textContent = `${els.batteryInput.value}%`;
  els.ambientValue.textContent = els.ambientInput.value;
  els.speechRateValue.textContent = `${Number(els.speechRate.value).toFixed(1)}x`;
}

function updateFace(expression, motion, durationMs) {
  const safeExpression = EXPRESSIONS.includes(expression) ? expression : "neutral";
  const safeMotion = MOTIONS.includes(motion) ? motion : "idle";
  const safeDuration = Number.isFinite(Number(durationMs)) ? Number(durationMs) : 0;

  for (const item of EXPRESSIONS) {
    els.face.classList.remove(`expression-${item}`);
  }
  for (const item of MOTIONS) {
    els.device.classList.remove(`motion-${item}`);
  }

  els.face.classList.add(`expression-${safeExpression}`);
  els.device.classList.add(`motion-${safeMotion}`);
  els.expressionLabel.textContent = safeExpression;
  els.motionLabel.textContent = safeMotion;
  els.durationLabel.textContent = `${safeDuration} ms`;

  window.clearTimeout(state.motionTimer);
  if (safeMotion !== "idle" && safeDuration > 0) {
    state.motionTimer = window.setTimeout(() => {
      for (const item of MOTIONS) {
        els.device.classList.remove(`motion-${item}`);
      }
      els.device.classList.add("motion-idle");
      els.motionLabel.textContent = "idle";
    }, Math.min(safeDuration, 30000));
  }
}

function supportsSpeech() {
  return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

function speechVoices() {
  if (!supportsSpeech()) {
    return [];
  }
  return window.speechSynthesis.getVoices().slice().sort((left, right) => {
    const leftZh = left.lang.toLowerCase().startsWith("zh") ? 0 : 1;
    const rightZh = right.lang.toLowerCase().startsWith("zh") ? 0 : 1;
    return leftZh - rightZh || left.name.localeCompare(right.name);
  });
}

function renderSpeechVoices() {
  const selected = els.speechVoice.dataset.selected || els.speechVoice.value;
  const options = [new Option("默认", "")];
  for (const voice of speechVoices()) {
    options.push(new Option(`${voice.name} (${voice.lang})`, voice.voiceURI));
  }
  els.speechVoice.replaceChildren(...options);
  if (selected && options.some((option) => option.value === selected)) {
    els.speechVoice.value = selected;
  }
  syncSpeechControls();
}

function syncSpeechControls() {
  const supported = supportsSpeech();
  const enabled = supported && els.speechEnabled.checked;
  els.speechEnabled.disabled = !supported;
  els.speechVoice.disabled = !enabled;
  els.speechRate.disabled = !enabled;
}

function selectedSpeechVoice() {
  const selected = els.speechVoice.value;
  if (!selected) {
    return null;
  }
  return speechVoices().find((voice) => voice.voiceURI === selected) || null;
}

function resolveAudioUrl(audioUrl) {
  const value = (audioUrl || "").trim();
  if (!value) {
    return "";
  }
  try {
    return new URL(value, normalizeApiBase()).toString();
  } catch {
    return "";
  }
}

function clearSpeakingState() {
  els.device.classList.remove("is-speaking");
}

function stopAudioPlayback() {
  if (!state.audioPlayer) {
    return;
  }
  state.audioPlayer.pause();
  state.audioPlayer.removeAttribute("src");
  state.audioPlayer.load();
  state.audioPlayer = null;
}

async function playAudioResponse(audioUrl) {
  const url = resolveAudioUrl(audioUrl);
  if (!url || !els.speechEnabled.checked) {
    return false;
  }

  stopAudioPlayback();
  if (supportsSpeech()) {
    window.speechSynthesis.cancel();
  }

  const audio = new Audio(url);
  audio.playbackRate = Number(els.speechRate.value) || 1;
  audio.onplay = () => {
    els.device.classList.add("is-speaking");
  };
  audio.onended = () => {
    clearSpeakingState();
  };
  audio.onerror = () => {
    clearSpeakingState();
    addSessionLog("voice", "音频播放失败", url);
  };
  state.audioPlayer = audio;

  try {
    await audio.play();
    return true;
  } catch (error) {
    clearSpeakingState();
    addSessionLog("voice", "音频播放被浏览器拦截", error.message || "");
    return false;
  }
}

function speakResponse(text) {
  const line = (text || "").trim();
  if (!line || !els.speechEnabled.checked) {
    return;
  }
  if (!supportsSpeech()) {
    addSessionLog("voice", "浏览器不支持语音输出");
    return;
  }

  const utterance = new SpeechSynthesisUtterance(line);
  const voice = selectedSpeechVoice();
  if (voice) {
    utterance.voice = voice;
    utterance.lang = voice.lang || "zh-CN";
  } else {
    utterance.lang = "zh-CN";
  }
  utterance.rate = Number(els.speechRate.value) || 1;
  utterance.pitch = 1;
  utterance.onstart = () => {
    els.device.classList.add("is-speaking");
  };
  utterance.onend = () => {
    els.device.classList.remove("is-speaking");
  };
  utterance.onerror = (event) => {
    clearSpeakingState();
    addSessionLog("voice", "语音输出失败", event.error || "");
  };

  stopAudioPlayback();
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function updateJson(json) {
  state.latestJson = json || {};
  els.jsonOutput.textContent = JSON.stringify(state.latestJson, null, 2);
}

function memoryItemNode(item) {
  const li = document.createElement("li");

  const meta = document.createElement("div");
  meta.className = "memory-key";
  const key = document.createElement("span");
  key.textContent = item.key || "memory";
  const importance = document.createElement("span");
  importance.textContent = `重要度 ${item.importance ?? "-"}`;
  meta.append(key, importance);

  const value = document.createElement("p");
  value.className = "memory-value";
  value.textContent = item.value || "";

  li.append(meta, value);

  if (Array.isArray(item.tags) && item.tags.length) {
    const tags = document.createElement("div");
    tags.className = "tag-row";
    for (const tag of item.tags) {
      const tagEl = document.createElement("span");
      tagEl.className = "tag";
      tagEl.textContent = tag;
      tags.appendChild(tagEl);
    }
    li.appendChild(tags);
  }

  return li;
}

function renderMemoryList(listEl, items, emptyText) {
  listEl.classList.toggle("empty-list", !items.length);
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = emptyText;
    listEl.replaceChildren(li);
    return;
  }
  listEl.replaceChildren(...items.map(memoryItemNode));
}

function addSessionLog(type, text, detail = "") {
  state.sessionLogs.unshift({
    type,
    text,
    detail,
    time: new Date(),
  });
  state.sessionLogs = state.sessionLogs.slice(0, 8);
  renderLogs();
}

function episodeNode(episode) {
  const li = document.createElement("li");
  const meta = document.createElement("div");
  meta.className = "log-meta";
  const time = document.createElement("span");
  time.textContent = formatDate(episode.created_at);
  const action = document.createElement("span");
  action.textContent = `${episode.expression || "neutral"} / ${episode.motion || "idle"}`;
  meta.append(time, action);

  const userLine = document.createElement("p");
  userLine.className = "log-text user-line";
  userLine.textContent = `你：${episode.user_text || ""}`;

  const assistantLine = document.createElement("p");
  assistantLine.className = "log-text assistant-line";
  assistantLine.textContent = `小栈：${episode.assistant_text || ""}`;

  li.append(meta, userLine, assistantLine);
  return li;
}

function sessionLogNode(log) {
  const li = document.createElement("li");
  const meta = document.createElement("div");
  meta.className = "log-meta";
  const time = document.createElement("span");
  time.textContent = formatDate(log.time);
  const type = document.createElement("span");
  type.textContent = log.type;
  meta.append(time, type);

  const text = document.createElement("p");
  text.className = "log-text";
  text.textContent = log.detail ? `${log.text}：${log.detail}` : log.text;
  li.append(meta, text);
  return li;
}

function renderLogs() {
  const nodes = [
    ...state.sessionLogs.map(sessionLogNode),
    ...state.serverEpisodes.map(episodeNode),
  ].slice(0, 16);

  els.logList.classList.toggle("empty-list", !nodes.length);
  if (!nodes.length) {
    const li = document.createElement("li");
    li.textContent = "暂无日志";
    els.logList.replaceChildren(li);
    return;
  }
  els.logList.replaceChildren(...nodes);
}

function formatDate(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

async function checkHealth() {
  try {
    const health = await apiFetch("/health");
    setHealth(health.llm_configured ? "LLM 已连接" : "Fallback", "ok");
    addSessionLog("health", "Brain 服务可用", health.pet_name || "");
    return health;
  } catch (error) {
    setHealth("连接失败", "error");
    addSessionLog("error", "Brain 连接失败", error.message);
    throw error;
  }
}

async function submitTurn(event) {
  event.preventDefault();
  const userText = els.userText.value.trim();
  if (!userText) {
    els.userText.focus();
    return;
  }

  saveSettings();
  const payload = buildPayload(userText);
  els.sendButton.disabled = true;
  els.sendButton.textContent = "发送中";
  addSessionLog("request", "发送 turn", userText);

  try {
    const response = await apiFetch("/api/v1/turn", {
      method: "POST",
      headers: requestHeaders(true),
      body: JSON.stringify(payload),
    });
    updateJson(response);
    updateFace(response.expression, response.motion, response.duration_ms);
    renderMemoryList(els.recalledList, response.recalled_memories || [], "暂无召回");
    renderMemoryList(els.savedList, response.saved_memories || [], "暂无保存");
    addSessionLog("response", response.say || "收到响应", response.thought || "");
    const playedAudio = await playAudioResponse(response.audio_url || "");
    if (!playedAudio) {
      speakResponse(response.say || "");
    }
    els.userText.value = "";
    setHealth("已连接", "ok");
    await Promise.allSettled([refreshLogs(), refreshMemories(userText)]);
  } catch (error) {
    setHealth("请求失败", "error");
    updateJson({ error: error.message, request: payload });
    addSessionLog("error", "turn 请求失败", error.message);
  } finally {
    els.sendButton.disabled = false;
    els.sendButton.textContent = "发送";
  }
}

async function refreshMemories(queryOverride) {
  const query = typeof queryOverride === "string" ? queryOverride : els.memoryQuery.value.trim();
  const params = new URLSearchParams({ q: query, limit: "12" });
  try {
    const memories = await apiFetch(`/api/v1/memories/search?${params.toString()}`);
    renderMemoryList(els.memorySearchList, memories, "暂无结果");
  } catch (error) {
    renderMemoryList(els.memorySearchList, [], "记忆读取失败");
    addSessionLog("error", "记忆读取失败", error.message);
  }
}

async function refreshLogs() {
  try {
    state.serverEpisodes = await apiFetch("/api/v1/episodes?limit=8");
    renderLogs();
  } catch (error) {
    addSessionLog("error", "日志读取失败", error.message);
  }
}

async function copyJson() {
  const text = JSON.stringify(state.latestJson, null, 2);
  try {
    await navigator.clipboard.writeText(text);
    addSessionLog("copy", "JSON 已复制");
  } catch {
    addSessionLog("copy", "浏览器未开放剪贴板");
  }
}

function bindEvents() {
  els.turnForm.addEventListener("submit", submitTurn);
  els.healthButton.addEventListener("click", () => {
    checkHealth().catch(() => {});
  });
  els.refreshMemoryButton.addEventListener("click", () => {
    refreshMemories("").catch(() => {});
  });
  els.memorySearchButton.addEventListener("click", () => {
    refreshMemories().catch(() => {});
  });
  els.refreshLogsButton.addEventListener("click", () => {
    refreshLogs().catch(() => {});
  });
  els.copyJsonButton.addEventListener("click", copyJson);

  for (const input of [
    els.apiBase,
    els.deviceId,
    els.deviceSecret,
    els.touchInput,
    els.wakeReason,
    els.faceDetected,
    els.speechEnabled,
    els.speechVoice,
  ]) {
    input.addEventListener("change", () => {
      if (input === els.speechVoice) {
        els.speechVoice.dataset.selected = els.speechVoice.value;
      }
      if (input === els.speechEnabled) {
        syncSpeechControls();
      }
      saveSettings();
    });
  }

  for (const input of [els.batteryInput, els.ambientInput, els.speechRate]) {
    input.addEventListener("input", () => {
      updateRangeLabels();
      saveSettings();
    });
  }

  els.userText.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      els.turnForm.requestSubmit();
    }
  });
}

function init() {
  loadSettings();
  updateRangeLabels();
  renderSpeechVoices();
  if (supportsSpeech()) {
    window.speechSynthesis.onvoiceschanged = renderSpeechVoices;
  }
  updateFace("neutral", "idle", 0);
  updateJson({});
  bindEvents();
  checkHealth()
    .catch(() => {})
    .finally(() => {
      refreshLogs().catch(() => {});
      refreshMemories("").catch(() => {});
    });
}

init();

const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const conversation = document.getElementById("conversation");
const commandInput = document.getElementById("command-input");
const sendButton = document.getElementById("send-button");
const confirmButton = document.getElementById("confirm-button");
const micButton = document.getElementById("mic-button");
const voiceToggle = document.getElementById("voice-toggle");
const personaButtons = Array.from(document.querySelectorAll(".persona-button"));
const onboardingRestart = document.getElementById("onboarding-restart");
const providerCalendar = document.getElementById("provider-calendar");
const providerEmail = document.getElementById("provider-email");
const calendarClientIdInput = document.getElementById("calendar-client-id");
const calendarClientSecretInput = document.getElementById("calendar-client-secret");
const calendarCodeInput = document.getElementById("calendar-auth-code");
const calendarConnectStartButton = document.getElementById("calendar-connect-start");
const calendarConnectFinishButton = document.getElementById("calendar-connect-finish");
const calendarTestButton = document.getElementById("calendar-test");
const calendarAuthLink = document.getElementById("calendar-auth-link");
const calendarSetupNote = document.getElementById("calendar-setup-note");
const emailClientIdInput = document.getElementById("email-client-id");
const emailClientSecretInput = document.getElementById("email-client-secret");
const emailCodeInput = document.getElementById("email-auth-code");
const emailConnectStartButton = document.getElementById("email-connect-start");
const emailConnectFinishButton = document.getElementById("email-connect-finish");
const emailTestButton = document.getElementById("email-test");
const emailAuthLink = document.getElementById("email-auth-link");
const emailSetupNote = document.getElementById("email-setup-note");
const appTasksList = document.getElementById("app-tasks-list");
const onboarding = document.getElementById("onboarding");
const onboardingTitle = document.getElementById("onboarding-title");
const onboardingStepLabel = document.getElementById("onboarding-step-label");
const onboardingProgressBar = document.getElementById("onboarding-progress-bar");
const onboardingBody = document.getElementById("onboarding-body");
const onboardingBack = document.getElementById("onboarding-back");
const onboardingNext = document.getElementById("onboarding-next");
const onboardingSkip = document.getElementById("onboarding-skip");

const apiBase = window.location.origin;
let recognition = null;
let voiceEnabled = false;
let pendingConfirmation = null;
let fillerTimer = null;
let fillerInterval = null;
let fillerIndex = 0;

let personaPresets = {};
let activePersona = "max";
let onboardingStep = 0;
let onboardingCompleted = false;
let onboardingStartedAt = null;
let providers = {
  calendar: "local",
  email: "gmail",
  weather: "default",
};
let appTasks = [];
const oauthPollTimers = {};

let fillerPhrases = [
  "Working on it.",
  "Still on it.",
  "Almost there.",
  "Thanks for waiting.",
  "Making progress.",
];
let progressPhrases = [];

const applyPersona = (persona) => {
  if (!persona) return;
  if (Array.isArray(persona.filler_phrases) && persona.filler_phrases.length > 0) {
    fillerPhrases = persona.filler_phrases;
  }
};

const setVoiceEnabled = (enabled) => {
  voiceEnabled = Boolean(enabled);
  voiceToggle.dataset.state = voiceEnabled ? "on" : "off";
  voiceToggle.textContent = voiceEnabled ? "On" : "Off";
};

const setActivePersona = (key) => {
  activePersona = key;
  localStorage.setItem("ai_distro_persona", key);
  personaButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.persona === key);
  });
  if (personaPresets[key]) {
    applyPersona(personaPresets[key]);
  }
};

const persistPersona = async (key) => {
  try {
    const res = await fetch(`${apiBase}/api/persona/set`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: key }),
    });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      addMessage("assistant", payload.message || "Couldn't save persona system-wide.");
      return false;
    }
    return true;
  } catch (err) {
    addMessage("assistant", "Couldn't save persona system-wide.");
    return false;
  }
};

const refreshPersona = async () => {
  try {
    const res = await fetch(`${apiBase}/api/persona`);
    if (!res.ok) return;
    const payload = await res.json();
    applyPersona(payload.persona);
  } catch (err) {
    // ignore
  }
};

const applyProvidersUI = () => {
  if (providerCalendar) providerCalendar.value = providers.calendar || "local";
  if (providerEmail) providerEmail.value = providers.email || "gmail";
  refreshProviderSetupUI();
};

const providerNeedsOAuth = (target, provider) => {
  if (target === "calendar") return ["google", "microsoft"].includes(provider);
  if (target === "email") return ["gmail", "outlook"].includes(provider);
  return false;
};

const setSetupNote = (target, text) => {
  const node = target === "calendar" ? calendarSetupNote : emailSetupNote;
  if (node) node.textContent = text || "";
};

const getProviderPayload = (target) => {
  if (target === "calendar") {
    return {
      target,
      provider: providers.calendar,
      client_id: calendarClientIdInput?.value?.trim() || "",
      client_secret: calendarClientSecretInput?.value?.trim() || "",
      code: calendarCodeInput?.value?.trim() || "",
    };
  }
  return {
    target,
    provider: providers.email,
    client_id: emailClientIdInput?.value?.trim() || "",
    client_secret: emailClientSecretInput?.value?.trim() || "",
    code: emailCodeInput?.value?.trim() || "",
  };
};

const setAuthLink = (target, url) => {
  const link = target === "calendar" ? calendarAuthLink : emailAuthLink;
  if (!link) return;
  if (url) {
    link.href = url;
    link.classList.remove("hidden");
  } else {
    link.href = "#";
    link.classList.add("hidden");
  }
};

const refreshProviderSetupUI = () => {
  const calendarNeedsOauth = providerNeedsOAuth("calendar", providers.calendar);
  if (calendarClientIdInput) calendarClientIdInput.classList.toggle("hidden", !calendarNeedsOauth);
  if (calendarClientSecretInput) calendarClientSecretInput.classList.toggle("hidden", !calendarNeedsOauth);
  if (calendarCodeInput) calendarCodeInput.classList.add("hidden");
  if (calendarConnectFinishButton) calendarConnectFinishButton.classList.add("hidden");
  if (!calendarNeedsOauth) setAuthLink("calendar", "");
  if (!calendarNeedsOauth) setSetupNote("calendar", "No account connection needed for local calendar.");
  if (calendarNeedsOauth) setSetupNote("calendar", "Click Connect and approve access in your browser. Setup will finish automatically.");

  const emailNeedsOauth = providerNeedsOAuth("email", providers.email);
  if (emailClientIdInput) emailClientIdInput.classList.toggle("hidden", !emailNeedsOauth);
  if (emailClientSecretInput) emailClientSecretInput.classList.toggle("hidden", !emailNeedsOauth);
  if (emailCodeInput) emailCodeInput.classList.add("hidden");
  if (emailConnectFinishButton) emailConnectFinishButton.classList.add("hidden");
  if (!emailNeedsOauth) setAuthLink("email", "");
  if (!emailNeedsOauth) setSetupNote("email", "No OAuth needed for IMAP. Use provider credentials in settings.");
  if (emailNeedsOauth) setSetupNote("email", "Click Connect and approve access in your browser. Setup will finish automatically.");
};

const stopProviderStatusPoll = (target) => {
  if (oauthPollTimers[target]) {
    clearInterval(oauthPollTimers[target]);
    delete oauthPollTimers[target];
  }
};

const pollProviderConnectStatus = async (target) => {
  try {
    const res = await fetch(`${apiBase}/api/provider/connect/status?target=${encodeURIComponent(target)}`);
    if (!res.ok) return;
    const out = await res.json();
    if (!out || !out.status) return;
    if (out.status === "idle") return;
    if (out.auth_url) setAuthLink(target, out.auth_url);
    if (out.status === "pending") {
      setSetupNote(target, out.message || "Waiting for authorization approval...");
      return;
    }
    if (out.status === "connected") {
      setSetupNote(target, out.message || "Provider connected.");
      addMessage("assistant", `${target === "calendar" ? "Calendar" : "Email"} provider connected.`);
      stopProviderStatusPoll(target);
      return;
    }
    if (out.status === "error") {
      setSetupNote(target, out.message || "Provider connection failed.");
      stopProviderStatusPoll(target);
    }
  } catch (err) {
    // ignore
  }
};

const startProviderConnect = async (target) => {
  const payload = getProviderPayload(target);
  setSetupNote(target, "Preparing authorization link...");
  stopProviderStatusPoll(target);
  try {
    const res = await fetch(`${apiBase}/api/provider/connect/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok || out.status === "error") {
      setSetupNote(target, out.message || "Couldn't start provider connection.");
      return;
    }
    if (out.auth_url) {
      setAuthLink(target, out.auth_url);
      window.open(out.auth_url, "_blank", "noopener");
    } else {
      setAuthLink(target, "");
    }
    setSetupNote(target, "Authorization started. Approve access in your browser.");
    addMessage("assistant", `${target === "calendar" ? "Calendar" : "Email"} connection started. I’ll finish setup when approval completes.`);
    oauthPollTimers[target] = setInterval(() => pollProviderConnectStatus(target), 1500);
    pollProviderConnectStatus(target);
  } catch (err) {
    setSetupNote(target, "Couldn't start provider connection.");
  }
};

const finishProviderConnect = async (target) => {
  const payload = getProviderPayload(target);
  setSetupNote(target, "Finishing connection...");
  try {
    const res = await fetch(`${apiBase}/api/provider/connect/finish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok || out.status === "error") {
      setSetupNote(target, out.message || "Couldn't finish provider connection.");
      return;
    }
    setSetupNote(target, out.message || "Provider connected.");
    addMessage("assistant", `${target === "calendar" ? "Calendar" : "Email"} provider connected.`);
  } catch (err) {
    setSetupNote(target, "Couldn't finish provider connection.");
  }
};

const testProviderConnection = async (target) => {
  const payload = getProviderPayload(target);
  setSetupNote(target, "Testing provider...");
  try {
    const res = await fetch(`${apiBase}/api/provider/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok || out.status === "error") {
      setSetupNote(target, out.message || "Provider test failed.");
      return;
    }
    setSetupNote(target, "Connection test passed.");
    addMessage("assistant", out.message || "Provider test passed.");
  } catch (err) {
    setSetupNote(target, "Provider test failed.");
  }
};

const persistProviders = async () => {
  try {
    const res = await fetch(`${apiBase}/api/providers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ providers }),
    });
    if (!res.ok) {
      addMessage("assistant", "Couldn't save provider settings.");
      return false;
    }
    return true;
  } catch (err) {
    addMessage("assistant", "Couldn't save provider settings.");
    return false;
  }
};

const loadProviders = async () => {
  try {
    const res = await fetch(`${apiBase}/api/providers`);
    if (!res.ok) return;
    const payload = await res.json();
    if (payload.providers) {
      providers = {
        ...providers,
        ...payload.providers,
      };
      applyProvidersUI();
    }
  } catch (err) {
    // ignore
  }
};

const addMessage = (role, text) => {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.innerHTML = `
    <div class="avatar">◉</div>
    <div class="bubble">
      <div class="name">${role === "user" ? "You" : "Assistant"}</div>
      <p>${text}</p>
    </div>
  `;
  conversation.appendChild(message);
  conversation.scrollTop = conversation.scrollHeight;
};

const setOnboardingFeedback = (text) => {
  const feedback = onboardingBody.querySelector("#onboarding-feedback");
  if (feedback) {
    feedback.textContent = text || "";
  }
};

const speak = (text) => {
  if (!voiceEnabled || !window.speechSynthesis) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.0;
  utter.pitch = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
};

const summarizeRequest = (text) => {
  const cleaned = (text || "").trim().replace(/\s+/g, " ");
  if (!cleaned) return "that";
  if (cleaned.length <= 64) return cleaned.toLowerCase();
  return `${cleaned.slice(0, 61).toLowerCase()}...`;
};

const conversationalAck = (text) => {
  const summary = summarizeRequest(text);
  if (summary === "that") {
    return "I heard you. I’m on it.";
  }
  return `I heard you ask to ${summary}. I’m on it now.`;
};

const buildProgressPhrases = (text) => {
  const summary = summarizeRequest(text);
  if (summary === "that") {
    return [...fillerPhrases];
  }
  return [
    `I’m working on ${summary}.`,
    `Still working on ${summary}.`,
    `Almost done with ${summary}.`,
    ...fillerPhrases,
  ];
};

const setStatus = (online, text) => {
  statusDot.classList.toggle("online", online);
  statusText.textContent = text;
};

const formatTaskTime = (ts) => {
  if (typeof ts !== "number") return "";
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const taskActionLabel = (action) => {
  if (action === "package_install") return "Install app";
  if (action === "package_remove") return "Remove app";
  if (action === "system_update") return "Update apps";
  return "Task";
};

const renderAppTasks = () => {
  if (!appTasksList) return;
  if (!Array.isArray(appTasks) || appTasks.length === 0) {
    appTasksList.innerHTML = `<div class="app-task-empty">No recent app tasks yet.</div>`;
    return;
  }
  const rows = appTasks
    .slice(0, 8)
    .map((t) => {
      const status = (t.status || "unknown").toLowerCase();
      const statusClass = ["ok", "error", "confirm"].includes(status) ? status : "error";
      const msg = (t.message || "Task update available.").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      const action = taskActionLabel(t.action || "");
      const time = formatTaskTime(t.ts);
      return `
        <div class="app-task-item">
          <div class="app-task-head">
            <span class="app-task-action">${action}</span>
            <span class="app-task-status ${statusClass}">${status}</span>
          </div>
          <div class="app-task-message">${msg}</div>
          <div class="app-task-time">${time}</div>
        </div>
      `;
    })
    .join("");
  appTasksList.innerHTML = rows;
};

const loadAppTasks = async () => {
  try {
    const res = await fetch(`${apiBase}/api/app-tasks`);
    if (!res.ok) return;
    const payload = await res.json();
    if (!Array.isArray(payload.tasks)) return;
    appTasks = payload.tasks;
    renderAppTasks();
  } catch (err) {
    // ignore
  }
};

const stopFiller = () => {
  if (fillerTimer) {
    clearTimeout(fillerTimer);
    fillerTimer = null;
  }
  if (fillerInterval) {
    clearInterval(fillerInterval);
    fillerInterval = null;
  }
  fillerIndex = 0;
};

const startFiller = () => {
  stopFiller();
  const lines = progressPhrases.length ? progressPhrases : fillerPhrases;
  // Wait a moment before speaking to avoid noise on fast responses.
  fillerTimer = setTimeout(() => {
    addMessage("assistant", lines[fillerIndex % lines.length]);
    speak(lines[fillerIndex % lines.length]);
    fillerIndex += 1;
    fillerInterval = setInterval(() => {
      addMessage("assistant", lines[fillerIndex % lines.length]);
      speak(lines[fillerIndex % lines.length]);
      fillerIndex += 1;
    }, 9000);
  }, 2000);
};

const onboardingSteps = [
  {
    title: "Welcome to AI Distro",
    stepLabel: "Step 1 of 5",
    nextLabel: "Next",
    body: `
      <h2>Talk naturally. I handle the rest.</h2>
      <p>This shell is your command center for voice and manual control. We’ll set voice preferences and run your first command.</p>
    `,
  },
  {
    title: "Voice Playback",
    stepLabel: "Step 2 of 5",
    nextLabel: "Next",
    body: `
      <h2>Choose spoken replies</h2>
      <p>Enable voice replies if you want the assistant to speak status and results aloud.</p>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-voice-toggle>Toggle Voice Replies</button>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      const toggle = onboardingBody.querySelector("[data-ob-voice-toggle]");
      if (!toggle) return;
      toggle.addEventListener("click", () => {
        setVoiceEnabled(!voiceEnabled);
        setOnboardingFeedback(`Voice replies are ${voiceEnabled ? "on" : "off"}.`);
      });
      setOnboardingFeedback(`Voice replies are currently ${voiceEnabled ? "on" : "off"}.`);
    },
  },
  {
    title: "Assistant Persona",
    stepLabel: "Step 3 of 5",
    nextLabel: "Next",
    body: `
      <h2>Pick your tone</h2>
      <p>Choose how the assistant sounds. You can change this any time from the side panel.</p>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-persona="max">Use Max</button>
        <button class="ghost" type="button" data-ob-persona="alfred">Use Alfred</button>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      const personaChoiceButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-persona]"));
      personaChoiceButtons.forEach((btn) => {
        btn.addEventListener("click", async () => {
          const key = btn.dataset.obPersona;
          if (!key) return;
          setActivePersona(key);
          const ok = await persistPersona(key);
          if (ok) {
            setOnboardingFeedback(`Persona set to ${key}.`);
            refreshPersona();
          } else {
            setOnboardingFeedback("Persona was updated locally only.");
          }
        });
      });
      setOnboardingFeedback(`Current persona: ${activePersona}.`);
    },
  },
  {
    title: "Safety Checks",
    stepLabel: "Step 4 of 5",
    nextLabel: "Next",
    body: `
      <h2>Risky actions always require confirmation</h2>
      <p>Before any dangerous action, the assistant pauses and asks for explicit confirmation. You stay in control.</p>
      <div class="onboarding-note">Example: reboot, shutdown, and package changes may ask to confirm first.</div>
    `,
  },
  {
    title: "Run a First Command",
    stepLabel: "Step 5 of 5",
    nextLabel: "Finish",
    body: `
      <h2>Try one now</h2>
      <p>Pick a sample command or type your own in the input field at the bottom.</p>
      <div class="onboarding-buttons">
        <button class="ghost" type="button" data-ob-command="what can you do">What can you do</button>
        <button class="ghost" type="button" data-ob-command="open firefox">Open Firefox</button>
        <button class="ghost" type="button" data-ob-command="set volume to 40 percent">Set volume to 40%</button>
      </div>
      <div id="onboarding-feedback" class="onboarding-note"></div>
    `,
    onRender: () => {
      const sampleButtons = Array.from(onboardingBody.querySelectorAll("[data-ob-command]"));
      sampleButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const command = btn.dataset.obCommand;
          if (!command) return;
          sendCommand(command);
          setOnboardingFeedback(`Sent: "${command}"`);
        });
      });
      setOnboardingFeedback("When you are ready, click Finish.");
    },
  },
];

const renderOnboardingStep = () => {
  const step = onboardingSteps[onboardingStep];
  if (!step) return;
  onboardingTitle.textContent = step.title;
  onboardingStepLabel.textContent = step.stepLabel;
  onboardingProgressBar.style.width = `${((onboardingStep + 1) / onboardingSteps.length) * 100}%`;
  onboardingBody.innerHTML = step.body;
  onboardingBack.classList.toggle("hidden", onboardingStep === 0);
  onboardingNext.textContent = step.nextLabel;
  if (typeof step.onRender === "function") {
    step.onRender();
  }
};

const fetchOnboardingState = async () => {
  try {
    const res = await fetch(`${apiBase}/api/onboarding`);
    if (!res.ok) return {};
    const payload = await res.json();
    return payload.state || {};
  } catch (err) {
    return {};
  }
};

const persistOnboardingState = async (state) => {
  try {
    await fetch(`${apiBase}/api/onboarding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state }),
    });
  } catch (err) {
    // ignore
  }
};

const persistOnboardingProgress = async () => {
  if (!onboardingStartedAt) {
    onboardingStartedAt = new Date().toISOString();
  }
  await persistOnboardingState({
    version: 1,
    completed: false,
    started_at: onboardingStartedAt,
    last_step: onboardingStep,
    voice_enabled: voiceEnabled,
    persona: activePersona,
  });
};

const openOnboarding = async (startStep = 0, persist = true) => {
  onboardingCompleted = false;
  onboarding.classList.remove("hidden");
  onboardingStep = Math.max(0, Math.min(startStep, onboardingSteps.length - 1));
  renderOnboardingStep();
  if (persist) {
    await persistOnboardingProgress();
  }
};

const completeOnboarding = async (skipped) => {
  onboardingCompleted = true;
  const state = {
    version: 1,
    completed: true,
    skipped: Boolean(skipped),
    started_at: onboardingStartedAt,
    last_step: onboardingStep,
    voice_enabled: voiceEnabled,
    persona: activePersona,
    completed_at: new Date().toISOString(),
  };
  localStorage.setItem("ai_distro_onboarding_v1_completed", "true");
  localStorage.setItem("ai_distro_onboarding_v1_completed_at", state.completed_at);
  await persistOnboardingState(state);
  onboarding.classList.add("hidden");
  addMessage("assistant", skipped ? "Onboarding skipped. Say the word when you want help." : "Onboarding complete. You are ready.");
};

const maybeStartOnboarding = async () => {
  const state = await fetchOnboardingState();
  onboardingStartedAt = state.started_at || null;
  const completedLocal = localStorage.getItem("ai_distro_onboarding_v1_completed") === "true";
  const completedRemote = Boolean(state.completed);
  onboardingCompleted = completedLocal || completedRemote;
  if (onboardingCompleted) {
    onboarding.classList.add("hidden");
    return;
  }
  const resumeStep = Number.isInteger(state.last_step) ? state.last_step : 0;
  await openOnboarding(resumeStep, false);
};

const sendCommand = async (text) => {
  if (!text) return;
  addMessage("user", text);
  const ack = conversationalAck(text);
  addMessage("assistant", ack);
  speak(ack);
  commandInput.value = "";
  progressPhrases = buildProgressPhrases(text);
  setStatus(true, "Thinking...");
  startFiller();
  try {
    const res = await fetch(`${apiBase}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const payload = await res.json();
    loadAppTasks();
    stopFiller();
    if (payload.status === "confirm") {
      pendingConfirmation = payload.confirmation_id || null;
      confirmButton.classList.toggle("hidden", !pendingConfirmation);
      addMessage("assistant", payload.message || "Confirmation required. Say confirm or tap confirm.");
      speak(payload.message || "Confirmation required.");
      setStatus(true, "Awaiting confirmation");
      return;
    }
    if (payload.status === "deny") {
      addMessage("assistant", payload.message || "I can't do that.");
      speak(payload.message || "I can't do that.");
      setStatus(true, "Ready");
      return;
    }
    if (payload.status === "error") {
      addMessage("assistant", payload.message || "Something went wrong.");
      speak(payload.message || "Something went wrong.");
      setStatus(false, "Agent error");
      return;
    }
    const message = payload.message || "Done.";
    addMessage("assistant", message);
    speak(message);
    setStatus(true, "Ready");
  } catch (err) {
    stopFiller();
    addMessage("assistant", "I couldn't reach the agent service.");
    setStatus(false, "Offline");
  }
};

const sendConfirm = async () => {
  if (!pendingConfirmation) return;
  setStatus(true, "Confirming...");
  startFiller();
  try {
    const res = await fetch(`${apiBase}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "confirm", payload: pendingConfirmation }),
    });
    const payload = await res.json();
    loadAppTasks();
    stopFiller();
    pendingConfirmation = null;
    confirmButton.classList.add("hidden");
    const message = payload.message || "Confirmed.";
    addMessage("assistant", message);
    speak(message);
    setStatus(true, "Ready");
  } catch (err) {
    stopFiller();
    addMessage("assistant", "Confirmation failed.");
    setStatus(false, "Offline");
  }
};

const initVoice = () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micButton.disabled = true;
    micButton.textContent = "Voice unavailable";
    return;
  }
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.addEventListener("result", (event) => {
    const transcript = event.results[0][0].transcript;
    sendCommand(transcript);
  });

  recognition.addEventListener("end", () => {
    micButton.classList.remove("active");
  });
};

micButton.addEventListener("mousedown", () => {
  if (!recognition) return;
  micButton.classList.add("active");
  recognition.start();
});

micButton.addEventListener("mouseup", () => {
  if (!recognition) return;
  recognition.stop();
});

sendButton.addEventListener("click", () => sendCommand(commandInput.value.trim()));
confirmButton.addEventListener("click", () => sendConfirm());
commandInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    const value = commandInput.value.trim();
    if (pendingConfirmation && ["confirm", "yes"].includes(value.toLowerCase())) {
      commandInput.value = "";
      sendConfirm();
      return;
    }
    if (pendingConfirmation && ["cancel", "no"].includes(value.toLowerCase())) {
      pendingConfirmation = null;
      confirmButton.classList.add("hidden");
      addMessage("assistant", "Cancelled.");
      commandInput.value = "";
      return;
    }
    sendCommand(value);
  }
});

voiceToggle.addEventListener("click", () => {
  setVoiceEnabled(!voiceEnabled);
});

onboardingBack.addEventListener("click", () => {
  if (onboardingStep === 0) return;
  onboardingStep -= 1;
  renderOnboardingStep();
  persistOnboardingProgress();
});

onboardingNext.addEventListener("click", async () => {
  if (onboardingStep < onboardingSteps.length - 1) {
    onboardingStep += 1;
    renderOnboardingStep();
    await persistOnboardingProgress();
    return;
  }
  await completeOnboarding(false);
});

onboardingSkip.addEventListener("click", async () => {
  await completeOnboarding(true);
});

onboardingRestart.addEventListener("click", async () => {
  localStorage.removeItem("ai_distro_onboarding_v1_completed");
  localStorage.removeItem("ai_distro_onboarding_v1_completed_at");
  onboardingStartedAt = new Date().toISOString();
  await openOnboarding(0, true);
  addMessage("assistant", "Onboarding restarted.");
});

if (providerCalendar) {
  providerCalendar.addEventListener("change", async () => {
    providers.calendar = providerCalendar.value;
    const ok = await persistProviders();
    if (ok) {
      addMessage("assistant", `Calendar provider set to ${providers.calendar}.`);
    }
    refreshProviderSetupUI();
  });
}

if (providerEmail) {
  providerEmail.addEventListener("change", async () => {
    providers.email = providerEmail.value;
    const ok = await persistProviders();
    if (ok) {
      addMessage("assistant", `Email provider set to ${providers.email}.`);
    }
    refreshProviderSetupUI();
  });
}

if (calendarConnectStartButton) {
  calendarConnectStartButton.addEventListener("click", () => startProviderConnect("calendar"));
}
if (calendarConnectFinishButton) {
  calendarConnectFinishButton.addEventListener("click", () => finishProviderConnect("calendar"));
}
if (calendarTestButton) {
  calendarTestButton.addEventListener("click", () => testProviderConnection("calendar"));
}
if (emailConnectStartButton) {
  emailConnectStartButton.addEventListener("click", () => startProviderConnect("email"));
}
if (emailConnectFinishButton) {
  emailConnectFinishButton.addEventListener("click", () => finishProviderConnect("email"));
}
if (emailTestButton) {
  emailTestButton.addEventListener("click", () => testProviderConnection("email"));
}

const ping = async () => {
  try {
    const res = await fetch(`${apiBase}/api/health`);
    if (res.ok) {
      const payload = await res.json();
      applyPersona(payload.persona);
      setStatus(true, "Ready");
      return;
    }
  } catch (err) {
    // ignore
  }
  setStatus(false, "Offline");
};

initVoice();
ping();
setInterval(ping, 5000);
setInterval(loadAppTasks, 7000);

const loadPersonaPresets = async () => {
  try {
    const res = await fetch(`${apiBase}/api/persona-presets`);
    if (!res.ok) return;
    const payload = await res.json();
    personaPresets = payload.presets || {};
  } catch (err) {
    // ignore
  }
  const saved = localStorage.getItem("ai_distro_persona");
  const defaultKey = saved || "max";
  setActivePersona(defaultKey);
};

personaButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const key = btn.dataset.persona;
    setActivePersona(key);
    persistPersona(key).then((ok) => {
      if (ok) {
        addMessage("assistant", "All set. I’ll sound like this everywhere now.");
        refreshPersona();
      }
    });
  });
});

loadPersonaPresets();
maybeStartOnboarding();
refreshProviderSetupUI();
loadProviders();
loadAppTasks();

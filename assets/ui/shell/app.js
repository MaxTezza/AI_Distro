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

let fillerPhrases = [
  "Working on it.",
  "Still on it.",
  "Almost there.",
  "Thanks for waiting.",
  "Making progress.",
];

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

const setStatus = (online, text) => {
  statusDot.classList.toggle("online", online);
  statusText.textContent = text;
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
  // Wait a moment before speaking to avoid noise on fast responses.
  fillerTimer = setTimeout(() => {
    addMessage("assistant", fillerPhrases[fillerIndex % fillerPhrases.length]);
    speak(fillerPhrases[fillerIndex % fillerPhrases.length]);
    fillerIndex += 1;
    fillerInterval = setInterval(() => {
      addMessage("assistant", fillerPhrases[fillerIndex % fillerPhrases.length]);
      speak(fillerPhrases[fillerIndex % fillerPhrases.length]);
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
  commandInput.value = "";
  setStatus(true, "Thinking...");
  startFiller();
  try {
    const res = await fetch(`${apiBase}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const payload = await res.json();
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
  });
}

if (providerEmail) {
  providerEmail.addEventListener("change", async () => {
    providers.email = providerEmail.value;
    const ok = await persistProviders();
    if (ok) {
      addMessage("assistant", `Email provider set to ${providers.email}.`);
    }
  });
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
loadProviders();

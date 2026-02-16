const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const conversation = document.getElementById("conversation");
const commandInput = document.getElementById("command-input");
const sendButton = document.getElementById("send-button");
const confirmButton = document.getElementById("confirm-button");
const micButton = document.getElementById("mic-button");
const voiceToggle = document.getElementById("voice-toggle");
const personaButtons = Array.from(document.querySelectorAll(".persona-button"));

const apiBase = window.location.origin;
let recognition = null;
let voiceEnabled = false;
let pendingConfirmation = null;
let fillerTimer = null;
let fillerInterval = null;
let fillerIndex = 0;

let personaPresets = {};
let activePersona = "max";

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
  voiceEnabled = !voiceEnabled;
  voiceToggle.dataset.state = voiceEnabled ? "on" : "off";
  voiceToggle.textContent = voiceEnabled ? "On" : "Off";
});

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

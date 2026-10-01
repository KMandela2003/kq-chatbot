(() => {
  const transcript = document.getElementById("transcript");
  const form = document.getElementById("composer");
  const input = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const roleButtons = document.querySelectorAll(".role-btn");

  let role = "passenger";
  let sessionToken = null;

  roleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      roleButtons.forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      role = btn.dataset.role;
    });
  });

  function addMessage(text, sender, readoutData) {
    const wrap = document.createElement("div");
    wrap.className = `msg msg-${sender}`;
    if (readoutData && readoutData.escalated) wrap.classList.add("escalated");

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);

    if (readoutData) {
      const readout = document.createElement("div");
      readout.className = "readout";
      const intentClass = readoutData.escalated ? "r-danger" : "r-amber";
      readout.innerHTML = `
        <span class="r-item ${intentClass}">intent: ${readoutData.intent_label}</span>
        <span class="r-item r-teal">confidence: ${(readoutData.confidence * 100).toFixed(0)}%</span>
        <span class="r-item">${readoutData.latency_ms}ms</span>
      `;
      wrap.appendChild(readout);
    }

    transcript.appendChild(wrap);
    transcript.scrollTop = transcript.scrollHeight;
  }

  async function sendMessage(message) {
    sendBtn.disabled = true;
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, role, session_token: sessionToken }),
      });
      const data = await res.json();
      if (!res.ok) {
        addMessage(data.error || "Something went wrong.", "bot");
        return;
      }
      sessionToken = data.session_token;
      addMessage(data.response, "bot", data);
    } catch (err) {
      addMessage("Couldn't reach the support service. Is the server running?", "bot");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    addMessage(value, "user");
    input.value = "";
    sendMessage(value);
  });
})();

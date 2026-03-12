const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");

function addMessage(text, isUser) {
  const msg = document.createElement("div");
  msg.className = `message ${isUser ? "user-message" : "bot-message"}`;
  msg.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(msg);
  scrollToBottom();
  return msg;
}

function addBotMessageWithSources(text, sources) {
  const msg = document.createElement("div");
  msg.className = "message bot-message";

  let html = `<div class="message-bubble">${escapeHtml(text)}</div>`;

  if (sources && sources.length > 0) {
    html += `<div class="sources"><strong>Sources:</strong><ul>`;
    sources.forEach(function (s) {
      html += `<li>[${escapeHtml(s.category)}] ${escapeHtml(s.question)}</li>`;
    });
    html += `</ul></div>`;
  }

  msg.innerHTML = html;
  chatMessages.appendChild(msg);
  scrollToBottom();
}

function showLoading() {
  const msg = document.createElement("div");
  msg.className = "message bot-message";
  msg.id = "loading";
  msg.innerHTML = `<div class="loading-dots"><span></span><span></span><span></span></div>`;
  chatMessages.appendChild(msg);
  scrollToBottom();
}

function removeLoading() {
  const el = document.getElementById("loading");
  if (el) el.remove();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendMessage() {
  const question = chatInput.value.trim();
  if (!question) return;

  addMessage(question, true);
  chatInput.value = "";
  sendBtn.disabled = true;
  showLoading();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question }),
    });

    removeLoading();

    if (!res.ok) {
      addMessage("Sorry, something went wrong. Please try again.", false);
      return;
    }

    const data = await res.json();
    addBotMessageWithSources(data.answer, data.sources);
  } catch (err) {
    removeLoading();
    addMessage("Unable to reach the server. Please check your connection.", false);
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);

chatInput.addEventListener("keydown", function (e) {
  if (e.key === "Enter") {
    sendMessage();
  }
});

chatInput.focus();

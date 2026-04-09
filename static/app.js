const chat = document.getElementById("chat-messages");
const input = document.getElementById("symptoms-input");
const button = document.getElementById("predict-btn");

function addMessage(text, type) {
  const div = document.createElement("div");
  div.className = `bubble ${type}`;
  div.innerHTML = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function predict() {
  const text = input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";

  addMessage("Searching...", "bot");

  try {
    const res = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symptoms: text }),
    });

    const data = await res.json();
    chat.lastChild.remove();

    if (!data.success) {
      addMessage("Error occurred", "bot");
      return;
    }

    let statusEmoji = {
      critical: "🚨",
      moderate: "⚠️",
      mild: "✅",
    }[data.status];

    let preds = data.top_predictions
      .map((p) => `• ${p.disease} (${p.confidence.toFixed(1)}%)`)
      .join("<br>");

    let msg = `
            <strong>${statusEmoji} ${data.status.toUpperCase()}</strong><br><br>
            ${preds}<br><br>
            ${data.response}
        `;

    addMessage(msg, "bot");
  } catch {
    addMessage("Server error", "bot");
  }
}

button.onclick = predict;

input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    predict();
  }
});

(function () {
  const root = document.querySelector("[data-agent]");
  if (!root) return;

  const toggle = root.querySelector("[data-agent-toggle]");
  const close = root.querySelector("[data-agent-close]");
  const panel = root.querySelector("[data-agent-panel]");
  const form = root.querySelector("[data-agent-form]");
  const input = root.querySelector("[data-agent-input]");
  const messages = root.querySelector("[data-agent-messages]");
  const chatUrl = root.dataset.chatUrl;
  const confirmUrl = root.dataset.confirmUrl;
  const csrf = form.querySelector("input[name=csrfmiddlewaretoken]").value;

  function setOpen(open) {
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) input.focus();
  }

  function addMessage(text, type, actions) {
    const bubble = document.createElement("div");
    bubble.className = "movie-agent__message movie-agent__message--" + type;
    bubble.textContent = text;
    messages.appendChild(bubble);
    if (actions && actions.length) {
      const actionRow = document.createElement("div");
      actionRow.className = "movie-agent__actions";
      actions.forEach((action) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = action.label || "打开";
        if (action.type === "open_url") {
          button.addEventListener("click", () => {
            window.location.href = action.url;
          });
        } else if (action.type === "confirm_sync") {
          button.addEventListener("click", () => confirmAction(action.action_id, button));
        }
        actionRow.appendChild(button);
      });
      messages.appendChild(actionRow);
    }
    messages.scrollTop = messages.scrollHeight;
  }

  async function sendMessage(message) {
    if (!message) return;
    addMessage(message, "user");
    input.value = "";
    input.disabled = true;
    const submit = form.querySelector("button");
    submit.disabled = true;
    try {
      const response = await fetch(chatUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ message }),
      });
      const payload = await response.json();
      addMessage(payload.reply || "我暂时没有理解这个问题。", "bot", payload.actions || []);
    } catch (error) {
      addMessage("助手暂时连接失败，请稍后再试。", "bot");
    } finally {
      input.disabled = false;
      submit.disabled = false;
      input.focus();
    }
  }

  async function confirmAction(actionId, button) {
    button.disabled = true;
    try {
      const response = await fetch(confirmUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ action_id: actionId }),
      });
      const payload = await response.json();
      addMessage(payload.reply || "操作已处理。", "bot", payload.actions || []);
    } catch (error) {
      addMessage("确认操作失败，请重新发送请求。", "bot");
      button.disabled = false;
    }
  }

  toggle.addEventListener("click", () => setOpen(panel.hidden));
  close.addEventListener("click", () => setOpen(false));
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value.trim());
  });
  root.querySelectorAll("[data-agent-quick]").forEach((button) => {
    button.addEventListener("click", () => {
      setOpen(true);
      sendMessage(button.dataset.agentQuick);
    });
  });
})();

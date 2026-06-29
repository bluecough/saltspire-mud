(function () {
  const output = document.getElementById("output");
  const input = document.getElementById("cmd");

  function appendLine(html) {
    const div = document.createElement("div");
    div.className = "line";
    div.innerHTML = html;
    output.appendChild(div);
    output.scrollTop = output.scrollHeight;
  }

  function appendEcho(text) {
    const div = document.createElement("div");
    div.className = "line";
    div.style.color = "#5fd75f";
    div.textContent = "> " + text;
    output.appendChild(div);
    output.scrollTop = output.scrollHeight;
  }

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(proto + "//" + location.host + "/ws");

  ws.onopen = () => {
    input.disabled = false;
    input.focus();
  };

  // The server wraps password prompts in a tiny control message so the
  // client can mask the input box, instead of switching the whole protocol
  // to JSON. A null byte can never appear in a normal HTML line.
  const CTRL_PREFIX = "\x00CTRL\x00";

  ws.onmessage = (event) => {
    const data = event.data;
    if (data.startsWith(CTRL_PREFIX)) {
      const cmd = data.slice(CTRL_PREFIX.length);
      if (cmd === "PASSWORD_ON") input.type = "password";
      else if (cmd === "PASSWORD_OFF") input.type = "text";
      return;
    }
    appendLine(data);
  };

  ws.onclose = () => {
    appendLine('<span class="c-error">-- connection closed. Refresh the page to reconnect. --</span>');
    input.disabled = true;
  };

  ws.onerror = () => {
    appendLine('<span class="c-error">-- connection error --</span>');
  };

  const history = [];
  let historyIndex = -1;

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const text = input.value;
      if (text.length === 0) return;
      const isPassword = input.type === "password";
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(text);
        appendEcho(isPassword ? "*".repeat(text.length) : text);
      }
      if (!isPassword) {
        // Never let a password land in the recallable command history.
        history.push(text);
        historyIndex = history.length;
      }
      input.value = "";
    } else if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex -= 1;
        input.value = history[historyIndex] || "";
      }
      e.preventDefault();
    } else if (e.key === "ArrowDown") {
      if (historyIndex < history.length) {
        historyIndex += 1;
        input.value = history[historyIndex] || "";
      }
      e.preventDefault();
    }
  });

  document.body.addEventListener("click", () => input.focus());
})();

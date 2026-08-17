const form = document.getElementById("discount-form");
const codeInput = document.getElementById("discount-code");
const emailInput = document.getElementById("discount-email");
const message = document.getElementById("discount-message");
const priceNodes = document.querySelectorAll(".price-value");

function setMessage(text, kind) {
  message.textContent = text;
  message.className = `discount-message ${kind}`;
}

function updatePrices(percentOff) {
  const factor = 1 - percentOff / 100;
  priceNodes.forEach((node) => {
    const base = Number(node.dataset.base);
    const discounted = Math.round(base * factor);
    node.textContent = `$${discounted}`;
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("", "");

  const payload = { code: codeInput.value };
  const email = emailInput.value.trim();
  if (email) {
    payload.email = email;
  }

  try {
    const response = await fetch("/api/v1/discount/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      const detail = data.detail || "Could not apply discount code";
      setMessage(detail, "error");
      return;
    }

    updatePrices(data.percent_off);
    setMessage(`${data.code} applied — ${data.percent_off}% off.`, "success");
  } catch {
    setMessage("Could not reach the discount service.", "error");
  }
});

const forms = {
  human: ["neutral", "curious", "happy", "worried", "thoughtful"],
  reverse: ["neutral", "curious", "happy", "worried", "thoughtful"],
};

const labels = ["Attentive", "Curious", "Encouraged", "Concerned", "Reconsidering"];
const buttons = document.querySelectorAll("[data-form]");
const expressions = document.querySelectorAll(".expression");
const expressionGrid = document.querySelector("[data-expression-grid]");

function setForm(form) {
  expressionGrid.dataset.form = form;
  buttons.forEach((button) => {
    const active = button.dataset.form === form;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  expressions.forEach((expression, index) => {
    const image = expression.querySelector("img");
    const caption = expression.querySelector("figcaption");
    expression.classList.add("is-changing");

    window.setTimeout(() => {
      image.src = `assets/${form}-${forms[form][index]}.png`;
      image.alt = `Mateo ${labels[index].toLowerCase()} in ${form === "human" ? "centaur" : "reverse-centaur"} form`;
      caption.textContent = labels[index];
      expression.classList.remove("is-changing");
    }, 130);
  });
}

buttons.forEach((button) => {
  button.addEventListener("click", () => setForm(button.dataset.form));
});

setForm("human");

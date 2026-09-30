/* Shared calculator engine.
 *
 * Usage in a page:
 *   Calc.run(function (v, out) {
 *     // v: every named field in form.calc — numbers for number inputs, strings for selects,
 *     //    booleans for checkboxes. Empty number fields are 0.
 *     out.set("fee", Calc.money(v.price * 0.1));   // fills [data-out="fee"]
 *     out.set("profit", Calc.money(p), Calc.tone(p)); // green if positive, red if negative
 *     out.show("advanced", v.mode === "pro");       // toggles [data-show="advanced"]
 *     out.note("Optional message under the results");
 *   });
 */
(function () {
  const Calc = {};

  Calc.money = (n, digits = 2) => {
    if (!isFinite(n)) return "—";
    const s = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    return (n < 0 ? "−$" : "$") + s;
  };
  Calc.num = (n, digits = 1) => (isFinite(n)
    ? n.toLocaleString("en-US", { maximumFractionDigits: digits }) : "—");
  Calc.pct = (n, digits = 1) => (isFinite(n) ? Calc.num(n * 100, digits) + "%" : "—");
  // Color class for a signed number: out.set("profit", Calc.money(p), Calc.tone(p))
  Calc.tone = (n) => (n > 0 ? "pos" : n < 0 ? "neg" : "");

  function read(form) {
    const v = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      if (el.type === "checkbox") v[el.name] = el.checked;
      else if (el.type === "radio") { if (el.checked) v[el.name] = el.value; }
      else if (el.type === "number" || el.dataset.num !== undefined) v[el.name] = parseFloat(el.value) || 0;
      else v[el.name] = el.value;
    }
    return v;
  }

  Calc.run = function (fn) {
    const form = document.querySelector("form.calc");
    const root = form.closest(".calc-card") || document;
    const noteEl = root.querySelector("[data-note]");
    const out = {
      set(name, text, cls) {
        root.querySelectorAll(`[data-out="${name}"]`).forEach((el) => {
          el.textContent = text;
          el.classList.remove("pos", "neg");
          if (cls) el.classList.add(cls);
        });
      },
      show(name, on) { root.querySelectorAll(`[data-show="${name}"]`).forEach((el) => { el.hidden = !on; }); },
      note(text) { if (noteEl) { noteEl.textContent = text || ""; noteEl.hidden = !text; } },
    };
    const update = () => { out.note(""); fn(read(form), out); };
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", (e) => { e.preventDefault(); update(); });
    update();
  };

  window.Calc = Calc;
})();

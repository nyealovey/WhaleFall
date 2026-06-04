(function (global) {
  "use strict";

  const PROGRESS_SELECTOR = "[data-progress-percent]";

  function normalizePercent(value) {
    const percent = Number.parseFloat(value);
    if (!Number.isFinite(percent)) {
      return 0;
    }
    return Math.min(100, Math.max(0, percent));
  }

  function applyProgressBar(bar) {
    const percent = normalizePercent(bar?.dataset?.progressPercent);
    bar.style.width = `${percent}%`;

    if (bar.getAttribute("role") === "progressbar") {
      bar.setAttribute("aria-valuemin", "0");
      bar.setAttribute("aria-valuemax", "100");
      bar.setAttribute("aria-valuenow", String(Math.round(percent)));
    }
  }

  function applyProgressBars(root = document) {
    if (!root) {
      return;
    }

    if (root.matches?.(PROGRESS_SELECTOR)) {
      applyProgressBar(root);
      return;
    }

    root.querySelectorAll?.(PROGRESS_SELECTOR).forEach(applyProgressBar);
  }

  global.UI.applyProgressBars = applyProgressBars;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => applyProgressBars(document), { once: true });
  } else {
    applyProgressBars(document);
  }
})(window);

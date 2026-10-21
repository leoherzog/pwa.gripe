(function () {
  "use strict";

  // Try runtime feature detection
  function detectFeature(expr) {
    try {
      return !!Function('"use strict"; return (' + expr + ")")();
    } catch {
      return false;
    }
  }

  // Create support icon
  function createIcon(support) {
    const span = document.createElement("span");
    if (support === "y") {
      span.className = "support-y";
      span.textContent = "✔";
    } else {
      span.className = "support-n";
      span.textContent = "✘";
    }
    return span;
  }

  // Fill "Your Browser" column
  document.querySelectorAll("td[data-detect]").forEach(function (td) {
    td.appendChild(createIcon(detectFeature(td.dataset.detect) ? "y" : "n"));
  });

  // Theme switcher
  var themes = ["auto", "light", "dark"];
  var icons = {
    auto:  { text: "◑", label: "Auto" },
    light: { text: "☀", label: "Light" },
    dark:  { text: "☾", label: "Dark" },
  };
  var toggle = document.getElementById("theme-toggle");
  var current = localStorage.getItem("theme") || "auto";

  function applyTheme(value) {
    current = value;
    if (value === "auto") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", value);
    }
    var icon = icons[value];
    toggle.textContent = icon.text;
    toggle.setAttribute("data-tooltip", icon.label);
    toggle.setAttribute("aria-label", icon.label + " theme");
    localStorage.setItem("theme", value);
  }

  toggle.addEventListener("click", function () {
    var next = themes[(themes.indexOf(current) + 1) % themes.length];
    applyTheme(next);
  });

  applyTheme(current);
})();

// Fills the Your Browser column from each row's detect expression, runs the theme toggle and registers the service worker.

const ICONS = {
  y: { className: "support-y", text: "✔︎", label: "Supported" },
  n: { className: "support-n", text: "✘", label: "Not supported" },
  u: { className: "support-u", text: "?", label: "Unknown" },
};

const THEMES = {
  auto: { icon: "◑", label: "Auto" },
  light: { icon: "☀︎", label: "Light", color: "#ffffff" },
  dark: { icon: "☾", label: "Dark", color: "#13171f" },
};
const ORDER = Object.keys(THEMES);
const nextTheme = (value) => ORDER[(ORDER.indexOf(value) + 1) % ORDER.length];

/**
 * Evaluate a detect expression from build.py. A runtime throw counts as unsupported.
 * @param {string} expr
 * @returns {"y" | "n" | "u"} "u" when the expression does not compile
 */
function detect(expr) {
  let test;
  try {
    test = Function(`"use strict"; return (${expr});`);
  } catch (err) {
    console.error(`Invalid detect expression: ${expr}`, err);
    return "u";
  }
  try {
    return test() ? "y" : "n";
  } catch {
    return "n";
  }
}

for (const td of document.querySelectorAll("td[data-detect]")) {
  const icon = ICONS[detect(td.dataset.detect)];
  const span = document.createElement("span");
  span.className = icon.className;
  span.setAttribute("role", "img");
  span.setAttribute("aria-label", icon.label);
  span.textContent = icon.text;
  td.append(span);
}

const root = document.documentElement;
const toggle = document.getElementById("theme-toggle");
const themeColors = document.querySelectorAll('meta[name="theme-color"]');
// The head script has already applied any saved theme.
let current = root.dataset.theme ?? "auto";

function applyTheme(value) {
  current = value;
  const theme = THEMES[value];
  if (value === "auto") delete root.dataset.theme;
  else root.dataset.theme = value;
  // Each meta keeps its media query, so a forced theme has to override both.
  for (const meta of themeColors) {
    meta.content = theme.color ?? THEMES[meta.media.includes("dark") ? "dark" : "light"].color;
  }
  toggle.textContent = theme.icon;
  toggle.dataset.tooltip = `Theme: ${theme.label}`;
  toggle.setAttribute("aria-label", `Theme: ${theme.label}. Switch to ${THEMES[nextTheme(value)].label}`);
}

toggle.addEventListener("click", () => {
  const value = nextTheme(current);
  applyTheme(value);
  try {
    if (value === "auto") localStorage.removeItem("theme");
    else localStorage.setItem("theme", value);
  } catch {
    // Blocked storage only means the choice lasts for this page view.
  }
});

applyTheme(current);

addEventListener("load", () => {
  navigator.serviceWorker?.register("/sw.js").catch((err) => console.error("Service worker registration failed", err));
});

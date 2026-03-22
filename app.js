(function () {
  "use strict";

  const stats = JSON.parse(
    document.getElementById("caniuse-data").textContent
  );

  const browser = bowser.getParser(navigator.userAgent);
  const browserName = browser.getBrowserName();
  const browserVersion = browser.getBrowserVersion() || "";
  const majorVersion = browserVersion.split(".")[0];
  const osName = browser.getOSName();

  // Update column header
  const header = document.getElementById("user-browser-header");
  header.innerHTML = `${browserName} ${majorVersion}<br><small>${osName} (You!)</small>`;

  // Map Bowser browser name to caniuse key
  function mapBrowserKey() {
    // All iOS/iPadOS browsers use WebKit
    if (osName === "iOS" || osName === "iPadOS") return "ios_saf";

    const map = {
      Chrome: "chrome",
      Firefox: "firefox",
      Safari: "safari",
      "Microsoft Edge": "edge",
      Opera: "opera",
      "Samsung Internet": "samsung",
      "Android Browser": "android",
      Vivaldi: "chrome",
      Brave: "chrome",
      Chromium: "chrome",
      Yandex: "chrome",
    };
    return map[browserName] || null;
  }

  const caniuseKey = mapBrowserKey();

  // Find support for a specific version in a version map
  function findSupport(versionMap, targetMajor) {
    if (!versionMap) return null;

    const target = parseInt(targetMajor, 10);

    // Try exact match first
    for (const [ver, support] of Object.entries(versionMap)) {
      if (ver.includes("-")) {
        // Range like "14.0-14.4"
        const parts = ver.split("-");
        const lo = parseInt(parts[0], 10);
        const hi = parseInt(parts[1], 10);
        if (target >= lo && target <= hi) return support;
      } else if (parseInt(ver, 10) === target) {
        return support;
      }
    }

    // If version is newer than anything in the map, use latest
    const versions = Object.keys(versionMap);
    const latestKey = versions[versions.length - 1];
    const latestMajor = parseInt(latestKey.split("-")[0], 10);
    if (target > latestMajor) {
      return versionMap[latestKey];
    }

    return null;
  }

  // Try runtime feature detection
  function detectFeature(expr) {
    try {
      return !!Function('"use strict"; return (' + expr + ")")();
    } catch {
      return false;
    }
  }

  // Resolve note text from caniuse _notes for a given support value
  function resolveNote(featureId, rawSupport) {
    var featureStats = stats[featureId];
    if (!featureStats || !featureStats._notes || !rawSupport) return null;
    var matches = rawSupport.match(/#(\d+)/g);
    if (!matches) return null;
    var texts = [];
    for (var i = 0; i < matches.length; i++) {
      var num = matches[i].slice(1);
      if (featureStats._notes[num]) texts.push(featureStats._notes[num]);
    }
    return texts.length ? texts.join(" ") : null;
  }

  // Create support icon and set tooltip on the parent td
  function createIcon(td, support, tooltip) {
    const span = document.createElement("span");
    span.classList.add("fa-solid");

    switch (support) {
      case "y":
        span.classList.add("fa-circle-check", "support-y");
        span.textContent = "\u2714";
        break;
      case "a":
      case "d":
        span.classList.add("fa-circle-exclamation", "support-a");
        span.textContent = "\u26A0";
        break;
      default:
        span.classList.add("fa-circle-xmark", "support-n");
        span.textContent = "\u2718";
    }

    if (tooltip) td.dataset.tooltip = tooltip;

    return span;
  }

  // Find raw (un-normalized) support value for a version
  function findRawSupport(versionMap, targetMajor) {
    if (!versionMap) return null;
    var target = parseInt(targetMajor, 10);
    for (var ver in versionMap) {
      if (ver.includes("-")) {
        var parts = ver.split("-");
        if (target >= parseInt(parts[0], 10) && target <= parseInt(parts[1], 10))
          return versionMap[ver];
      } else if (parseInt(ver, 10) === target) {
        return versionMap[ver];
      }
    }
    var versions = Object.keys(versionMap);
    var latestKey = versions[versions.length - 1];
    if (target > parseInt(latestKey.split("-")[0], 10))
      return versionMap[latestKey];
    return null;
  }

  // Fill "Your Browser" column
  document.querySelectorAll("td[data-feature]").forEach(function (td) {
    const featureId = td.dataset.feature;
    const detectExpr = td.dataset.detect;
    let support = null;
    let tooltip = null;

    // Prefer runtime feature detection (direct browser check)
    if (detectExpr) {
      support = detectFeature(detectExpr) ? "y" : "n";
    }

    // Fallback: caniuse data lookup when no detect expression exists
    if (support === null && caniuseKey && stats[featureId]) {
      const browserStats = stats[featureId][caniuseKey];
      support = findSupport(browserStats, majorVersion);
    }

    // Resolve note tooltip for partial/flagged support
    if ((support === "a" || support === "d") && caniuseKey && stats[featureId]) {
      var raw = findRawSupport(stats[featureId][caniuseKey], majorVersion);
      tooltip = resolveNote(featureId, raw);
    }

    // Final fallback
    if (support === null) support = "u";

    td.appendChild(createIcon(td, support, tooltip));
  });

  // Theme switcher
  var themes = ["auto", "light", "dark"];
  var icons = {
    auto:  { fa: "fa-circle-half-stroke", text: "\u25D1", label: "Auto" },
    light: { fa: "fa-sun",                text: "\u2600", label: "Light" },
    dark:  { fa: "fa-moon",               text: "\u263E", label: "Dark" },
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
    var span = document.createElement("span");
    span.className = "fa-solid " + icon.fa;
    span.textContent = icon.text;
    toggle.replaceChildren(span);
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

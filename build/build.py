# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "jinja2"]
# ///
"""Download caniuse data and render index.html from Jinja template."""

import json
from datetime import date, timezone
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader

CANIUSE_URL = "https://raw.githubusercontent.com/Fyrd/caniuse/main/fulldata-json/data-2.0.json"

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"

# (display_name, caniuse_id_or_None, detect_expression_or_None)
FEATURES = [
    # (display_name, caniuse_id_or_None, detect_expression_or_None)
    # IDs verified against caniuse fulldata-json/data-2.0.json
    ("Installation", None, "'BeforeInstallPromptEvent' in window"),
    ("Offline Support", "serviceworkers", "'serviceWorker' in navigator"),
    ("Notifications", "notifications", "'Notification' in window"),
    ("Web Push", "push-api", "'PushManager' in window"),
    ("Shortcuts", None, None),
    ("View Transitions", "view-transitions", "'startViewTransition' in document"),
    ("Incoming Call Notifications", None, None),
    ("Geolocation", "geolocation", "'geolocation' in navigator"),
    ("Media Capture", "stream", "'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices"),
    ("Picture-in-Picture", "picture-in-picture", "document.pictureInPictureEnabled"),
    ("File System", "native-filesystem-api", "'showOpenFilePicker' in window"),
    ("Compression Streams", None, "'CompressionStream' in window"),
    ("Authentication", "webauthn", "'PublicKeyCredential' in window"),
    ("Protocol Handling", None, "'registerProtocolHandler' in navigator"),
    ("File Handling", None, "'launchQueue' in window"),
    ("Contact Picker", None, "'contacts' in navigator"),
    ("Web Share", "web-share", "'share' in navigator"),
    ("Virtual Keyboard", None, "'virtualKeyboard' in navigator"),
    ("Barcode Detection", None, "'BarcodeDetector' in window"),
    ("Face Detection", None, "'FaceDetector' in window"),
    ("Vibration", "vibration", "'vibrate' in navigator"),
    ("Audio Recording", "mediarecorder", "'MediaRecorder' in window"),
    ("Media Session", None, "'mediaSession' in navigator"),
    ("Audio Session", None, "'audioSession' in navigator"),
    ("Screen Capturing", "mdn-api_mediadevices_getdisplaymedia", "'getDisplayMedia' in navigator.mediaDevices"),
    ("Element Capture", None, "'CaptureController' in window"),
    ("Background Sync", "background-sync", "'SyncManager' in window"),
    ("Background Fetch", None, "'BackgroundFetchManager' in window"),
    ("Storage", "indexeddb", "'indexedDB' in window"),
    ("Bluetooth", "web-bluetooth", "'bluetooth' in navigator"),
    ("NFC", "webnfc", "'NDEFReader' in window"),
    ("AR / VR", "webxr", "'xr' in navigator"),
    ("Payment", "payment-request", "'PaymentRequest' in window"),
    ("Wake Lock", "wake-lock", "'wakeLock' in navigator"),
    ("Orientation", "deviceorientation", "'DeviceOrientationEvent' in window"),
    ("Motion", None, "'DeviceMotionEvent' in window"),
    ("Network Info", "netinfo", "'connection' in navigator"),
    ("Speech Synthesis", "speech-synthesis", "'speechSynthesis' in window"),
    ("Speech Recognition", "speech-recognition", "'SpeechRecognition' in window || 'webkitSpeechRecognition' in window"),
    ("Multi Touch", "touch", "'ontouchstart' in window"),
]

# Hardcoded support for features without caniuse data.
# Values: y=supported, a=partial, n=not supported
HARDCODED = {
    "Installation":               {"and_chr": "y", "ios_saf": "a"},
    "Shortcuts":                  {"and_chr": "y", "ios_saf": "n"},
    "Incoming Call Notifications": {"and_chr": "n", "ios_saf": "n"},
    "Compression Streams":        {"and_chr": "y", "ios_saf": "y"},
    "Protocol Handling":          {"and_chr": "y", "ios_saf": "n"},
    "File Handling":              {"and_chr": "y", "ios_saf": "n"},
    "Contact Picker":             {"and_chr": "y", "ios_saf": "n"},
    "Virtual Keyboard":           {"and_chr": "y", "ios_saf": "y"},
    "Barcode Detection":          {"and_chr": "y", "ios_saf": "a"},
    "Face Detection":             {"and_chr": "y", "ios_saf": "n"},
    "Media Session":              {"and_chr": "y", "ios_saf": "y"},
    "Audio Session":              {"and_chr": "n", "ios_saf": "n"},
    "Element Capture":            {"and_chr": "y", "ios_saf": "n"},
    "Background Fetch":           {"and_chr": "y", "ios_saf": "n"},
    "Motion":                     {"and_chr": "y", "ios_saf": "y"},
}

# Browsers to include in runtime stats (for "Your Browser" column)
RUNTIME_BROWSERS = [
    "chrome", "firefox", "safari", "edge", "opera",
    "samsung", "android", "and_ff", "op_mob",
]

MAX_VERSIONS = 15  # keep last N versions per browser


def normalize_support(val: str | None) -> str:
    """Strip note refs: 'y #1' -> 'y', 'a #2 #3' -> 'a'."""
    if not val:
        return "u"
    base = val.strip().split(" ")[0]
    return base if base in ("y", "a", "n", "d", "u", "p", "x") else "u"


def extract_note_nums(val: str | None) -> list[str]:
    """Extract note numbers from a support value like 'a #1 #3'."""
    if not val:
        return []
    import re
    return re.findall(r"#(\d+)", val)


def strip_markdown_links(text: str) -> str:
    """Convert markdown links [text](url) to just text."""
    import re
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def resolve_notes(val: str | None, notes_by_num: dict[str, str]) -> str | None:
    """Look up note text for a raw support value. Returns joined note string or None."""
    nums = extract_note_nums(val)
    if not nums:
        return None
    texts = [notes_by_num[n] for n in nums if n in notes_by_num]
    return strip_markdown_links(" ".join(texts)) if texts else None


def get_latest_raw(version_map: dict[str, str]) -> str | None:
    """Get the raw (un-normalized) support value for the latest version."""
    if not version_map:
        return None
    versions = list(version_map.keys())
    return version_map[versions[-1]]


def get_latest_support(version_map: dict[str, str]) -> str:
    """Get support value for the latest version in a version map."""
    return normalize_support(get_latest_raw(version_map))


def trim_versions(version_map: dict[str, str], n: int = MAX_VERSIONS) -> dict[str, str]:
    """Keep only the last n versions, normalize support values."""
    items = list(version_map.items())[-n:]
    return {ver: normalize_support(sup) for ver, sup in items}


def main():
    print("Downloading caniuse data...")
    resp = requests.get(CANIUSE_URL, timeout=30)
    resp.raise_for_status()
    caniuse = resp.json()
    all_data = caniuse["data"]
    agents = caniuse["agents"]

    # Get latest versions for fixed columns
    and_chr_latest = list(agents.get("and_chr", {}).get("version_list", [{}]))[-1].get("version", "?")
    ios_saf_latest = list(agents.get("ios_saf", {}).get("version_list", [{}]))[-1].get("version", "?")

    features_out = []
    runtime_stats = {}  # feature_id -> {browser_key: {version: support}}

    for display_name, caniuse_id, detect_expr in FEATURES:
        feature_id = (caniuse_id or display_name.lower().replace(" ", "-").replace("/", "-"))

        feature_data = all_data.get(caniuse_id) if caniuse_id else None

        chrome_note = None
        ios_note = None

        if feature_data:
            stats = feature_data.get("stats", {})
            notes_by_num = feature_data.get("notes_by_num", {})
            # Prefer and_chr/ios_saf; fall back to chrome/safari desktop
            # (many features lack mobile-specific entries)
            chrome_map = stats.get("and_chr", {}) or stats.get("chrome", {})
            ios_map = stats.get("ios_saf", {}) or stats.get("safari", {})
            chrome_support = get_latest_support(chrome_map)
            ios_support = get_latest_support(ios_map)

            # Resolve footnotes for partial/flagged support
            if chrome_support in ("a", "d"):
                chrome_note = resolve_notes(get_latest_raw(chrome_map), notes_by_num)
            if ios_support in ("a", "d"):
                ios_note = resolve_notes(get_latest_raw(ios_map), notes_by_num)

            # Build runtime stats for user browser lookup
            rt = {}
            for browser_key in RUNTIME_BROWSERS:
                browser_stats = stats.get(browser_key, {})
                if browser_stats:
                    rt[browser_key] = trim_versions(browser_stats)
            # Also include and_chr and ios_saf for completeness
            for bk in ("and_chr", "ios_saf"):
                bs = stats.get(bk, {})
                if bs:
                    rt[bk] = trim_versions(bs)
            # Include notes for runtime tooltip use
            if notes_by_num:
                rt["_notes"] = notes_by_num
            runtime_stats[feature_id] = rt
        else:
            # Use hardcoded values
            hc = HARDCODED.get(display_name, {"and_chr": "u", "ios_saf": "u"})
            chrome_support = hc.get("and_chr", "u")
            ios_support = hc.get("ios_saf", "u")

        features_out.append({
            "name": display_name,
            "id": feature_id,
            "chrome_support": chrome_support,
            "ios_support": ios_support,
            "chrome_note": chrome_note,
            "ios_note": ios_note,
            "detect": detect_expr,
        })

    # Render template
    env = Environment(loader=FileSystemLoader(str(BUILD)), autoescape=False)
    template = env.get_template("template.html.j2")

    html = template.render(
        features=features_out,
        stats_json=json.dumps(runtime_stats, separators=(",", ":")),
        updated=date.today().isoformat(),
        chrome_version=and_chr_latest,
        ios_version=ios_saf_latest,
    )

    out_path = ROOT / "index.html"
    out_path.write_text(html)
    print(f"Wrote {out_path} ({len(features_out)} features, updated {date.today()})")


if __name__ == "__main__":
    main()

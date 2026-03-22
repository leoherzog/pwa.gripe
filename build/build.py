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

# (display_name, caniuse_id, detect_expression, mdn_url, description)
MDN = "https://developer.mozilla.org/en-US/docs"
FEATURES = [
    ("Installation", None, "'BeforeInstallPromptEvent' in window",
     f"{MDN}/Web/Progressive_web_apps/Guides/Making_PWAs_installable",
     "Add the app to the home screen and launch it like a native app."),
    ("Offline Support", "serviceworkers", "'serviceWorker' in navigator",
     f"{MDN}/Web/API/Service_Worker_API",
     "Cache resources and serve content without a network connection."),
    ("Notifications", "notifications", "'Notification' in window",
     f"{MDN}/Web/API/Notifications_API",
     "Show system-level notifications outside the browser tab."),
    ("Web Push", "push-api", "'PushManager' in window",
     f"{MDN}/Web/API/Push_API",
     "Receive push messages from a server even when the app is closed."),
    ("Shortcuts", None, None,
     f"{MDN}/Web/Manifest/shortcuts",
     "Expose quick actions in the app icon's context menu."),
    ("View Transitions", "view-transitions", "'startViewTransition' in document",
     f"{MDN}/Web/API/View_Transition_API",
     "Animate seamless transitions between DOM states or page navigations."),
    ("Geolocation", "geolocation", "'geolocation' in navigator",
     f"{MDN}/Web/API/Geolocation_API",
     "Access the device's GPS or network-based location."),
    ("Media Capture", "stream", "'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices",
     f"{MDN}/Web/API/Media_Capture_and_Streams_API",
     "Access the camera and microphone for audio/video capture."),
    ("Picture-in-Picture", "picture-in-picture", "document.pictureInPictureEnabled",
     f"{MDN}/Web/API/Picture-in-Picture_API",
     "Float a video in a small overlay window above other content."),
    ("File System", "native-filesystem-api", "'showOpenFilePicker' in window",
     f"{MDN}/Web/API/File_System_API",
     "Read and write files directly on the user's local file system."),
    ("Compression Streams", None, "'CompressionStream' in window",
     f"{MDN}/Web/API/Compression_Streams_API",
     "Compress and decompress data streams using gzip or deflate."),
    ("Authentication", "webauthn", "'PublicKeyCredential' in window",
     f"{MDN}/Web/API/Web_Authentication_API",
     "Sign in with biometrics, security keys, or passkeys."),
    ("Protocol Handling", None, "'registerProtocolHandler' in navigator",
     f"{MDN}/Web/API/Navigator/registerProtocolHandler",
     "Register the app as a handler for custom URL protocols."),
    ("File Handling", None, "'launchQueue' in window",
     f"{MDN}/Web/Progressive_web_apps/How_to/Associate_files_with_your_PWA",
     "Open files from the OS directly in the installed web app."),
    ("Contact Picker", None, "'contacts' in navigator",
     f"{MDN}/Web/API/Contact_Picker_API",
     "Let the user select contacts from their device address book."),
    ("Web Share", "web-share", "'share' in navigator",
     f"{MDN}/Web/API/Web_Share_API",
     "Share text, URLs, or files using the native share sheet."),
    ("Virtual Keyboard", None, "'virtualKeyboard' in navigator",
     f"{MDN}/Web/API/VirtualKeyboard_API",
     "Control on-screen keyboard visibility and layout behavior."),
    ("Barcode Detection", None, "'BarcodeDetector' in window",
     f"{MDN}/Web/API/Barcode_Detection_API",
     "Detect and decode barcodes and QR codes from images or camera feeds."),
    ("Face Detection", None, "'FaceDetector' in window",
     "https://wicg.github.io/shape-detection-api/#face-detection-api",
     "Detect faces in images using the platform's native detector."),
    ("Vibration", "vibration", "'vibrate' in navigator",
     f"{MDN}/Web/API/Vibration_API",
     "Trigger haptic vibration patterns on the device."),
    ("Audio Recording", "mediarecorder", "'MediaRecorder' in window",
     f"{MDN}/Web/API/MediaStream_Recording_API",
     "Record audio or video from a media stream."),
    ("Media Session", None, "'mediaSession' in navigator",
     f"{MDN}/Web/API/Media_Session_API",
     "Customize media playback controls in the OS notification area."),
    ("Audio Session", None, "'audioSession' in navigator",
     f"{MDN}/Web/API/AudioSession",
     "Declare audio session type to coordinate with other audio sources."),
    ("Screen Capturing", "mdn-api_mediadevices_getdisplaymedia", "'getDisplayMedia' in navigator.mediaDevices",
     f"{MDN}/Web/API/Screen_Capture_API",
     "Capture the contents of a screen, window, or tab as a media stream."),
    ("Element Capture", None, "'CaptureController' in window",
     f"{MDN}/Web/API/Screen_Capture_API/Element_Region_Capture",
     "Restrict a screen capture stream to a specific DOM element."),
    ("Background Sync", "background-sync", "'SyncManager' in window",
     f"{MDN}/Web/API/Background_Synchronization_API",
     "Defer actions until the device has a stable network connection."),
    ("Background Fetch", None, "'BackgroundFetchManager' in window",
     f"{MDN}/Web/API/Background_Fetch_API",
     "Download or upload large files in the background, surviving page close."),
    ("Storage", "indexeddb", "'indexedDB' in window",
     f"{MDN}/Web/API/IndexedDB_API",
     "Store large amounts of structured data locally in the browser."),
    ("Bluetooth", "web-bluetooth", "'bluetooth' in navigator",
     f"{MDN}/Web/API/Web_Bluetooth_API",
     "Communicate with nearby Bluetooth Low Energy devices."),
    ("NFC", "webnfc", "'NDEFReader' in window",
     f"{MDN}/Web/API/Web_NFC_API",
     "Read and write NFC tags when the device is held close."),
    ("AR / VR", "webxr", "'xr' in navigator",
     f"{MDN}/Web/API/WebXR_Device_API",
     "Render augmented or virtual reality experiences using headsets or cameras."),
    ("Payment", "payment-request", "'PaymentRequest' in window",
     f"{MDN}/Web/API/Payment_Request_API",
     "Invoke the browser's built-in payment UI for checkout flows."),
    ("Wake Lock", "wake-lock", "'wakeLock' in navigator",
     f"{MDN}/Web/API/Screen_Wake_Lock_API",
     "Prevent the screen from dimming or locking while the app is active."),
    ("Orientation", "deviceorientation", "'DeviceOrientationEvent' in window",
     f"{MDN}/Web/API/Device_orientation_events",
     "Read the device's compass heading, tilt, and rotation."),
    ("Motion", None, "'DeviceMotionEvent' in window",
     f"{MDN}/Web/API/DeviceMotionEvent",
     "Read accelerometer and gyroscope data for motion sensing."),
    ("Network Info", "netinfo", "'connection' in navigator",
     f"{MDN}/Web/API/Network_Information_API",
     "Query the device's network connection type and effective speed."),
    ("Speech Synthesis", "speech-synthesis", "'speechSynthesis' in window",
     f"{MDN}/Web/API/SpeechSynthesis",
     "Convert text to spoken audio using the platform's voices."),
    ("Speech Recognition", "speech-recognition", "'SpeechRecognition' in window || 'webkitSpeechRecognition' in window",
     f"{MDN}/Web/API/SpeechRecognition",
     "Transcribe spoken words into text in real time."),
    ("Multi Touch", "touch", "'ontouchstart' in window",
     f"{MDN}/Web/API/Touch_events",
     "Respond to multi-finger touch gestures on the screen."),
]

# Hardcoded support for features without caniuse data.
# Values: y=supported, a=partial, n=not supported
HARDCODED = {
    "Installation":               {"and_chr": "y", "ios_saf": "a"},
    "Shortcuts":                  {"and_chr": "y", "ios_saf": "n"},
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

    for display_name, caniuse_id, detect_expr, mdn_url, description in FEATURES:
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
            "mdn_url": mdn_url,
            "description": description,
        })

    # Sort: Android-yes/iOS-no first, then iOS-yes/Android-no, then the rest
    def sort_key(f):
        chrome_yes = f["chrome_support"] in ("y", "a")
        ios_yes = f["ios_support"] in ("y", "a")
        if chrome_yes and not ios_yes:
            return 0
        if ios_yes and not chrome_yes:
            return 1
        return 2
    features_out.sort(key=sort_key)

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

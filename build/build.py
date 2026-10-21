# /// script
# requires-python = ">=3.12"
# dependencies = ["jinja2"]
# ///
"""Download caniuse data and render index.html from the Jinja template."""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.request import urlopen

from jinja2 import Environment, FileSystemLoader, StrictUndefined

CANIUSE_URL = "https://raw.githubusercontent.com/Fyrd/caniuse/main/fulldata-json/data-2.0.json"

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
MDN = "https://developer.mozilla.org/en-US/docs"

MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
NOTE_REF = re.compile(r"#(\d+)")
RANK = {"y": 2, "a": 1, "n": 0}


@dataclass(frozen=True)
class Feature:
    """One table row. android/ios take y, a or n; they override caniuse and are required without it.

    detect is a JS expression for the Your Browser column; without one that cell shows unknown.
    """

    name: str
    description: str
    url: str
    caniuse: str | None = None
    detect: str | None = None
    android: str | None = None
    ios: str | None = None

    def __post_init__(self):
        if not self.caniuse and not (self.android and self.ios):
            raise ValueError(f"{self.name}: needs a caniuse id or both android and ios values")


FEATURES = [
    Feature("Install Prompt", "Offer an in-app install button instead of relying on the browser menu.",
            f"{MDN}/Web/Progressive_web_apps/How_to/Trigger_install_prompt",
            detect="'BeforeInstallPromptEvent' in window", android="y", ios="n"),
    Feature("Offline Support", "Cache resources and serve content without a network connection.",
            f"{MDN}/Web/API/Service_Worker_API",
            caniuse="serviceworkers", detect="'serviceWorker' in navigator"),
    Feature("Notifications", "Show system-level notifications outside the browser tab.",
            f"{MDN}/Web/API/Notifications_API",
            caniuse="notifications", detect="'Notification' in window"),
    Feature("Web Push", "Receive push messages from a server even when the app is closed.",
            f"{MDN}/Web/API/Push_API",
            caniuse="push-api", detect="'PushManager' in window"),
    Feature("Shortcuts", "Expose quick actions in the app icon's context menu.",
            f"{MDN}/Web/Progressive_web_apps/Manifest/Reference/shortcuts",
            android="y", ios="n"),
    Feature("View Transitions", "Animate seamless transitions between DOM states or page navigations.",
            f"{MDN}/Web/API/View_Transition_API",
            caniuse="view-transitions", detect="'startViewTransition' in document"),
    Feature("Geolocation", "Access the device's GPS or network-based location.",
            f"{MDN}/Web/API/Geolocation_API",
            caniuse="geolocation", detect="'geolocation' in navigator"),
    Feature("Media Capture", "Access the camera and microphone for audio/video capture.",
            f"{MDN}/Web/API/Media_Capture_and_Streams_API",
            caniuse="stream", detect="'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices"),
    # caniuse marks Chrome Android partial over an auto-PiP note; the API itself has shipped since Chrome 105.
    Feature("Picture-in-Picture", "Float a video in a small overlay window above other content.",
            f"{MDN}/Web/API/Picture-in-Picture_API",
            caniuse="picture-in-picture", detect="document.pictureInPictureEnabled", android="y"),
    # caniuse still lists Chrome Android as unsupported; the pickers shipped there in Chrome 132.
    Feature("File System", "Read and write files directly on the user's local file system.",
            f"{MDN}/Web/API/Window/showOpenFilePicker",
            caniuse="native-filesystem-api", detect="'showOpenFilePicker' in window", android="y"),
    Feature("Compression Streams", "Compress and decompress data streams using gzip or deflate.",
            f"{MDN}/Web/API/Compression_Streams_API",
            detect="'CompressionStream' in window", android="y", ios="y"),
    Feature("Authentication", "Sign in with biometrics, security keys, or passkeys.",
            f"{MDN}/Web/API/Web_Authentication_API",
            caniuse="webauthn", detect="'PublicKeyCredential' in window"),
    Feature("Protocol Handling", "Register the app as a handler for custom URL protocols.",
            f"{MDN}/Web/API/Navigator/registerProtocolHandler",
            caniuse="registerprotocolhandler", detect="'registerProtocolHandler' in navigator"),
    Feature("File Handling", "Open files from the OS directly in the installed web app.",
            f"{MDN}/Web/Progressive_web_apps/How_to/Associate_files_with_your_PWA",
            detect="'launchQueue' in window", android="n", ios="n"),
    Feature("Contact Picker", "Let the user select contacts from their device address book.",
            f"{MDN}/Web/API/Contact_Picker_API",
            detect="'contacts' in navigator", android="y", ios="n"),
    Feature("Web Share", "Share text, URLs, or files using the native share sheet.",
            f"{MDN}/Web/API/Web_Share_API",
            caniuse="web-share", detect="'share' in navigator"),
    Feature("Virtual Keyboard", "Control on-screen keyboard visibility and layout behavior.",
            f"{MDN}/Web/API/VirtualKeyboard_API",
            detect="'virtualKeyboard' in navigator", android="y", ios="n"),
    Feature("Barcode Detection", "Detect and decode barcodes and QR codes from images or camera feeds.",
            f"{MDN}/Web/API/Barcode_Detection_API",
            detect="'BarcodeDetector' in window", android="y", ios="n"),
    Feature("Face Detection", "Detect faces in images using the platform's native detector.",
            "https://wicg.github.io/shape-detection-api/#face-detection-api",
            detect="'FaceDetector' in window", android="n", ios="n"),
    Feature("Vibration", "Trigger haptic vibration patterns on the device.",
            f"{MDN}/Web/API/Vibration_API",
            caniuse="vibration", detect="'vibrate' in navigator"),
    Feature("Audio Recording", "Record audio or video from a media stream.",
            f"{MDN}/Web/API/MediaStream_Recording_API",
            caniuse="mediarecorder", detect="'MediaRecorder' in window"),
    Feature("Media Session", "Customize media playback controls in the OS notification area.",
            f"{MDN}/Web/API/Media_Session_API",
            detect="'mediaSession' in navigator", android="y", ios="y"),
    Feature("Audio Session", "Declare audio session type to coordinate with other audio sources.",
            f"{MDN}/Web/API/AudioSession",
            detect="'audioSession' in navigator", android="n", ios="y"),
    Feature("Screen Capturing", "Capture the contents of a screen, window, or tab as a media stream.",
            f"{MDN}/Web/API/Screen_Capture_API",
            detect="'mediaDevices' in navigator && 'getDisplayMedia' in navigator.mediaDevices",
            android="n", ios="y"),
    Feature("Element Capture", "Restrict a screen capture stream to a specific DOM element.",
            f"{MDN}/Web/API/Screen_Capture_API/Element_Region_Capture",
            detect="'RestrictionTarget' in window", android="n", ios="n"),
    Feature("Background Sync", "Defer actions until the device has a stable network connection.",
            f"{MDN}/Web/API/Background_Synchronization_API",
            caniuse="background-sync", detect="'SyncManager' in window"),
    Feature("Background Fetch", "Download or upload large files in the background, surviving page close.",
            f"{MDN}/Web/API/Background_Fetch_API",
            detect="'BackgroundFetchManager' in window", android="y", ios="n"),
    Feature("Storage", "Store large amounts of structured data locally in the browser.",
            f"{MDN}/Web/API/IndexedDB_API",
            caniuse="indexeddb", detect="'indexedDB' in window"),
    Feature("Bluetooth", "Communicate with nearby Bluetooth Low Energy devices.",
            f"{MDN}/Web/API/Web_Bluetooth_API",
            caniuse="web-bluetooth", detect="'bluetooth' in navigator"),
    Feature("NFC", "Read and write NFC tags when the device is held close.",
            f"{MDN}/Web/API/Web_NFC_API",
            caniuse="webnfc", detect="'NDEFReader' in window"),
    Feature("AR / VR", "Render augmented or virtual reality experiences using headsets or cameras.",
            f"{MDN}/Web/API/WebXR_Device_API",
            caniuse="webxr", detect="'xr' in navigator"),
    Feature("Payment", "Invoke the browser's built-in payment UI for checkout flows.",
            f"{MDN}/Web/API/Payment_Request_API",
            caniuse="payment-request", detect="'PaymentRequest' in window"),
    Feature("Wake Lock", "Prevent the screen from dimming or locking while the app is active.",
            f"{MDN}/Web/API/Screen_Wake_Lock_API",
            caniuse="wake-lock", detect="'wakeLock' in navigator"),
    Feature("Orientation", "Read the device's compass heading, tilt, and rotation.",
            f"{MDN}/Web/API/Device_orientation_events",
            caniuse="deviceorientation", detect="'DeviceOrientationEvent' in window"),
    # The deviceorientation caniuse entry covers both orientation and motion events.
    Feature("Motion", "Read accelerometer and gyroscope data for motion sensing.",
            f"{MDN}/Web/API/DeviceMotionEvent",
            caniuse="deviceorientation", detect="'DeviceMotionEvent' in window"),
    Feature("Network Info", "Query the device's network connection type and effective speed.",
            f"{MDN}/Web/API/Network_Information_API",
            caniuse="netinfo", detect="'connection' in navigator"),
    Feature("Speech Synthesis", "Convert text to spoken audio using the platform's voices.",
            f"{MDN}/Web/API/SpeechSynthesis",
            caniuse="speech-synthesis", detect="'speechSynthesis' in window"),
    Feature("Speech Recognition", "Transcribe spoken words into text in real time.",
            f"{MDN}/Web/API/SpeechRecognition",
            caniuse="speech-recognition", detect="'SpeechRecognition' in window || 'webkitSpeechRecognition' in window"),
    Feature("Multi Touch", "Respond to multi-finger touch gestures on the screen.",
            f"{MDN}/Web/API/Touch_events",
            caniuse="touch", detect="'TouchEvent' in window"),
]


def support(raw: str) -> str:
    """Reduce a caniuse value such as 'a x #2' to y, a or n."""
    value = raw.split()[0]
    return value if value in ("y", "a") else "n"


def note(raw: str, notes_by_num: dict[str, str]) -> str | None:
    """Join the footnotes a caniuse value references, as plain text."""
    texts = [notes_by_num[n] for n in NOTE_REF.findall(raw) if n in notes_by_num]
    return MD_LINK.sub(r"\1", " ".join(texts)).replace("`", "") or None


def column(override: str | None, entry: dict | None, browser: str, version: str) -> tuple[str, str | None]:
    """Return (support, partial-support note) for one fixed column. An override carries no note."""
    if override:
        return override, None
    raw = entry["stats"][browser][version]
    value = support(raw)
    return value, note(raw, entry["notes_by_num"]) if value == "a" else None


def group(android: str, ios: str) -> int:
    """Sort group: 0 when Android support beats iOS, 1 when iOS beats Android, 2 on a tie."""
    gap = RANK[android] - RANK[ios]
    return 0 if gap > 0 else 1 if gap < 0 else 2


def main():
    print("Downloading caniuse data...")
    with urlopen(CANIUSE_URL, timeout=30) as resp:
        caniuse = json.load(resp)
    data = caniuse["data"]
    # caniuse lists unreleased versions after current_version.
    android_version = caniuse["agents"]["and_chr"]["current_version"]
    ios_version = caniuse["agents"]["ios_saf"]["current_version"]

    rows = []
    for f in FEATURES:
        if f.caniuse and f.caniuse not in data:
            raise SystemExit(f"{f.name}: caniuse id {f.caniuse!r} is not in data-2.0.json")
        entry = data.get(f.caniuse)
        android, android_note = column(f.android, entry, "and_chr", android_version)
        ios, ios_note = column(f.ios, entry, "ios_saf", ios_version)
        rows.append({
            "name": f.name,
            "description": f.description,
            "url": f.url,
            "detect": f.detect,
            "android": android,
            "ios": ios,
            "android_note": android_note,
            "ios_note": ios_note,
            "group": group(android, ios),
        })
    rows.sort(key=lambda r: r["group"])

    env = Environment(loader=FileSystemLoader(BUILD), autoescape=True, undefined=StrictUndefined)
    today = date.today().isoformat()
    html = env.get_template("template.html.j2").render(
        features=rows,
        updated=today,
        android_version=android_version,
        ios_version=ios_version,
    )

    out_path = ROOT / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} ({len(rows)} features, updated {today})")


if __name__ == "__main__":
    main()

# Camera review — 2026-11-14

User reports severe preview lag and confirms actual black/white inversion (white becomes black AND black becomes white). Saved capture has not yet been checked. Review covers the local working tree only; deployed Pi revision, installed Picamera2 version, lighting and actual image pixels were not inspected.

## Confirmed code findings

1. P2 — ui/app.js:52-54: preview fetches a complete JPEG, then waits another 700 ms before requesting the next. Single-loop update frequency is bounded by 1000 / (700 + request/blob time) fps, under about 1.43 fps even before browser rendering. This is a frame-update bound, not a measured sensor-to-screen latency.
2. P2 — field_app/camera.py:18,25-30 and field_app/server.py:214-218,254-264: live preview uses the same 1280x960 still capture/JPEG method and camera lock as saved captures. There is no separate preview stream/latest-frame producer. A pending preview delays a capture; the capture route also holds the application-wide lock while waiting for camera I/O. Actual timing needs Pi measurements. Current upstream still defaults include one buffer, high-quality noise reduction and a broad frame-duration range; installed defaults must be checked before assuming identical behavior.
3. P2 — ui/app.js:51-54,60: stopPreview does not cancel its timer or pending fetch; both old/new loops share live. Stop/restart before the old timer fires leaves two independently scheduling loops. Reproduced using actual app.js in a Node VM with stub DOM/fetch/timers: 1 initial timer -> 2 after restart -> 2 continuing timers. Use a generation token, clearTimeout and cancellation; keep only one live acquisition loop.
4. P2 — field_app/camera.py:11-14: the UI button labelled reconnect calls start, but start returns whenever device is non-null, even after capture failure. Python fake-device reproduction confirms start retains the same failed device. Provide explicit serialized recovery/close/reopen, including bounded failure handling; do not race an in-flight capture.

## Black/white inversion: cause not established

The local path is Picamera2.capture_file(JPEG) -> HTTP image/jpeg -> Blob URL -> img; capture storage also writes those JPEG bytes. No local pixel inversion, OpenCV conversion, canvas transform or image CSS inversion was found. The only CSS brightness filter applies to active buttons. Swapping R/B channels cannot exchange neutral black and white. Upstream JPEG saving maps the configured pixel format; the BGR888 name alone is not evidence of a channel-order bug.

NoIR sensitivity/tuning can affect colour, but the user's confirmed negative-like inversion must not be diagnosed as normal NoIR behaviour without image evidence. Do not apply a compensating inversion or guessed white balance to AI input.

Discriminating checks on Pi:
1. With a stationary white sheet and black object in one scene, save one capture and open it in the gallery.
2. Export that session, extract its images/ JPEG and view it outside the browser, ideally on another display. If file looks normal, inspect browser forced-dark extensions/accessibility colour inversion and display settings; these are hypotheses, not established causes.
3. If the saved file is inverted too, stop the app before using the OS camera preview (rpicam-hello if installed). Compare the same scene/light; do not run two camera owners together. Collect camera model, package versions, active configuration/metadata and deployed revision before changing controls.
4. Measure capture/JPEG time, HTTP time and sensor frame duration separately; the model's inference latency is not camera preview latency.

## Proposed repair scope (not implemented)

Use a continuous camera configuration with an explicit tested frame-rate/exposure budget, a lower-resolution preview path/latest-frame delivery and separate saved-image resolution. Ensure a single preview consumer lifecycle and genuine reconnect recovery. Preserve model/decision rules and original saved-image evidence. Validate colour against an actual saved JPEG before changing colour processing. No achieved fps or Pi success is claimed.

## Primary sources checked

- https://raw.githubusercontent.com/raspberrypi/picamera2/main/picamera2/picamera2.py — configuration defaults and capture_file implementation (upstream main, not proof of installed version).
- https://raw.githubusercontent.com/raspberrypi/picamera2/main/picamera2/request.py — format-aware JPEG encoding.
- https://www.raspberrypi.com/documentation/accessories/camera-software.html — NoIR/tuning distinctions; tuning examples for IMX219 must not be copied blindly to Module 3/IMX708.

Verification: deterministic UI lifecycle simulation and fake-device reconnect test only. No Pi connection/hardware execution. Application code, camera controls, models and thresholds unchanged.

## Follow-up implementation
Confirmed code defects addressed after this review; see [FIXES_2026-11-14.md](FIXES_2026-11-14.md) for changes and tests. Hardware colour inversion and measured Pi performance still require device evidence.

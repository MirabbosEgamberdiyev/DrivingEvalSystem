"""Camera Discovery & USB Controller Topology Diagnostics Utility.

Scans connected DirectShow camera devices, queries supported resolutions and FPS,
and inspects Windows USB controller topology to prevent USB bus bandwidth bottlenecks.
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import time
from typing import Any

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("camera_discovery")


def probe_directshow_cameras(max_index: int = 6) -> list[dict[str, Any]]:
    """Probes video capture indexes 0..max_index using DirectShow backend on Windows."""
    found: list[dict[str, Any]] = []

    test_resolutions = [
        (1920, 1080),
        (1280, 720),
        (640, 480),
    ]

    for idx in range(max_index):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            continue

        # Camera responds
        cam_info: dict[str, Any] = {
            "index": idx,
            "backend": "CAP_DSHOW",
            "supported_resolutions": [],
        }

        for w, h in test_resolutions:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = cap.get(cv2.CAP_PROP_FPS)

            if actual_w == w and actual_h == h:
                # Read a test frame to measure capture latency
                t0 = time.monotonic()
                ret, frame = cap.read()
                latency_ms = round((time.monotonic() - t0) * 1000.0, 1)

                if ret and frame is not None:
                    cam_info["supported_resolutions"].append({
                        "resolution": [w, h],
                        "fps": actual_fps or 30.0,
                        "frame_read_ok": True,
                        "latency_ms": latency_ms,
                    })

        cap.release()
        found.append(cam_info)

    return found


def query_windows_usb_devices() -> list[dict[str, str]]:
    """Queries Windows PnP entities to identify USB cameras and host controllers."""
    if platform.system() != "Windows":
        return []

    ps_cmd = (
        'Get-CimInstance Win32_PnPEntity | '
        'Where-Object { $_.PNPClass -in @("Camera", "Image", "USB") } | '
        'Select-Object Name, DeviceID, PNPClass, Status | '
        'ConvertTo-Json -Compress'
    )

    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
    except Exception as e:
        logger.warning("Could not query Windows PnP devices: %s", e)

    return []


def print_camera_report(cameras: list[dict[str, Any]], usb_entities: list[dict[str, str]]) -> None:
    """Formats and prints console diagnostic report."""
    print("\n" + "=" * 65)
    print("4-KAMERALI TIZIM APPARAT VA USB DIAGNOSTIKA HISOBOTI")
    print("=" * 65)

    print(f"\n[+] Aniqlangan DirectShow kameralar soni: {len(cameras)}")
    for cam in cameras:
        idx = cam["index"]
        print(f"\n  Kamera Indeksi [{idx}]:")
        for r in cam["supported_resolutions"]:
            w, h = r["resolution"]
            fps = r["fps"]
            lat = r["latency_ms"]
            print(f"    - {w}x{h} @ {fps:.0f} FPS (Frame olish kechikishi: {lat} ms)")

    if len(cameras) < 4:
        print(f"\n[!] OGOHLANTIRISH: Tizimga {len(cameras)} ta kamera ulangan. Real imtihon uchun kamida 4 ta talab qilinadi.")
    else:
        print("\n[OK] 4 ta kamera mavjud! Tavsiya etilgan konfiguratsiya:")
        print("     FRONT: index 0")
        print("     REAR:  index 1")
        print("     LEFT:  index 2")
        print("     RIGHT: index 3")

    print("\n[+] Windows USB va Kamera qurilmalari ro'yxati:")
    for dev in usb_entities[:10]:
        name = dev.get("Name", "Noma'lum")
        pnp = dev.get("PNPClass", "")
        status = dev.get("Status", "OK")
        print(f"    * [{pnp}] {name} (Holati: {status})")

    print("=" * 65 + "\n")


def main() -> int:
    logger.info("DirectShow kameralari skanerlanmoqda...")
    cameras = probe_directshow_cameras()
    usb_entities = query_windows_usb_devices()
    print_camera_report(cameras, usb_entities)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

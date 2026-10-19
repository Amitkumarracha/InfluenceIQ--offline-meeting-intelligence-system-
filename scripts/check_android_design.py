#!/usr/bin/env python3
"""Read-only UI smoke check on an explicitly selected Android emulator.

Requires an installed debug APK, adb and an unlocked emulator. The default
check does not modify meetings; --check-cached-update explicitly updates a
completed meeting three times to verify that quick jobs release UI controls.
"""
import argparse
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--meeting-title", help="Existing meeting to inspect")
    parser.add_argument("--check-cached-update", action="store_true", help="Exercise Update analysis on an already completed matching checkpoint")
    parser.add_argument("--output", type=Path, default=Path("outputs/android-design"))
    args = parser.parse_args()
    if not args.serial.startswith("emulator-"):
        parser.error("Use an emulator; physical-device testing is manual.")
    if args.check_cached_update and not args.meeting_title:
        parser.error("--check-cached-update requires --meeting-title")
    args.output.mkdir(parents=True, exist_ok=True)

    def adb(*command):
        return subprocess.check_output([args.adb, "-s", args.serial, *command], timeout=40)

    def tree():
        adb("shell", "uiautomator", "dump", "/sdcard/influence-design-check.xml")
        return ET.fromstring(adb("shell", "cat", "/sdcard/influence-design-check.xml"))

    def control(label, description=True):
        for node in tree().iter("node"):
            if node.get("content-desc" if description else "text") == label:
                bounds = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
                if len(bounds) == 4 and bounds[2] > bounds[0] and bounds[3] > bounds[1]:
                    return node, bounds
        return None

    def tap(label, description=True):
        match = control(label, description)
        assert match, f"Missing visible control: {label}"
        node, (left, top, right, bottom) = match
        assert node.get("enabled") == "true", f"Disabled control: {label}"
        adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))
        time.sleep(.5)

    def capture(name):
        (args.output / (name + ".png")).write_bytes(adb("exec-out", "screencap", "-p"))
        (args.output / (name + ".xml")).write_bytes(ET.tostring(tree()))

    def reveal(label, horizontal=False, description=True):
        for _ in range(8):
            if control(label, description):
                return
            kind = "android.widget.HorizontalScrollView" if horizontal else "android.widget.ScrollView"
            view = next(n for n in tree().iter("node") if n.get("class") == kind)
            left, top, right, bottom = map(int, re.findall(r"\d+", view.get("bounds")))
            if horizontal:
                adb("shell", "input", "swipe", str(right-30), str((top+bottom)//2), str(left+30), str((top+bottom)//2), "300")
            else:
                adb("shell", "input", "swipe", str((left+right)//2), str(bottom-80), str((left+right)//2), str(top+180), "300")
            time.sleep(.3)
        raise AssertionError(f"Could not reveal control: {label}")

    adb("shell", "am", "start", "-n", "org.meetiq.offline/.MainActivity")
    time.sleep(1)
    # Run from Home; do not force-stop a running foreground operation.
    assert control("Record meeting"), "Open Home before running this check"
    capture("home")
    tap("Settings")
    assert control("Name")
    capture("settings")
    reveal("Transcription language")
    capture("settings-language")
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(.5)
    if args.meeting_title:
        label = "Open meeting " + args.meeting_title
        if not control(label):
            reveal("History")
            tap("History")
        for _ in range(20):
            if control(label):
                break
            # Use visible scroll bounds, so the check is independent of density.
            view = next(n for n in tree().iter("node") if n.get("class") == "android.widget.ScrollView")
            left, top, right, bottom = map(int, re.findall(r"\d+", view.get("bounds")))
            adb("shell", "input", "swipe", str((left + right)//2), str(bottom-80), str((left + right)//2), str(top+180), "300")
        tap(label)
        if args.check_cached_update:
            for _ in range(3):
                reveal("Update analysis")
                tap("Update analysis")
                for attempt in range(12):
                    time.sleep(.5)
                    found=control("Update analysis")
                    if found and found[0].get("enabled")=="true":
                        break
                else:
                    raise AssertionError("Cached update left the controls locked")
        for section in ("Overview", "Transcript", "Action items", "Decisions", "Analysis"):
            reveal(section, horizontal=True)
            tap(section)
            capture(section.lower().replace(" ", "-"))
        tap("Back to meetings")
    print(f"Android design smoke check passed; screenshots: {args.output}")


if __name__ == "__main__":
    main()

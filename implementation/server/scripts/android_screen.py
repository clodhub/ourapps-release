#!/usr/bin/env python3
"""Install an Android app on the one running emulator or device, start it, and drive it until given text is on screen.

  android_screen.py APK [--tap LABEL]... [--enter FIELD=TEXT]... [--then LABEL]... --until LABEL... [--seconds N] [--shot PNG]

Each second it reads the screen (uiautomator) and stops with success once every --until label is shown. Otherwise it taps
the first --tap label on screen, or fills the first --enter field on screen (tap, type, close the keyboard, then tap each
--then label; a field still shown ten seconds later is filled again). Labels match a view's text or content description exactly. Needs ANDROID_HOME (adb and apkanalyzer).
"""
import argparse
import html
import os
import re
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("apk")
    parser.add_argument("--tap", action="append", default=[])
    parser.add_argument("--enter", action="append", default=[], type=lambda value: tuple(value.split("=", 1)))
    parser.add_argument("--then", action="append", default=[])
    parser.add_argument("--until", action="append", required=True)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--shot")
    arguments = parser.parse_args()
    sdk = os.environ["ANDROID_HOME"]
    adb = os.path.join(sdk, "platform-tools", "adb")
    analyzer = os.path.join(sdk, "cmdline-tools", "latest", "bin", "apkanalyzer")
    package = subprocess.run([analyzer, "manifest", "application-id", arguments.apk], check=True, capture_output=True, text=True).stdout.strip()

    def device(*args):
        return subprocess.run([adb, *args], check=True, capture_output=True, text=True, timeout=300).stdout

    def screen():
        device("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        found = {}
        for text, description, bounds in re.findall(r'text="([^"]*)"[^>]*?content-desc="([^"]*)"[^>]*?bounds="([^"]*)"',
                                                    device("exec-out", "cat", "/sdcard/ui.xml")):
            x1, y1, x2, y2 = map(int, re.findall(r"\d+", bounds))
            for key in (text, description):
                if key:
                    found.setdefault(html.unescape(key), (str((x1 + x2) // 2), str((y1 + y2) // 2)))
        return found

    device("install", "-r", "-g", arguments.apk)
    device("shell", "am", "start", "-W", "-n", f"{package}/.MainActivity")
    deadline, found, entered = time.time() + arguments.seconds, {}, {}
    while not set(arguments.until) <= set(found):
        if time.time() > deadline:
            sys.exit(f"{', '.join(arguments.until)} not on screen within {arguments.seconds}s; saw {sorted(found)[:30]}")
        time.sleep(1)
        found = screen()
        label = next((label for label in arguments.tap if label in found), None)
        field = next(((name, value) for name, value in arguments.enter if name in found and time.time() - entered.get(name, 0) > 10), None)
        if label is not None:
            device("shell", "input", "tap", *found[label])
        elif field is not None:
            device("shell", "input", "tap", *found[field[0]])
            time.sleep(1)
            device("shell", "input", "text", field[1].replace(" ", "%s"))
            device("shell", "input", "keyevent", "111")
            time.sleep(1)
            entered[field[0]] = time.time()
            for then in arguments.then:
                now = screen()
                if then in now:
                    device("shell", "input", "tap", *now[then])
    if arguments.shot:
        with open(arguments.shot, "wb") as handle:
            subprocess.run([adb, "exec-out", "screencap", "-p"], stdout=handle, check=True, timeout=60)
    print("PASS " + ", ".join(arguments.until) + " on screen")


if __name__ == "__main__":
    main()

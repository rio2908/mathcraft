"""Register our native receiver after p4a generates the SDL2 manifest."""

from pathlib import Path
from xml.etree import ElementTree as ET


ANDROID_NS = "http://schemas.android.com/apk/res/android"
RECEIVER_NAME = "org.game.mathcraft.reminders.ReminderReceiver"


def add_reminder_receiver(manifest_path):
    ET.register_namespace("android", ANDROID_NS)
    manifest_path = Path(manifest_path)
    tree = ET.parse(manifest_path)
    application = tree.getroot().find("application")
    if application is None:
        raise ValueError("Android manifest has no application element")
    name_attribute = f"{{{ANDROID_NS}}}name"
    if not any(receiver.get(name_attribute) == RECEIVER_NAME for receiver in application.findall("receiver")):
        receiver = ET.SubElement(application, "receiver", {
            name_attribute: RECEIVER_NAME, f"{{{ANDROID_NS}}}exported": "false",
        })
        intent_filter = ET.SubElement(receiver, "intent-filter")
        for action in ("BOOT_COMPLETED", "TIME_SET", "TIMEZONE_CHANGED", "MY_PACKAGE_REPLACED"):
            ET.SubElement(intent_filter, "action", {name_attribute: f"android.intent.action.{action}"})
    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)


def after_apk_build(toolchain):
    dist = Path(toolchain.ctx.dist_dir) / toolchain.ctx.distribution.dist_dir
    add_reminder_receiver(dist / "src" / "main" / "AndroidManifest.xml")

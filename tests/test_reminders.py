import configparser
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

import game_reminders
import game_storage
from game_tasks import credit_activity_day, start_activity_challenge


ROOT = Path(__file__).resolve().parents[1]
JAVA_SOURCE = ROOT / "android/src/org/game/mathcraft/reminders"


class ReminderBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = game_reminders.AndroidChallengeReminders()
        self.native = Mock()
        self.native.notificationsAllowed.return_value = True
        self.context = object()
        self.platform_patch = patch.object(self.bridge, "_android", return_value=(self.native, self.context, 33))
        self.platform_patch.start()
        self.addCleanup(self.platform_patch.stop)
        environment = patch.dict(os.environ, {"ANDROID_ARGUMENT": "test"})
        environment.start()
        self.addCleanup(environment.stop)
        self.permissions = ModuleType("android.permissions")
        self.permissions.check_permission = Mock(return_value=False)
        self.permissions.request_permissions = Mock()
        self.ui_jobs = []
        runnable = ModuleType("android.runnable")
        runnable.run_on_ui_thread = lambda function: lambda: self.ui_jobs.append(function)
        modules = patch.dict("sys.modules", {
            "android": ModuleType("android"), "android.permissions": self.permissions,
            "android.runnable": runnable,
        })
        modules.start()
        self.addCleanup(modules.stop)

    def test_non_android_has_no_jni_or_permission_side_effects(self):
        with patch.dict(os.environ, {}, clear=True):
            self.bridge.sync({}, "save.json")
            self.bridge.resume()
            self.assertIn("Android", self.bridge.request_permission())
        self.bridge._android.assert_not_called()
        self.permissions.request_permissions.assert_not_called()

    def test_sync_only_when_challenge_state_changes(self):
        profiles = {"Настя": {"emeralds": 20}}
        start_activity_challenge(profiles["Настя"], "Осень", 2)
        self.bridge.sync(profiles, "save.json")
        self.native.configure.assert_called_once_with(self.context, os.path.abspath("save.json"))
        profiles["Настя"]["emeralds"] = 40
        profiles["Настя"]["marathon_elapsed_seconds"] = 100
        self.bridge.sync(profiles, "save.json")
        self.assertEqual(self.native.configure.call_count, 1)
        credit_activity_day(profiles["Настя"], "2026-10-16")
        self.bridge.sync(profiles, "save.json")
        self.assertEqual(self.native.configure.call_count, 2)
        credit_activity_day(profiles["Настя"], "2026-10-17")
        self.bridge.sync(profiles, "save.json")
        self.assertEqual(self.native.configure.call_count, 3)
        self.assertFalse(profiles["Настя"]["activity_challenge"]["active"])
        self.bridge.sync({}, "save.json")
        self.assertEqual(self.native.configure.call_count, 4)

    def test_sync_runs_after_successful_atomic_write_not_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            with patch.object(game_storage, "SAVE_FILE", str(path)), \
                    patch.object(game_storage, "challenge_reminders", self.bridge):
                profiles = {"Настя": {"emeralds": 42}}
                self.native.configure.side_effect = lambda context, name: self.assertEqual(
                    json.loads(Path(name).read_text(encoding="utf-8")), profiles)
                game_storage.save_data(profiles)
                self.native.configure.assert_called_once()
                self.native.configure.reset_mock()
                start_activity_challenge(profiles["Настя"], "Осень", 1)
                with patch.object(game_storage.os, "replace", side_effect=OSError("Disk full")):
                    game_storage.save_data(profiles)
                self.native.configure.assert_not_called()
                self.assertNotIn("activity_challenge", game_storage.load_data()["Настя"])

    def test_unavailable_native_class_cannot_break_a_save_and_is_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            with patch.object(game_storage, "SAVE_FILE", str(path)), \
                    patch.object(game_storage, "challenge_reminders", self.bridge):
                self.native.configure.side_effect = RuntimeError("Class not found")
                with self.assertLogs("game_reminders", level="WARNING"):
                    game_storage.save_data({"Настя": {"emeralds": 42}})
                self.assertEqual(game_storage.load_data()["Настя"]["emeralds"], 42)
                self.native.configure.side_effect = None
                game_storage.save_data({"Настя": {"emeralds": 42}})
                self.assertEqual(self.native.configure.call_count, 2)

    def test_android_13_permission_request_is_dispatched_to_ui_and_processed_once(self):
        self.assertIn("Разрешите", self.bridge.request_permission())
        self.permissions.request_permissions.assert_not_called()
        self.assertIn("Подтвердите", self.bridge.request_permission())
        self.assertEqual(len(self.ui_jobs), 1)
        self.ui_jobs.pop()()
        permissions, callback = self.permissions.request_permissions.call_args.args
        self.assertEqual(permissions, [game_reminders.POST_NOTIFICATIONS])
        callback(permissions, [True])
        self.native.refresh.assert_not_called()  # Callback must not schedule from the UI thread.
        self.assertIn("07:00 и 17:00", self.bridge.poll())
        self.native.refresh.assert_called_once_with(self.context)
        self.assertIsNone(self.bridge.poll())

    def test_denied_or_interrupted_permission_does_not_reprompt_automatically(self):
        for permissions, grants in (([game_reminders.POST_NOTIFICATIONS], [False]), ([], [])):
            with self.subTest(grants=grants):
                self.bridge.request_permission()
                self.ui_jobs.pop()()
                callback = self.permissions.request_permissions.call_args.args[1]
                callback(permissions, grants)
                self.assertIn("Без разрешения", self.bridge.poll())
                self.assertIsNone(self.bridge.poll())
                self.native.refresh.assert_not_called()

    def test_older_android_needs_no_runtime_permission_and_disabled_channel_is_explained(self):
        self.bridge._android.return_value = self.native, self.context, 28
        self.assertIn("07:00 и 17:00", self.bridge.request_permission())
        self.permissions.request_permissions.assert_not_called()
        self.native.notificationsAllowed.return_value = False
        self.assertIn("настройках телефона", self.bridge.request_permission())

    def test_permission_errors_release_pending_request(self):
        self.permissions.request_permissions.side_effect = RuntimeError("Activity unavailable")
        self.bridge.request_permission()
        self.ui_jobs.pop()()
        self.assertIn("Не удалось", self.bridge.poll())
        self.assertFalse(self.bridge._asking)

    def test_resume_rechecks_system_settings_without_asking_for_permission(self):
        self.bridge.resume()
        self.native.refresh.assert_called_once_with(self.context)
        self.permissions.request_permissions.assert_not_called()
        self.assertEqual(self.ui_jobs, [])


class ReminderBuildTests(unittest.TestCase):
    def test_manifest_hook_is_idempotent_and_registers_only_a_private_receiver(self):
        spec = importlib.util.spec_from_file_location("reminder_hook", ROOT / "android/p4a_hook.py")
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "src/main/AndroidManifest.xml"
            path.parent.mkdir(parents=True)
            path.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
                            '<application android:allowBackup="true"><activity android:name="Existing"/>'
                            '</application></manifest>', encoding="utf-8")
            toolchain = SimpleNamespace(ctx=SimpleNamespace(
                dist_dir=directory, distribution=SimpleNamespace(dist_dir=directory)))
            hook.after_apk_build(toolchain)
            hook.after_apk_build(toolchain)
            application = ET.parse(path).getroot().find("application")
            attribute = "{http://schemas.android.com/apk/res/android}"
            self.assertIsNotNone(application.find("activity"))
            self.assertEqual(application.get(attribute + "allowBackup"), "true")
            receivers = application.findall("receiver")
            self.assertEqual(len(receivers), 1)
            self.assertEqual(receivers[0].get(attribute + "exported"), "false")
            actions = {item.get(attribute + "name") for item in receivers[0].findall("intent-filter/action")}
            self.assertEqual(actions, {"android.intent.action." + action for action in (
                "BOOT_COMPLETED", "TIME_SET", "TIMEZONE_CHANGED", "MY_PACKAGE_REPLACED")})

    def test_android_build_includes_native_sources_and_required_permissions(self):
        config = configparser.ConfigParser()
        config.read(ROOT / "buildozer.spec", encoding="utf-8")
        self.assertTrue((ROOT / config["app"]["android.add_src"]).is_dir())
        self.assertTrue((ROOT / config["app"]["p4a.hook"]).is_file())
        permissions = config["app"]["android.permissions"]
        self.assertIn("android.permission.POST_NOTIFICATIONS", permissions)
        self.assertIn("android.permission.RECEIVE_BOOT_COMPLETED", permissions)
        self.assertNotIn("EXACT_ALARM", permissions)

    @unittest.skipUnless(os.environ.get("MATHCRAFT_ANDROID_JAR") and shutil.which("javac"),
                         "Set MATHCRAFT_ANDROID_JAR to an Android API 34 android.jar")
    def test_native_receiver_compiles_against_android_api(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([
                shutil.which("javac"), "-encoding", "UTF-8", "--release", "8",
                "-cp", os.environ["MATHCRAFT_ANDROID_JAR"], "-d", directory,
                *map(str, JAVA_SOURCE.glob("*.java")),
            ], capture_output=True, text=True, errors="replace", timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "JDK is not installed")
class NativeReminderPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        harness = Path(cls.directory.name) / "ReminderPolicyTest.java"
        harness.write_text('''
import java.text.SimpleDateFormat;
import java.util.TimeZone;
import org.game.mathcraft.reminders.ReminderPolicy;

public class ReminderPolicyTest {
    static final TimeZone ZONE = TimeZone.getTimeZone("Europe/Moscow");
    static long at(String time, TimeZone zone) throws Exception {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        format.setTimeZone(zone);
        return format.parse(time).getTime();
    }
    static void check(boolean condition) {
        if (!condition) { throw new AssertionError("Reminder policy regression"); }
    }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("calendar")) {
            check(ReminderPolicy.nextTime(at("2026-10-16 06:59", ZONE), 7, ZONE) == at("2026-10-16 07:00", ZONE));
            check(ReminderPolicy.nextTime(at("2026-10-16 07:00", ZONE), 7, ZONE) == at("2026-10-17 07:00", ZONE));
            check(ReminderPolicy.nextTime(at("2026-10-16 16:59", ZONE), 17, ZONE) == at("2026-10-16 17:00", ZONE));
            check(ReminderPolicy.nextTime(at("2026-10-16 17:01", ZONE), 17, ZONE) == at("2026-10-17 17:00", ZONE));
            check(ReminderPolicy.nextTime(at("2026-12-31 23:59", ZONE), 7, ZONE) == at("2027-01-01 07:00", ZONE));
            TimeZone dst = TimeZone.getTimeZone("America/New_York");
            long spring = at("2026-03-07 07:00", dst);
            long autumn = at("2026-10-31 07:00", dst);
            check(ReminderPolicy.nextTime(spring, 7, dst) - spring == 23 * 3600000L);
            check(ReminderPolicy.nextTime(autumn, 7, dst) - autumn == 25 * 3600000L);
        } else if (args[0].equals("delivery")) {
            long morning = at("2026-10-16 07:00", ZONE);
            long evening = at("2026-10-16 17:00", ZONE);
            check(ReminderPolicy.shouldNotify(true, "", "", "2026-10-16", 7, morning, ZONE));
            check(ReminderPolicy.shouldNotify(true, "", "", "2026-10-16", 17, evening, ZONE));
            check(!ReminderPolicy.shouldNotify(false, "", "", "2026-10-16", 7, morning, ZONE));
            check(!ReminderPolicy.shouldNotify(true, "2026-10-16", "", "2026-10-16", 17, evening, ZONE));
            check(!ReminderPolicy.shouldNotify(true, "", "2026-10-16", "2026-10-16", 7, morning, ZONE));
            check(!ReminderPolicy.shouldNotify(true, "", "", "2026-10-15", 7, morning, ZONE));
            check(!ReminderPolicy.shouldNotify(true, "", "", "2026-10-16", 7, evening, ZONE));
            check(!ReminderPolicy.shouldNotify(true, "", "", "2026-10-16", 17, at("2026-10-16 22:00", ZONE), ZONE));
            check(ReminderPolicy.shouldNotify(true, "2026-10-15", "2026-10-15", "2026-10-16", 7, morning, ZONE));
        } else if (args[0].equals("copy")) {
            for (int hour : new int[] {7, 17}) {
                String title = ReminderPolicy.title("Настя", hour);
                String body = ReminderPolicy.body("Осеннее приключение", hour);
                check(title.contains("Настя"));
                check(body.contains("Осеннее приключение") && body.contains("марафон"));
                for (String bad : new String[] {"должен", "штраф", "срочно", "пропустил", "стыд", "потеряешь"}) {
                    check(!body.contains(bad));
                }
            }
        } else { throw new AssertionError("Unknown suite"); }
    }
}
''', encoding="utf-8")
        result = subprocess.run([
            shutil.which("javac"), "-encoding", "UTF-8", "--release", "8",
            "-d", cls.directory.name, str(JAVA_SOURCE / "ReminderPolicy.java"), str(harness),
        ], capture_output=True, text=True, errors="replace", timeout=40)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def run_policy(self, suite):
        result = subprocess.run([
            shutil.which("java"), "-Dfile.encoding=UTF-8", "-cp", self.directory.name,
            "ReminderPolicyTest", suite,
        ], capture_output=True, text=True, errors="replace", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_local_schedule_boundaries_year_change_and_daylight_saving(self):
        self.run_policy("calendar")

    def test_completed_day_inactive_challenge_duplicates_and_late_alarms(self):
        self.run_policy("delivery")

    def test_child_friendly_copy_names_challenge_and_explains_marathon(self):
        self.run_policy("copy")

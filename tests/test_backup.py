"""Exercise the Android bridge using real files and a strict fake Java API."""

import json
import os
from pathlib import Path
import tempfile
from threading import Event, get_ident
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import game_backup
import game_storage


class Bundle:
    def __init__(self):
        self.strings = {}

    def putString(self, key, value):
        assert isinstance(value, str)
        self.strings[key] = value


class Intent:
    ACTION_CREATE_DOCUMENT = "create"
    ACTION_OPEN_DOCUMENT = "open"
    CATEGORY_OPENABLE = "openable"
    EXTRA_TITLE = "title"

    def __init__(self, action):
        self.action = action
        self.extras = None
        self.uri = None
        self.categories = []

    def setType(self, mime):
        self.mime = mime

    def putExtra(self, *args):
        raise AssertionError("Ambiguous putExtra overload must not be used for the filename")

    def putExtras(self, extras):
        self.extras = extras

    def addCategory(self, category):
        self.categories.append(category)

    def getData(self):
        return self.uri


class Descriptor:
    def __init__(self, fd):
        self.fd = fd
        self.detached = False
        self.closed = False

    def detachFd(self):
        self.detached = True
        return self.fd

    def close(self):
        self.closed = True
        if not self.detached:
            os.close(self.fd)


class BackupPickerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.save = self.root / "save.json"
        self.last = self.root / "last.txt"
        self.document = self.root / "backup.json"
        self.entered = Event()
        self.release = Event()
        self.release.set()
        self.descriptors = []
        self.opens = []
        self.open_error = None
        self.ui_jobs = []
        self.launches = []

        def open_descriptor(uri, mode):
            self.opens.append((uri, mode, get_ident()))
            self.entered.set()
            if not self.release.wait(5):
                raise OSError("Test provider was not released")
            if self.open_error:
                raise self.open_error
            flags = os.O_RDONLY if mode == "r" else os.O_WRONLY | os.O_CREAT
            if mode == "wt":
                flags |= os.O_TRUNC
            flags |= getattr(os, "O_BINARY", 0)
            descriptor = Descriptor(os.open(uri, flags))
            self.descriptors.append(descriptor)
            return descriptor

        def launch(intent, request_code):
            self.launches.append((intent, request_code))

        self.current = SimpleNamespace(
            startActivityForResult=Mock(side_effect=launch),
            getContentResolver=lambda: SimpleNamespace(openFileDescriptor=open_descriptor),
        )
        self.activity = SimpleNamespace(bind=Mock())
        android = ModuleType("android")
        android.activity = self.activity
        runnable = ModuleType("android.runnable")
        runnable.run_on_ui_thread = lambda function: lambda *args: self.ui_jobs.append((function, args))
        jnius = ModuleType("jnius")
        classes = {
            "org.kivy.android.PythonActivity": SimpleNamespace(mActivity=self.current),
            "android.content.Intent": Intent,
            "android.os.Bundle": Bundle,
        }
        jnius.autoclass = classes.__getitem__
        for active_patch in (
            patch.dict("sys.modules", {"android": android, "android.runnable": runnable, "jnius": jnius}),
            patch.object(game_storage, "SAVE_FILE", str(self.save)),
            patch.object(game_storage, "LAST_PLAYER_FILE", str(self.last)),
        ):
            active_patch.start()
            self.addCleanup(active_patch.stop)
        self.picker = game_backup.AndroidBackupPicker()
        self.profiles = {
            "Настя": {"emeralds": 300, "task_num": 27, "game_history": [{"errors": 2}],
                      "activity_challenge": {"name": "Осень", "count": 2, "active": True}},
            "Ксения": {"emeralds": 123},
        }
        game_storage.save_data(self.profiles)
        game_storage.set_last_player("Настя")

    def launch(self, export):
        self.assertTrue(self.picker.start(export))
        # startActivityForResult must be scheduled, not called by the game loop.
        self.assertEqual(len(self.ui_jobs), 1)
        function, args = self.ui_jobs.pop()
        function(*args)
        return self.launches[-1]

    def select(self, request):
        response = Intent("result")
        response.uri = str(self.document)
        self.picker._on_activity_result(request, -1, response)
        return self.picker.poll()

    def finish(self, initial=None):
        if initial is not None:
            return initial
        worker = self.picker._worker
        self.assertIsNotNone(worker)
        worker.join(3)
        self.assertFalse(worker.is_alive(), "Backup transfer did not finish")
        result = self.picker.poll()
        self.assertIsNotNone(result)
        self.assertIsNone(self.picker.pending)
        self.assertEqual(self.picker.status, "")
        self.assertIsNone(self.picker.poll(), "Each result must be delivered only once")
        return result

    def test_export_has_string_filename_and_nonempty_valid_utf8_json(self):
        intent, request = self.launch(True)
        self.assertEqual(intent.action, Intent.ACTION_CREATE_DOCUMENT)
        self.assertEqual(intent.mime, "application/json")
        self.assertEqual(intent.extras.strings[Intent.EXTRA_TITLE], "MathCraft-backup.json")
        self.assertIn(Intent.CATEGORY_OPENABLE, intent.categories)
        # Existing longer documents must be truncated, or JSON has trailing garbage.
        self.document.write_bytes(b"x" * 10000)
        notice, restored = self.finish(self.select(request))
        self.assertIn("Копия сохранена", notice)
        self.assertFalse(restored)
        content = self.document.read_bytes()
        self.assertGreater(len(content), 0)
        document = json.loads(content.decode("utf-8"))
        self.assertEqual(document["profiles"], self.profiles)
        self.assertEqual(document["last_player"], "Настя")
        self.assertEqual(self.opens[0][1], "wt")
        self.assertNotEqual(self.opens[0][2], get_ident())
        self.assertTrue(self.descriptors[0].closed)
        with self.assertRaises(OSError):
            os.fstat(self.descriptors[0].fd)

    def test_export_import_roundtrip_after_reinstall_and_duplicate_import(self):
        _, request = self.launch(True)
        self.finish(self.select(request))
        self.save.unlink()
        self.last.unlink()
        intent, request = self.launch(False)
        self.assertEqual(intent.action, Intent.ACTION_OPEN_DOCUMENT)
        self.assertEqual(intent.mime, "*/*")
        notice, restored = self.finish(self.select(request))
        self.assertTrue(restored)
        self.assertIn("2", notice)
        self.assertEqual(game_storage.load_data(), self.profiles)
        self.assertEqual(game_storage.get_last_player(), "Настя")
        game_storage.save_data({**self.profiles, "Настя": {"emeralds": 900}})
        _, request = self.launch(False)
        notice, restored = self.finish(self.select(request))
        self.assertFalse(restored)
        self.assertIn("не перезаписан", notice)
        self.assertEqual(game_storage.load_data()["Настя"]["emeralds"], 900)
        self.activity.bind.assert_called_once()

    def test_slow_provider_does_not_block_poll_and_rejects_duplicate_start(self):
        self.document.write_bytes(game_storage.make_backup_bytes())
        self.release.clear()
        try:
            _, request = self.launch(False)
            self.assertIsNone(self.select(request))
            self.assertTrue(self.entered.wait(1))
            self.assertIsNone(self.picker.poll())
            self.assertIn("Читаем", self.picker.status)
            self.assertFalse(self.picker.start(True))
        finally:
            self.release.set()
        self.finish()

    def test_timeout_discards_late_import_without_changing_profiles(self):
        self.document.write_bytes(game_storage.make_backup_bytes())
        self.save.unlink()
        self.release.clear()
        try:
            _, request = self.launch(False)
            with patch.object(game_backup, "monotonic", return_value=100):
                self.assertIsNone(self.select(request))
            self.assertTrue(self.entered.wait(1))
            worker = self.picker._worker
            with patch.object(game_backup, "monotonic", return_value=131):
                notice, restored = self.picker.poll()
            self.assertIn("не отвечает", notice)
            self.assertFalse(restored)
            self.assertIsNone(self.picker.pending)
        finally:
            self.release.set()
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertIsNone(self.picker.poll())
        self.assertFalse(self.save.exists(), "Timed-out imports must not be applied later")

    def test_cancel_and_unrelated_callback_do_not_leave_picker_busy(self):
        _, request = self.launch(True)
        self.picker._on_activity_result(9999, -1, None)
        self.assertIsNone(self.picker.poll())
        self.assertEqual(self.picker.pending, request)
        self.picker._on_activity_result(request, 0, None)
        self.assertIn("отменён", self.picker.poll()[0])
        self.assertIsNone(self.picker.pending)
        self.assertEqual(self.opens, [])
        self.assertTrue(self.picker.start(False))

    def test_launch_exception_is_reported_after_ui_dispatch_and_allows_retry(self):
        self.current.startActivityForResult.side_effect = RuntimeError("No document picker")
        self.assertTrue(self.picker.start(True))
        function, args = self.ui_jobs.pop()
        function(*args)
        notice, restored = self.picker.poll()
        self.assertIn("No document picker", notice)
        self.assertFalse(restored)
        self.assertIsNone(self.picker.pending)
        self.assertTrue(self.picker.start(False))

    def test_provider_errors_and_missing_uri_leave_local_save_untouched(self):
        before = self.save.read_bytes()
        self.open_error = PermissionError("Access denied")
        _, request = self.launch(False)
        notice, restored = self.finish(self.select(request))
        self.assertIn("Access denied", notice)
        self.assertFalse(restored)
        self.assertEqual(self.save.read_bytes(), before)
        self.assertTrue(self.picker.start(False))
        self.picker._on_activity_result(game_backup.IMPORT_REQUEST, -1, Intent("result"))
        self.assertIn("Файл не выбран", self.picker.poll()[0])
        self.assertIsNone(self.picker.pending)

    def test_empty_corrupt_and_oversized_import_do_not_change_save(self):
        before = self.save.read_bytes()
        for content, message in ((b"", "пуст"), (b"not json", "Не удалось прочитать"),
                                 (b"x" * (game_storage.MAX_BACKUP_BYTES + 1), "слишком большой")):
            with self.subTest(message=message):
                self.document.write_bytes(content)
                _, request = self.launch(False)
                notice, restored = self.finish(self.select(request))
                self.assertIn(message, notice)
                self.assertFalse(restored)
                self.assertEqual(self.save.read_bytes(), before)

    def test_failed_stream_creation_closes_detached_fd(self):
        _, request = self.launch(True)
        with patch.object(game_backup.os, "fdopen", side_effect=OSError("Cannot wrap fd")):
            notice, restored = self.finish(self.select(request))
        self.assertIn("Cannot wrap fd", notice)
        self.assertFalse(restored)
        self.assertTrue(self.descriptors[0].closed)
        with self.assertRaises(OSError):
            os.fstat(self.descriptors[0].fd)

    def test_write_flush_and_close_errors_never_report_success(self):
        for failure in ("write", "flush", "close"):
            with self.subTest(failure=failure):
                original_fdopen = os.fdopen

                def wrap(fd, mode):
                    stream = original_fdopen(fd, mode)
                    proxy = Mock(wraps=stream)
                    proxy.__enter__ = Mock(return_value=proxy)

                    def close(*args):
                        stream.close()
                        if failure == "close":
                            raise OSError("close failed")

                    proxy.__exit__ = Mock(side_effect=close)
                    if failure != "close":
                        getattr(proxy, failure).side_effect = OSError(failure + " failed")
                    return proxy

                _, request = self.launch(True)
                with patch.object(game_backup.os, "fdopen", side_effect=wrap):
                    notice, restored = self.finish(self.select(request))
                self.assertIn(failure + " failed", notice)
                self.assertNotIn("Копия сохранена", notice)
                self.assertFalse(restored)
                with self.assertRaises(OSError):
                    os.fstat(self.descriptors[-1].fd)

    def test_no_players_fails_before_creating_document(self):
        self.save.unlink()
        with self.assertRaises(ValueError):
            self.picker.start(True)
        self.assertIsNone(self.picker.pending)
        self.assertEqual(self.ui_jobs, [])
        self.assertEqual(self.launches, [])

"""Android document-picker bridge for portable save backups.

The picker stores the copy outside app-private storage, so uninstalling the
APK does not remove it. Android-specific imports are delayed until requested.
"""

import os
from queue import Empty, Queue
from threading import Thread
from time import monotonic

from game_storage import MAX_BACKUP_BYTES, make_backup_bytes, restore_backup_bytes


EXPORT_REQUEST = 4101
IMPORT_REQUEST = 4102
TRANSFER_TIMEOUT_SECONDS = 30
BACKUP_FILENAME = "MathCraft-backup.json"


class AndroidBackupPicker:
    def __init__(self):
        self.pending = None
        self._bound = False
        self._payload = None
        self._operation = None
        self._events = Queue()
        self._worker = None
        self._deadline = None
        self._launch_on_ui = None

    @property
    def status(self):
        if self.pending is None:
            return ""
        if self._worker is None:
            return "Выберите файл в системном окне Android."
        if self.pending == EXPORT_REQUEST:
            return "Сохраняем копию… Не закрывайте приложение."
        return "Читаем копию… Игра не заблокирована."

    def _android(self):
        from android import activity
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        return activity, PythonActivity.mActivity, Intent

    def _on_activity_result(self, request_code, result_code, intent):
        if request_code == self.pending and self._worker is None:
            self._events.put((self._operation, "activity", (result_code, intent)))

    def _launch(self, intent, request_code, operation):
        """Runs on Android's UI thread, not the SDL/Pygame thread."""
        try:
            _, current_activity, _ = self._android()
            current_activity.startActivityForResult(intent, request_code)
        except Exception as error:
            self._events.put((operation, "error", str(error)))

    def start(self, export):
        if self.pending is not None:
            return False
        # Validate the snapshot before Android creates an otherwise empty file.
        payload = make_backup_bytes() if export else None
        activity, _, Intent = self._android()
        if not self._bound:
            activity.bind(on_activity_result=self._on_activity_result)
            self._bound = True
        if export:
            from jnius import autoclass

            intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
            intent.setType("application/json")
            # putExtra has String/CharSequence/char[] overloads. A Python str
            # can select the array overload, which DocumentsUI calls invalid.
            extras = autoclass("android.os.Bundle")()
            extras.putString(Intent.EXTRA_TITLE, BACKUP_FILENAME)
            intent.putExtras(extras)
            request_code = EXPORT_REQUEST
        else:
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            # Some providers label JSON as text/plain or octet-stream. Validate
            # the contents ourselves instead of hiding those valid backups.
            intent.setType("*/*")
            request_code = IMPORT_REQUEST
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        self.pending = request_code
        self._payload = payload
        self._operation = object()
        try:
            if self._launch_on_ui is None:
                from android.runnable import run_on_ui_thread

                self._launch_on_ui = run_on_ui_thread(self._launch)
            self._launch_on_ui(intent, request_code, self._operation)
        except Exception:
            self._clear()
            raise
        return True

    def _clear(self):
        self.pending = None
        self._payload = None
        self._operation = None
        self._worker = None
        self._deadline = None

    def _transfer(self, operation, request_code, uri, payload):
        """Only document I/O runs here; local saves are merged by poll()."""
        try:
            _, current_activity, _ = self._android()
            resolver = current_activity.getContentResolver()
            mode = "wt" if request_code == EXPORT_REQUEST else "r"
            descriptor = resolver.openFileDescriptor(uri, mode)
            if descriptor is None:
                raise OSError("Не удалось открыть файл.")
            try:
                if operation is not self._operation:
                    return
                fd = descriptor.detachFd()
                try:
                    backup_file = os.fdopen(fd, "wb" if request_code == EXPORT_REQUEST else "rb")
                except Exception:
                    os.close(fd)
                    raise
                with backup_file:
                    if request_code == EXPORT_REQUEST:
                        if backup_file.write(payload) != len(payload):
                            raise OSError("Копия записана не полностью.")
                        backup_file.flush()
                        content = None
                    else:
                        content = backup_file.read(MAX_BACKUP_BYTES + 1)
            finally:
                descriptor.close()
            # In particular, do not report success before flush AND close.
            self._events.put((operation, "transferred", content))
        except Exception as error:
            self._events.put((operation, "error", str(error)))

    def poll(self):
        """Consume callbacks without blocking a frame on a document provider."""
        try:
            while True:
                try:
                    operation, kind, value = self._events.get_nowait()
                except Empty:
                    break
                if operation is not self._operation:
                    continue
                if kind == "error":
                    raise OSError(value)
                if kind == "activity":
                    if self._worker is not None:
                        continue
                    result_code, intent = value
                    if result_code != -1 or intent is None:
                        self._clear()
                        return "Выбор файла отменён.", False
                    uri = intent.getData()
                    if uri is None:
                        raise ValueError("Файл не выбран.")
                    self._worker = Thread(
                        target=self._transfer,
                        args=(operation, self.pending, uri, self._payload),
                        name="MathCraft-backup", daemon=True,
                    )
                    self._deadline = monotonic() + TRANSFER_TIMEOUT_SECONDS
                    self._worker.start()
                elif kind == "transferred":
                    request_code = self.pending
                    self._clear()
                    if request_code == EXPORT_REQUEST:
                        return "Копия сохранена. Не удаляйте её перед переустановкой.", False
                    added, skipped = restore_backup_bytes(value)
                    if added:
                        return f"Восстановлено игроков: {added}. Уже были: {skipped}.", True
                    return f"Все {skipped} игроки уже есть. Прогресс не перезаписан.", False
            if self._deadline is not None and monotonic() >= self._deadline:
                self._clear()
                return "Файловое хранилище не отвечает. Повторите с файлом в Загрузках.", False
        except Exception as error:
            self._clear()
            return f"Ошибка копии: {error}", False
        return None

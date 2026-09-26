"""Android document-picker bridge for portable save backups.

The picker stores the copy outside app-private storage, so uninstalling the
APK does not remove it. Android-specific imports are delayed until requested.
"""

import os

from game_storage import MAX_BACKUP_BYTES, make_backup_bytes, restore_backup_bytes


EXPORT_REQUEST = 4101
IMPORT_REQUEST = 4102


class AndroidBackupPicker:
    def __init__(self):
        self.pending = None
        self.result = None
        self._bound = False

    def _android(self):
        from android import activity
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        return activity, PythonActivity.mActivity, Intent

    def _on_activity_result(self, request_code, result_code, intent):
        if request_code in (EXPORT_REQUEST, IMPORT_REQUEST):
            self.result = (request_code, result_code, intent)

    def start(self, export):
        if self.pending is not None:
            return False
        activity, current_activity, Intent = self._android()
        if not self._bound:
            activity.bind(on_activity_result=self._on_activity_result)
            self._bound = True
        if export:
            payload = make_backup_bytes()
            intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
            intent.setType("application/json")
            intent.putExtra(Intent.EXTRA_TITLE, "MathCraft-backup.json")
            request_code = EXPORT_REQUEST
        else:
            payload = None
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.setType("application/json")
            request_code = IMPORT_REQUEST
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        self.pending = payload if export else True
        try:
            current_activity.startActivityForResult(intent, request_code)
        except Exception:
            self.pending = None
            raise
        return True

    def poll(self):
        if self.result is None:
            return None
        request_code, result_code, intent = self.result
        self.result = None
        payload = self.pending
        self.pending = None
        if result_code != -1 or intent is None:
            return "Выбор файла отменён.", False
        try:
            _, current_activity, _ = self._android()
            uri = intent.getData()
            if uri is None:
                raise ValueError("Файл не выбран.")
            resolver = current_activity.getContentResolver()
            mode = "w" if request_code == EXPORT_REQUEST else "r"
            descriptor = resolver.openFileDescriptor(uri, mode)
            if descriptor is None:
                raise OSError("Не удалось открыть файл.")
            fd = descriptor.detachFd()
            if request_code == EXPORT_REQUEST:
                with os.fdopen(fd, "wb") as backup_file:
                    backup_file.write(payload)
                return "Копия сохранена. Не удаляйте её перед переустановкой.", False
            with os.fdopen(fd, "rb") as backup_file:
                content = backup_file.read(MAX_BACKUP_BYTES + 1)
            added, skipped = restore_backup_bytes(content)
            if added:
                return f"Восстановлено игроков: {added}. Уже были: {skipped}.", True
            return f"Все {skipped} игроки уже есть. Прогресс не перезаписан.", False
        except Exception as error:
            return f"Ошибка копии: {error}", False

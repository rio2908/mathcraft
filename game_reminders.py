"""Optional Android bridge; reminders themselves run in a native receiver."""

import logging
import os
from queue import Empty, SimpleQueue


POST_NOTIFICATIONS = "android.permission.POST_NOTIFICATIONS"


class AndroidChallengeReminders:
    def __init__(self):
        self._signature = None
        self._platform = None
        self._asking = False
        self._request_on_ui = None
        self._results = SimpleQueue()
        self._last_error = None

    @staticmethod
    def available():
        return "ANDROID_ARGUMENT" in os.environ

    def _android(self):
        if self._platform is None:
            from jnius import autoclass

            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            context = activity.getApplicationContext()
            native = autoclass("org.game.mathcraft.reminders.ChallengeReminders")
            api = int(autoclass("android.os.Build$VERSION").SDK_INT)
            self._platform = native, context, api
        return self._platform

    def sync(self, profiles, save_path):
        """Called only after a successful save; ignore ordinary score/timer updates."""
        if not self.available():
            return
        try:
            challenges = []
            for name, profile in profiles.items():
                challenge = profile.get("activity_challenge") if isinstance(profile, dict) else None
                challenge = challenge if isinstance(challenge, dict) else {}
                challenges.append((name, bool(challenge.get("active")),
                                   challenge.get("name", ""), challenge.get("last_date")))
            signature = (os.path.abspath(save_path), tuple(sorted(challenges)))
            if signature == self._signature:
                return
            native, context, _ = self._android()
            native.configure(context, signature[0])
            self._signature = signature
            self._last_error = None
        except Exception as error:
            # A notification failure must never make a saved marathon look unsaved.
            message = str(error)
            if message != self._last_error:
                logging.getLogger(__name__).warning("Android reminders unavailable: %s", message)
            self._last_error = message

    def _on_permission(self, permissions, grants):
        granted = any(permission == POST_NOTIFICATIONS and bool(grant)
                      for permission, grant in zip(permissions, grants))
        self._results.put(("permission", granted))

    def resume(self):
        """Recheck OS/channel settings when returning from Android settings."""
        if not self.available():
            return
        try:
            native, context, _ = self._android()
            native.refresh(context)
        except Exception as error:
            message = str(error)
            if message != self._last_error:
                logging.getLogger(__name__).warning("Android reminders unavailable: %s", message)
            self._last_error = message

    def _request(self):
        try:
            from android.permissions import request_permissions

            request_permissions([POST_NOTIFICATIONS], self._on_permission)
        except Exception as error:
            self._results.put(("error", str(error)))

    def _ready_message(self):
        native, context, _ = self._android()
        native.refresh(context)
        if native.notificationsAllowed(context):
            return "Напомним в 07:00 и 17:00, если день ещё не зачтён."
        return "Включите уведомления MathCraft в настройках телефона."

    def request_permission(self):
        """Only call after a parent's gesture, not automatically every launch."""
        if not self.available():
            return "Напоминания доступны в Android-приложении."
        if self._asking:
            return "Подтвердите разрешение в системном окне."
        try:
            _, _, api = self._android()
            if api >= 33:
                from android.permissions import check_permission

                if not check_permission(POST_NOTIFICATIONS):
                    from android.runnable import run_on_ui_thread

                    self._asking = True
                    if self._request_on_ui is None:
                        self._request_on_ui = run_on_ui_thread(self._request)
                    self._request_on_ui()
                    return "Разрешите уведомления в системном окне Android."
            return self._ready_message()
        except Exception:
            self._asking = False
            return "Не удалось включить напоминания. Попробуйте ещё раз."

    def poll(self):
        try:
            kind, value = self._results.get_nowait()
        except Empty:
            return None
        # p4a v2024.01.21 keeps every completed permission callback forever.
        # Release only our own entries, never callbacks belonging to other code.
        # Do this on the game thread, after the UI callback has returned.
        try:
            from android.permissions import _RequestPermissionsManager
        except ImportError:
            pass  # Other p4a versions (or desktop test doubles) may not expose it.
        else:
            callbacks = getattr(_RequestPermissionsManager, "_callbacks", None)
            if isinstance(callbacks, dict):
                for request, callback in tuple(callbacks.items()):
                    if callback == self._on_permission:
                        callbacks.pop(request, None)
        self._asking = False
        if kind == "error":
            return "Не удалось запросить разрешение на уведомления."
        if not value:
            return "Без разрешения напоминаний не будет. Игра доступна."
        try:
            return self._ready_message()
        except Exception:
            return "Не удалось включить напоминания. Попробуйте ещё раз."


challenge_reminders = AndroidChallengeReminders()

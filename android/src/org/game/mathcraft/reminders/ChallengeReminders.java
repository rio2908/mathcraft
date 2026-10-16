package org.game.mathcraft.reminders;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.drawable.Icon;
import android.os.Build;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;
import java.util.TimeZone;

import org.json.JSONObject;

/** Uses only native Android APIs: no running Python process or foreground service required. */
public final class ChallengeReminders {
    static final String ACTION = "org.game.mathcraft.CHALLENGE_REMINDER";
    private static final String CHANNEL = "mathcraft_challenge";
    private static final String PREFS = "mathcraft_reminders";
    private static final int NOTIFICATION_ID = 1;
    private static final int MAX_SAVE_BYTES = 16 * 1024 * 1024;

    private ChallengeReminders() { }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static boolean notificationsAllowed(Context context) {
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(
                "android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) {
            return false;
        }
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null || !manager.areNotificationsEnabled()) {
            return false;
        }
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = manager.getNotificationChannel(CHANNEL);
            if (channel != null && channel.getImportance() == NotificationManager.IMPORTANCE_NONE) {
                return false;
            }
        }
        return true;
    }

    public static synchronized void configure(Context context, String savePath) {
        // The path is supplied by Python once its app-private working directory is known.
        prefs(context).edit().putString("save_path", savePath).apply();
        refresh(context);
    }

    private static JSONObject readProfiles(Context context) throws Exception {
        String path = prefs(context).getString("save_path", "");
        if (path.isEmpty()) {
            return new JSONObject();
        }
        File file = new File(path);
        String root = context.getFilesDir().getCanonicalPath() + File.separator;
        if (!file.getCanonicalPath().startsWith(root)) {
            throw new SecurityException("Save must be inside app-private files");
        }
        if (!file.exists()) {
            return new JSONObject();
        }
        try (FileInputStream input = new FileInputStream(file);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) {
                if (output.size() + count > MAX_SAVE_BYTES) {
                    throw new IllegalArgumentException("Save is too large");
                }
                output.write(buffer, 0, count);
            }
            return new JSONObject(new String(output.toByteArray(), StandardCharsets.UTF_8));
        }
    }

    private static PendingIntent alarmIntent(Context context, int hour, String day) {
        Intent intent = new Intent(context, ReminderReceiver.class).setAction(ACTION);
        intent.putExtra("hour", hour);
        intent.putExtra("day", day);
        return PendingIntent.getBroadcast(context, hour, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    public static synchronized void refresh(Context context) {
        try {
            refresh(context, readProfiles(context));
        } catch (Exception error) {
            // Do not erase existing alarms because of an unreadable save.
            Log.w("MathCraftReminders", "Cannot refresh reminders", error);
        }
    }

    private static void refresh(Context context, JSONObject profiles) throws Exception {
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        SharedPreferences preferences = prefs(context);
        Set<String> activeNames = new HashSet<String>();
        String today = ReminderPolicy.day(System.currentTimeMillis(), TimeZone.getDefault());
        Iterator<String> names = profiles.keys();
        while (names.hasNext()) {
            String name = names.next();
            JSONObject profile = profiles.optJSONObject(name);
            JSONObject challenge = profile == null ? null : profile.optJSONObject("activity_challenge");
            if (challenge != null && challenge.optBoolean("active", false)) {
                activeNames.add(name);
                if (today.equals(challenge.optString("last_date")) && manager != null) {
                    manager.cancel(name, NOTIFICATION_ID);
                }
            }
        }
        Set<String> previous = preferences.getStringSet("active_names", new HashSet<String>());
        for (String name : previous) {
            if (!activeNames.contains(name) && manager != null) {
                manager.cancel(name, NOTIFICATION_ID);
            }
        }
        preferences.edit().putStringSet("active_names", activeNames).apply();
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms == null) {
            return;
        }
        for (int hour : new int[] {7, 17}) {
            long next = ReminderPolicy.nextTime(System.currentTimeMillis(), hour, TimeZone.getDefault());
            PendingIntent alarm = alarmIntent(context, hour, ReminderPolicy.day(next, TimeZone.getDefault()));
            if (activeNames.isEmpty() || !notificationsAllowed(context)) {
                alarms.cancel(alarm);
            } else {
                // Inexact by design: no restricted exact-alarm permission for a children's game.
                alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, next, alarm);
            }
        }
    }

    private static Icon smallIcon() {
        Bitmap bitmap = Bitmap.createBitmap(24, 24, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        Paint paint = new Paint();
        paint.setColor(Color.WHITE);
        Path diamond = new Path();
        diamond.moveTo(12, 2);
        diamond.lineTo(21, 10);
        diamond.lineTo(21, 15);
        diamond.lineTo(12, 23);
        diamond.lineTo(3, 15);
        diamond.lineTo(3, 10);
        diamond.close();
        canvas.drawPath(diamond, paint);
        return Icon.createWithBitmap(bitmap);
    }

    private static void notifyPlayer(Context context, String name, String challenge, int hour) {
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) {
            return;
        }
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(CHANNEL,
                "Напоминания о челлендже", NotificationManager.IMPORTANCE_DEFAULT);
            channel.setDescription("Добрые напоминания в 07:00 и 17:00, если день ещё не зачтён");
            manager.createNotificationChannel(channel);
        }
        String body = ReminderPolicy.body(challenge, hour);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
            ? new Notification.Builder(context, CHANNEL) : new Notification.Builder(context);
        builder.setSmallIcon(smallIcon()).setContentTitle(ReminderPolicy.title(name, hour))
            .setContentText(body).setStyle(new Notification.BigTextStyle().bigText(body))
            .setAutoCancel(true).setVisibility(Notification.VISIBILITY_PRIVATE)
            .setCategory(Notification.CATEGORY_REMINDER).setColor(Color.rgb(35, 175, 60));
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            builder.setContentIntent(PendingIntent.getActivity(context, 0, launch,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE));
        }
        // Replace this player's morning card instead of stacking another one in the evening.
        manager.notify(name, NOTIFICATION_ID, builder.build());
    }

    public static synchronized void handle(Context context, Intent intent) {
        try {
            JSONObject profiles = readProfiles(context);
            if (ACTION.equals(intent.getAction()) && notificationsAllowed(context)) {
                int hour = intent.getIntExtra("hour", -1);
                String scheduledDay = intent.getStringExtra("day");
                long now = System.currentTimeMillis();
                TimeZone zone = TimeZone.getDefault();
                SharedPreferences preferences = prefs(context);
                Iterator<String> names = profiles.keys();
                while (names.hasNext()) {
                    String name = names.next();
                    JSONObject profile = profiles.optJSONObject(name);
                    JSONObject challenge = profile == null ? null : profile.optJSONObject("activity_challenge");
                    if (challenge == null) {
                        continue;
                    }
                    String sentKey = "sent_" + hour + "_" + name;
                    if (ReminderPolicy.shouldNotify(challenge.optBoolean("active", false),
                            challenge.optString("last_date"), preferences.getString(sentKey, ""),
                            scheduledDay, hour, now, zone)) {
                        notifyPlayer(context, name, challenge.optString("name", "Мой челлендж"), hour);
                        preferences.edit().putString(sentKey, ReminderPolicy.day(now, zone)).commit();
                    }
                }
            }
            refresh(context, profiles);
        } catch (Exception error) {
            Log.w("MathCraftReminders", "Cannot deliver reminder", error);
            refresh(context);
        }
    }
}

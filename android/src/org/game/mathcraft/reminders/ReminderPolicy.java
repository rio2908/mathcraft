package org.game.mathcraft.reminders;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Locale;
import java.util.TimeZone;

/** Calendar and child-facing copy, independent of Android for JVM tests. */
public final class ReminderPolicy {
    private ReminderPolicy() { }

    public static String day(long millis, TimeZone zone) {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd", Locale.ROOT);
        format.setTimeZone(zone);
        return format.format(millis);
    }

    public static long nextTime(long now, int hour, TimeZone zone) {
        Calendar next = Calendar.getInstance(zone);
        next.setTimeInMillis(now);
        next.set(Calendar.HOUR_OF_DAY, hour);
        next.set(Calendar.MINUTE, 0);
        next.set(Calendar.SECOND, 0);
        next.set(Calendar.MILLISECOND, 0);
        if (next.getTimeInMillis() <= now) {
            next.add(Calendar.DAY_OF_YEAR, 1);
        }
        return next.getTimeInMillis();
    }

    public static boolean shouldNotify(boolean active, String lastDate, String sentDate,
                                       String scheduledDay, int hour, long now, TimeZone zone) {
        String today = day(now, zone);
        Calendar clock = Calendar.getInstance(zone);
        clock.setTimeInMillis(now);
        int currentHour = clock.get(Calendar.HOUR_OF_DAY);
        // Never deliver an old alarm at night or a delayed morning reminder in the evening.
        return (hour == 7 || hour == 17) && active && !today.equals(lastDate)
            && !today.equals(sentDate) && today.equals(scheduledDay)
            && currentHour >= hour && currentHour < hour + 2;
    }

    public static String title(String player, int hour) {
        return hour == 7 ? "Доброе утро, " + player + "!" : player + ", время приключений?";
    }

    public static String body(String challenge, int hour) {
        if (hour == 7) {
            return "Новый день — новое приключение! Пройди марафон в MathCraft, "
                + "чтобы сделать шаг в челлендже «" + challenge + "». Играй, когда будет удобно!";
        }
        return "Сегодня ещё можно сделать шаг в челлендже «" + challenge
            + "»: пройти марафон и победить Дракона. Если есть время и настроение — вперёд!";
    }
}

package org.game.mathcraft.reminders;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class ReminderReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(final Context context, final Intent intent) {
        final PendingResult result = goAsync();
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    ChallengeReminders.handle(context.getApplicationContext(), intent);
                } finally {
                    result.finish();
                }
            }
        }, "MathCraft-reminder").start();
    }
}

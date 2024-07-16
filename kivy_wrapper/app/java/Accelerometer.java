package org.rss;

import org.kivy.android.PythonActivity;
import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import java.util.LinkedList;

public class Accelerometer {

    // Contain the last event we got from the listener
    static public LinkedList<SensorEvent> lastEvents = new LinkedList<SensorEvent>();

    static public int lastAccuracy = 0;

    // Define a new listener
    static class AccelListener implements SensorEventListener {
        public void onSensorChanged(SensorEvent ev) {
            lastEvents.add(ev);
        }
        public void onAccuracyChanged(Sensor sensor, int accuracy) {
            lastAccuracy = accuracy;
        }
    }

    // Create our listener
    static AccelListener accelListener = new AccelListener();

    // Method to activate/deactivate the accelerometer service and listener
    static void accelerometerEnable(boolean enable) {
        Context context = (Context) PythonActivity.mActivity;
        SensorManager sm = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
        Sensor accel = sm.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION);

        if (accel == null)
            return;

        if (enable)
            sm.registerListener(accelListener, accel, SensorManager.SENSOR_DELAY_FASTEST);
        else
            sm.unregisterListener(accelListener, accel);
    }

    static void flush(){
        lastEvents = new LinkedList<SensorEvent>();
    }
}
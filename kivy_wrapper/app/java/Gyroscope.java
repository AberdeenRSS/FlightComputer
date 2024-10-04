package org.rss;

import org.kivy.android.PythonActivity;
import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import java.util.LinkedList;

public class Gyroscope {

    // Contain the last event we got from the listener
    static public LinkedList<SensorEvent> lastEvents = new LinkedList<SensorEvent>();

    static public int lastAccuracy = 0;

    // Define a new listener
    static class GyroListener implements SensorEventListener {
        public void onSensorChanged(SensorEvent ev) {
            lastEvents.add(ev);
        }
        public void onAccuracyChanged(Sensor sensor, int accuracy) {
            lastAccuracy = accuracy;
        }
    }

    // Create our listener
    static GyroListener gyroListener = new GyroListener();

    // Method to activate/deactivate the accelerometer service and listener
    static void gyroEnable(boolean enable) {
        Context context = (Context) PythonActivity.mActivity;
        SensorManager sm = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
        Sensor gyro = sm.getDefaultSensor(Sensor.TYPE_GYROSCOPE);

        if (gyro == null)
            return;

        if (enable)
            sm.registerListener(gyroListener, gyro, SensorManager.SENSOR_DELAY_FASTEST);
        else
            sm.unregisterListener(gyroListener, gyro);
    }

    static void flush(){
        lastEvents = new LinkedList<SensorEvent>();
    }
}
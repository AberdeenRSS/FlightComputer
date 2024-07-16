package org.rss;

import org.kivy.android.PythonActivity;
import android.content.Context;

import android.location.LocationManager;
import android.location.Location;
import android.location.LocationListener;
import android.os.Looper;

import java.lang.Exception;

import android.os.Bundle;

import java.util.LinkedList;
import java.util.List;


public class GPS {

    // Locaiton buffer
    static public LinkedList<Location> lastEvents = new LinkedList<Location>();

    static public List<String> providers = new LinkedList<String>();

    static public String provider = "";

    static public String status = "";

    private static float MIN_DISTANCE_CHANGE_FOR_UPDATES = 0.1f;

    private static long MIN_TIME_BW_UPDATES = 10;

    static class LocationTrack implements LocationListener {

        // @Override
        // public IBinder onBind(Intent intent) {
        //     return null;
        // }

        @Override
        public void onLocationChanged(Location location) {
            lastEvents.add(location);
        }

        @Override
        public void onStatusChanged(String s, int i, Bundle bundle) {
            status = s;
        }

        // @Override
        // public void onProviderEnabled(String s) {
        // }

        // @Override
        // public void onProviderDisabled(String s) {

        // }
    }

    static LocationTrack locationTrack = new LocationTrack();


    static void refreshOrStart() {

        Context mContext = (Context) PythonActivity.mActivity;


        LocationManager locationManager = (LocationManager) mContext
                .getSystemService(Context.LOCATION_SERVICE);

        providers = locationManager.getAllProviders();

        boolean fusedAvailable = false;
        boolean networkAvailable =false;
        boolean gpsAvailable = false;

        for(String s : providers){
            if(s.equals("fused")){
                fusedAvailable = true;
            }
            if(s.equals("gps")){
                gpsAvailable = true;
            }
            if(s.equals("network")){
                networkAvailable = true;
            }
        }

        String oldProvider = provider;
        
        if(fusedAvailable){
            provider = "fused";
        }

        else if(gpsAvailable){
            provider = "gps";
        }

        else if (networkAvailable){
            provider = "network";
        }

        if(oldProvider.equals(provider)){
            return;
        }

        locationManager.removeUpdates(locationTrack);

        locationManager.requestLocationUpdates(provider, MIN_TIME_BW_UPDATES, MIN_DISTANCE_CHANGE_FOR_UPDATES, locationTrack, Looper.getMainLooper());
        

    }

    static void stopListener() {

        Context mContext = (Context) PythonActivity.mActivity;

        LocationManager locationManager = (LocationManager) mContext
                .getSystemService(Context.LOCATION_SERVICE);

        if (locationManager != null) {
            locationManager.removeUpdates(locationTrack);
        }
    }

    static void flush(){
        lastEvents = new LinkedList<Location>();
    }

}




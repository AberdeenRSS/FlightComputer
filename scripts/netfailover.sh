#!/bin/bash
# failover.sh - Simple Wi-Fi <-> GSM failover using ip route

# SETTINGS
WIFI_IF="wlan0"
GSM_IF="ppp0"
PING_HOST="1.1.1.1"   # Test host for connectivity
PING_COUNT=2
PING_TIMEOUT=2

# GLOBAL VARS
CUR_DEFAULT=0

# FUNCTIONS
wifi_up() {
    ping -I "$WIFI_IF" -c $PING_COUNT -W $PING_TIMEOUT "$PING_HOST" > /dev/null 2>&1
}

add_gsm_default() {
  # Setup gsm as a defualt network adapter if it
  # hasn't been added yet
  ip route add default dev $GSM_IF metric 1000 || true
}

# Set default to Wi-Fi: remove default for GSM, then add default via gateway (if resolvable) or dev iface
set_default_to_wifi() {
  echo "$(date) Switching default to Wi-Fi ($WIFI_IF)"
  add_gsm_default
  ifmetric $WIFI_IF 200
  ifmetric $GSM_IF 600
  CUR_DEFAULT=$WIFI_IF
}

# Set default to GSM: remove default for Wi-Fi then add default dev ppp0
set_default_to_gsm() {
  echo "$(date) Switching default to GSM ($GSM_IF)"
  add_gsm_default
  ifmetric $GSM_IF 200
  ifmetric $WIFI_IF 600
  CUR_DEFAULT=$GSM_IF
}

# MAIN LOOP
while true; do

    if wifi_up; then
        # If Wi-Fi is up but not the default, switch back to Wi-Fi
        if [ "$CUR_DEFAULT" != "$WIFI_IF" ]; then
            set_default_to_wifi
        fi
    else
        # Wi-Fi down, use GSM if available
        if [ "$CUR_DEFAULT" != "$GSM_IF" ]; then
            set_default_to_gsm
        fi
    fi

    sleep 5
done


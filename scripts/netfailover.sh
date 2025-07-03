#!/bin/bash

WIFI_INTERFACE="wlan0"
PPP_INTERFACE="ppp0"
PING_TARGET="1.1.1.1"
PING_COUNT=3
LOG_FILE="/var/log/netfailover.log"

# Absolute paths
IFCONFIG="/sbin/ifconfig"
PON="/usr/bin/pon"
POFF="/usr/bin/poff"
PING="/bin/ping"
TEE="/usr/bin/tee"
DATE="/bin/date"

log() {
    echo "[$($DATE)] $1" | $TEE -a "$LOG_FILE"
}

$PING -I $WIFI_INTERFACE -c $PING_COUNT $PING_TARGET > /dev/null 2>&1

if [ $? -eq 0 ]; then
    if $IFCONFIG $PPP_INTERFACE > /dev/null 2>&1; then
        log "Wi-Fi is up, shutting down GSM..."
        sudo $POFF gprs
    else
        log "Wi-Fi is up, GSM already off."
    fi
else
    if $IFCONFIG $PPP_INTERFACE > /dev/null 2>&1; then
        log "Wi-Fi down, GSM already active."
    else
        log "Wi-Fi down, starting GSM..."
        sudo $PON gprs
    fi
fi

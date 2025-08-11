
# Network setup

[Wifi Setup](https://docs.radxa.com/en/zero/zero3/radxa-os/network)

## GSM hat

The hat uses the default serial pins 8 and 10.
By default the standard UART pins (8 and 10) are used as a serial output on the radxa 3w. To change this follow:

[Enable UART2](https://docs.radxa.com/en/zero/zero3/os-config/rsetup#configure-uart2_m0-as-normal-serial-port)

Next pp dial up needs to be setup. The setup steps can be found here:
[Waveshare](https://www.waveshare.com/wiki/SIM868_PPP_Dail-up_Networking)

A correctly setup file for the radxa can be found in `scripts/gprs`.
Add this to `/etc/ppp/peers/gprs`.   

Next the network failover script needs to be added. It automatically switches the
the network over to GSM if wifi is unavailable. The script can be found in 
`scripts/netfailover.sh` and needs to go into `/usr/local/bin/netfailover.sh`.   

Next these have to be added as services. To do so copy `ppp.service` and `netfailover.service`
to `/etc/systemd/system`. Lastly enable and start them with

```sh
sudo systemctl enable ppp
sudo systemctl enable netfailover
sudo systemctl start ppp
sudo systemctl start netfailover
```

### Troubleshooting

The following commands might be useful to diagnose the status of the network:


#### General overview of network interfaces
```sh
ip a
```

should output something like this (some numbers have been anonymized):
```
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host 
       valid_lft forever preferred_lft forever
2: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 00:22:00:00:00:e1 brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.103/24 brd 192.168.1.255 scope global dynamic noprefixroute wlan0
       valid_lft 6709sec preferred_lft 6709sec
    inet6 fd00::0000:0000:0000:dcd/64 scope global dynamic noprefixroute 
       valid_lft 23sec preferred_lft 23sec
    inet6 fe80::0000:0000:0000:480b/64 scope link noprefixroute 
       valid_lft forever preferred_lft forever
3: usb0: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN group default qlen 1000
    link/ether ae:00:00:00:00:6b brd ff:ff:ff:ff:ff:ff
4: ppp0: <POINTOPOINT,MULTICAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UNKNOWN group default qlen 3
    link/ppp 
    inet 10.000.000.000 peer 192.168.254.254/32 scope global ppp0
       valid_lft forever preferred_lft forever
```

#### Routes
```sh
ip route
```

should look like this:

```
default via 192.168.1.1 dev wlan0 proto dhcp metric 200 
default dev ppp0 scope link metric 600 
192.168.1.0/24 dev wlan0 proto kernel scope link src 192.168.1.103 metric 200 
192.168.254.254 dev ppp0 proto kernel scope link src 10.000.000.000 metric 600 
```

#### Logs

Logs can be found here
```sh
/var/log/netfailover.log
/var/log/netfailover.err

sudo journalctl -u netfailover
sudo journalctl -u ppp
```
opkg update
opkg install python3
opkg install python3-pip

mkdir /etc/hotplug.d/button
cp ./src/etc/50-toggle_display /etc/hotplug.d/button/
chmod +x /etc/hotplug.d/button/50-toggle_display
/etc/init.d/e750_mcu restart

pip3 install -e .

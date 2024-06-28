import pywifi

from pywifi import const


def is_wifi_connected():
    try:
        wifi = pywifi.PyWiFi()
        for iface in wifi.interfaces():
            if iface.status() == const.IFACE_CONNECTED:
                return True
        return False
    except Exception as e:
        return False


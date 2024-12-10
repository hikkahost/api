import socket


def is_ip_available(ip):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex((ip, 80)) == 0:
                return False
    except Exception:
        pass
    return True


def find_free_ip(ip_prefix_range):
    for ip_prefix in ip_prefix_range:
        ip = f"192.168.{ip_prefix}.101"
        if is_ip_available(ip):
            return ip_prefix
    return None


if __name__ == "__main__":
    ip_prefix_range = range(0, 256)
    free_ip = find_free_ip(ip_prefix_range)
    if free_ip is None:
        print("Свободный IP:", f"192.168.{ip_prefix}.101")
    else:
        print("Нет свободных IP-адресов в заданном диапазоне.")

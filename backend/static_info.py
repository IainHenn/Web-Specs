import os
import platform
import socket
import psutil
import datetime
import uuid
import subprocess

def get_ip_addresses():
    ip_list = []
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip_list.append((iface, addr.address))
    return ip_list

def get_mac_addresses():
    mac_list = []
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                mac_list.append((iface, addr.address))
    return mac_list

def get_boot_time():
    bt = datetime.datetime.fromtimestamp(psutil.boot_time())
    return bt.strftime("%Y-%m-%d %H:%M:%S")

def get_logged_in_users():
    return [u.name for u in psutil.users()]

def get_listening_ports():
    connections = psutil.net_connections(kind="inet")
    ports = set()
    for conn in connections:
        if conn.status == "LISTEN":
            ports.add(conn.laddr.port)
    return sorted(list(ports))

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError:
        return "N/A"

def system_info():
    try:
        info = {
            "Hostname": socket.gethostname(),
            "FQDN": socket.getfqdn(),
            "IP Addresses": get_ip_addresses(),
            "MAC Addresses": get_mac_addresses(),
            "OS": platform.system(),
            "OS Release": platform.release(),
            "Kernel Version": platform.version(),
            "Architecture": platform.machine(),
            "CPU Model": platform.processor(),
            "CPU Cores": psutil.cpu_count(logical=False),
            "CPU Threads": psutil.cpu_count(logical=True),
            "Memory (Total)": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
            "Swap (Total)": f"{round(psutil.swap_memory().total / (1024**3), 2)} GB",
            "Boot Time": get_boot_time(),
            "Uptime (hours)": round((datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())).total_seconds() / 3600, 2),
            "Users Logged In": get_logged_in_users(),
            "Listening Ports": get_listening_ports(),
            "Firewall Rules": run_cmd("sudo iptables -L -n") or "N/A",
            "Installed Docker Version": run_cmd("docker --version"),
            "Installed PostgreSQL Version": run_cmd("psql --version"),
            "Virtualization": run_cmd("systemd-detect-virt"),
            "Cloud Metadata": run_cmd("curl -s http://169.254.169.254/latest/meta-data/instance-id || echo 'Not Cloud'"),
        }

        return info
    
    except Exception as e:
        print(e)
        return {}
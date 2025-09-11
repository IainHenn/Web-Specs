from fastapi import FastAPI, WebSocket
import asyncio
import psutil
import json

from ping3 import ping
import ifcfg 
import platform
import pynvml
import pyadl
import subprocess
import psycopg2
import os
import datetime

def get_db_connection():
    try:
        connection = psycopg2.connect(
            dbname="web_specs",
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PW"),
            host=os.getenv("DB_HOST"),
            port="5433"
        )
        print("Database connection successful")
        return connection
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None

def get_gpu_stats():
    gpu_info = {}
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        gpus = []
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle).decode()
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpus.append({
                'name': name,
                'memory_total': memory.total,
                'memory_used': memory.used,
                'memory_free': memory.free,
                'temperature': temperature,
                'gpu_utilization': utilization.gpu,
                'memory_utilization': utilization.memory
            })
        gpu_info['vendor'] = 'NVIDIA'
        gpu_info['gpus'] = gpus 
        pynvml.nvmlShutdown()
    except Exception as e:
        gpu_info['error'] = str(e)
    return gpu_info

def get_ping():
    try:
        interfaces = ifcfg.interfaces()
        ip = None
        for iface in interfaces.values():
            if 'inet' in iface and iface['inet'] != '127.0.0.1':
                ip = iface['inet']
                break
        if ip:
            result = ping(ip)
            return result * 1000000 if result else None
        return None
    except Exception as e:
        print("error: {e}")
        return None

def gather_cpu_times():
    cpu_times = psutil.cpu_times(percpu=True)

    user_time = {f"core_{i+1}": core[0] for i, core in enumerate(cpu_times)}
    system_time = {f"core_{i+1}": core[1] for i, core in enumerate(cpu_times)}
    idle_time = {f"core_{i+1}": core[2] for i, core in enumerate(cpu_times)}
    
    return user_time, system_time, idle_time

def gather_cpu_percents():
    cpu_percents = psutil.cpu_percent(percpu=True)
    return {f"core_{i+1}": percent for i, percent in enumerate(cpu_percents)}

def gather_virtual_memory_stats():
    virtual_memory = psutil.virtual_memory()
    return virtual_memory[1], virtual_memory[2], virtual_memory[3]

def gather_swap_memory_stats():
    swap_memory = psutil.swap_memory()
    return swap_memory[1], swap_memory[2], swap_memory[3]

def get_disk_usage():
    disk_partitions = psutil.disk_partitions()
    disk_usage_info = {}
    for partition in disk_partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_usage_info[partition.device] = {
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            }
        except PermissionError:
            continue
    return disk_usage_info

# Windows needs diskperf -y ran in cmd.exe
def get_disk_io_counters():
    raw_disks = psutil.disk_io_counters(perdisk=True)
    result = {}
    for key, value in raw_disks.items():
        result[key] = {
            'read_count': value.read_count,
            'write_count': value.write_count,
            'read_bytes': value.read_bytes,
            'write_bytes': value.write_bytes,
            'read_time': value.read_time,
            'write_time': value.write_time,
        }
    return result

def log_data(system_info):
    try:
        now = datetime.datetime.now()
        conn = get_db_connection()
        print(f"conn: {conn}")
        with conn.cursor() as cursor:
            
            #CPU logging
            num_cpus = len(system_info['cpu']['user_time'].keys())
            for i in range(0,num_cpus):
                core_id = i+1
                user_time = system_info['cpu']['user_time'][f'core_{core_id}']
                system_time = system_info['cpu']['system_time'][f'core_{core_id}']
                idle_time = system_info['cpu']['idle_time'][f'core_{core_id}']
                percent = system_info['cpu']['percent'][f'core_{core_id}']
                cursor.execute(f"""INSERT INTO 
                    cpu_metrics (timestamp, core_id, user_time, system_time, idle_time, percent_usage)
                    VALUES ('{now}', {core_id}, {user_time}, {system_time}, {idle_time}, {percent})"""
                )
            
            # IO
            for raw_disk in system_info['io']:
                cursor.execute(f"""INSERT INTO
                disk_io_metrics (timestamp, device_name, read_count, write_count, read_bytes, write_bytes, read_time, write_time)
                VALUES ('{now}', '{raw_disk}', {system_info['io'][raw_disk]['read_count']}, {system_info['io'][raw_disk]['write_count']}, {system_info['io'][raw_disk]['read_bytes']}, {system_info['io'][raw_disk]['write_bytes']}, {system_info['io'][raw_disk]['read_time']}, {system_info['io'][raw_disk]['write_time']})"""
                )
            
            # Disk Usage
            for disk in system_info['disk_usage']:
                cursor.execute(f"""INSERT INTO
                    disk_usage_metrics (timestamp, device_name, mountpoint, fstype, total_space, used_space, free_space, percent_usage)
                    VALUES ('{now}', '{disk}', '{system_info['disk_usage'][disk]['mountpoint']}', '{system_info['disk_usage'][disk]['fstype']}', {system_info['disk_usage'][disk]['total']}, {system_info['disk_usage'][disk]['used']}, {system_info['disk_usage'][disk]['free']}, {system_info['disk_usage'][disk]['percent']})"""
                )
            
            # Memory
            cursor.execute(f"""INSERT INTO
                    memory_metrics (timestamp, available_memory, used_memory, memory_percent_usage)
                    VALUES ('{now}', {system_info['memory']['available_memory']}, {system_info['memory']['used_memory']}, {system_info['memory']['memory_percent_usage']})"""
                )
            
            # Swap Memory
            cursor.execute(f"""INSERT INTO
                    swap_memory_metrics (timestamp, used_memory, free_memory, percent_usage)
                    VALUES ('{now}', {system_info['swap_memory']['used_memory']}, {system_info['swap_memory']['free_memory']}, {system_info['swap_memory']['percent_usage']})"""
                )
            
            conn.commit()

    except Exception as e:
        print(e)
        conn.rollback()
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

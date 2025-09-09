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

from fastapi.responses import JSONResponse as jsonify
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

'''
PLANS:
- overall/monthly/yearly/daily/hourly average/max/min CPU (per CPU) /memory/swap memory percent usage --> backend done
- overall/monthly/yearly/daily/hourly average/max/min IO read/write --> backend routes done
- cpu/memory/swap memory distribution, read/write distribution
- violin plot for disk io latency
- notif system 
- config page + thresholds for notif
- static info page (ip, system info, etc)
- possible RAG based chatbot......?
'''

#Rest-like Routes
@app.get("/io/read/bytes")
def io_read_bytes(type: str='avg', time: str = 'overall'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        time_query = ""
        if time == 'hourly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
        elif time == 'daily':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
        elif time == 'monthly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
        elif time == 'yearly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT device_name, {type.upper()}(read_bytes) FROM disk_io_metrics {time_query} GROUP BY device_name"
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_read_bytes": {row[0]: round(float(row[1]),2) for row in data}})
            else:
                return jsonify({"error": f"Unable to grab {type} data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/write/bytes")
def io_write_bytes(type: str='avg', time: str = 'overall'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        time_query = ""
        if time == 'hourly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
        elif time == 'daily':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
        elif time == 'monthly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
        elif time == 'yearly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT device_name, {type.upper()}(write_bytes) FROM disk_io_metrics {time_query} GROUP BY device_name"
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_write_bytes": {row[0]: round(float(row[1]),2) for row in data}})
            else:
                return jsonify({"error": f"Unable to grab {type} data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/read/time")
def io_read_time(type: str='avg', time: str = 'overall'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        time_query = ""
        if time == 'hourly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
        elif time == 'daily':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
        elif time == 'monthly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
        elif time == 'yearly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT device_name, {type.upper()}(read_time) FROM disk_io_metrics {time_query} GROUP BY device_name"
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_read_time": {row[0]: round(float(row[1]),2) for row in data}})
            else:
                return jsonify({"error": f"Unable to grab {type} data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/write/time")
def io_write_time(type: str='avg', time: str = 'overall'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        time_query = ""
        if time == 'hourly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
        elif time == 'daily':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
        elif time == 'monthly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
        elif time == 'yearly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT device_name, {type.upper()}(write_time) FROM disk_io_metrics {time_query} GROUP BY device_name"
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_write_time": {row[0]: round(float(row[1]),2) for row in data}})
            else:
                return jsonify({"error": f"Unable to grab {type} data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/memory/percent")
def memory_percent(type: str = 'avg', time: str = 'overall'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        time_query = ""
        if time == 'hourly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
        elif time == 'daily':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
        elif time == 'monthly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
        elif time == 'yearly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT {type.upper()}(memory_percent_usage) FROM memory_metrics {time_query}")
            data = cursor.fetchone()
            if data:
                return jsonify({"memory_percent": {"Memory":round(float(data[0]),2)}})
            else:
                return jsonify({"error": f"Unable to grab {type} data for memory"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/memory/percent/timeseries")
def memory_percent_timeseries(type: str = 'avg', groupby: str = 'hour'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        # Set time window and truncation for grouping
        if groupby == 'minute':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
            trunc = "minute"
        elif groupby == 'hour':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
            trunc = "hour"
        elif groupby == 'day':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
            trunc = "day"
        elif groupby == 'month':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"
            trunc = "month"
        elif groupby == 'year':
            time_query = ""
            trunc = "year"
        else:
            return jsonify({"error": "Invalid groupby parameter. Use 'minute', 'hour', 'day', 'month', or 'year'."}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT date_trunc('{trunc}', timestamp) AS period, {type.upper()}(memory_percent_usage)
                FROM memory_metrics
                {time_query}
                GROUP BY date_trunc('{trunc}', timestamp)
                ORDER BY period
                """
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"memory_percent_timeseries": [
                    {"period": row[0].isoformat(), "value": round(float(row[1]), 2)} for row in data
                ]})
            else:
                return jsonify({"error": f"Unable to grab {type} timeseries data for memory"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/swap_memory/percent")
def swap_memory_percent(type: str = 'avg', time: str = 'overall'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        time_query = ""
        if time == 'hourly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
        elif time == 'daily':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
        elif time == 'monthly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
        elif time == 'yearly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT {type.upper()}(percent_usage) FROM swap_memory_metrics {time_query}")
            data = cursor.fetchone()
            if data:
                return jsonify({"memory_percent": {"Memory": data[0]}})
            else:
                return jsonify({"error": f"Unable to grab {type} data for swap memory"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/swap_memory/percent/timeseries")
def swap_memory_percent_timeseries(type: str = 'avg', groupby: str = 'hour'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        # Set time window and truncation for grouping
        if groupby == 'minute':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
            trunc = "minute"
        elif groupby == 'hour':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
            trunc = "hour"
        elif groupby == 'day':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
            trunc = "day"
        elif groupby == 'month':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"
            trunc = "month"
        elif groupby == 'year':
            time_query = ""
            trunc = "year"
        else:
            return jsonify({"error": "Invalid groupby parameter. Use 'minute', 'hour', 'day', 'month', or 'year'."}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT date_trunc('{trunc}', timestamp) AS period, {type.upper()}(percent_usage)
                FROM swap_memory_metrics
                {time_query}
                GROUP BY date_trunc('{trunc}', timestamp)
                ORDER BY period
                """
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"swap_memory_percent_timeseries": [
                    {"period": row[0].isoformat(), "value": round(float(row[1]), 2)} for row in data
                ]})
            else:
                return jsonify({"error": f"Unable to grab {type} timeseries data for memory"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/cpu/percent")
def cpu_percent(type: str = 'avg', time: str = 'overall'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        time_query = ""
        if time == 'hourly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
        elif time == 'daily':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
        elif time == 'monthly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
        elif time == 'yearly':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT core_id, {type.upper()}(percent_usage) FROM cpu_metrics {time_query} GROUP BY core_id"
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"cpu_percent": {row[0]: round(row[1], 2) for row in data}})
            else:
                return jsonify({"error": f"Unable to grab {type} data for CPU cores"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/cpu/percent/timeseries")
def cpu_percent_timeseries(type: str = 'avg', groupby: str = 'hour'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        # Set time window and truncation for grouping
        if groupby == 'minute':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
            trunc = "minute"
        elif groupby == 'hour':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
            trunc = "hour"
        elif groupby == 'day':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
            trunc = "day"
        elif groupby == 'month':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"
            trunc = "month"
        elif groupby == 'year':
            time_query = ""
            trunc = "year"
        else:
            return jsonify({"error": "Invalid groupby parameter. Use 'minute', 'hour', 'day', 'month', or 'year'."}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT core_id, date_trunc('{trunc}', timestamp) AS period, {type.upper()}(percent_usage)
                FROM cpu_metrics
                {time_query}
                GROUP BY core_id, date_trunc('{trunc}', timestamp)
                ORDER BY core_id, period
                """
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"cpu_percent_timeseries": [
                    {"core_id": row[0], "period": row[1].isoformat(), "value": round(float(row[2]), 2)} for row in data
                ]})
            else:
                return jsonify({"error": f"Unable to grab {type} timeseries data for memory"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/read/bytes/timeseries")
def io_read_bytes_timeseries(type: str = 'avg', groupby: str = 'hour'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        # Set time window and truncation for grouping
        if groupby == 'minute':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
            trunc = "minute"
        elif groupby == 'hour':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
            trunc = "hour"
        elif groupby == 'day':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
            trunc = "day"
        elif groupby == 'month':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"
            trunc = "month"
        elif groupby == 'year':
            time_query = ""
            trunc = "year"
        else:
            return jsonify({"error": "Invalid groupby parameter. Use 'minute', 'hour', 'day', 'month', or 'year'."}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT device_name, date_trunc('{trunc}', timestamp) AS period, {type.upper()}(read_bytes)
                FROM disk_io_metrics
                {time_query}
                GROUP BY device_name, date_trunc('{trunc}', timestamp)
                ORDER BY device_name, period
                """
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_read_bytes_timeseries": [
                    {"device_name": row[0], "period": row[1].isoformat(), "value": round(float(row[2]), 2)} for row in data
                ]})
            else:
                return jsonify({"error": f"Unable to grab {type} timeseries data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/write/bytes/timeseries")
def io_write_bytes_timeseries(type: str = 'avg', groupby: str = 'hour'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        # Set time window and truncation for grouping
        if groupby == 'minute':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
            trunc = "minute"
        elif groupby == 'hour':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
            trunc = "hour"
        elif groupby == 'day':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
            trunc = "day"
        elif groupby == 'month':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"
            trunc = "month"
        elif groupby == 'year':
            time_query = ""
            trunc = "year"
        else:
            return jsonify({"error": "Invalid groupby parameter. Use 'minute', 'hour', 'day', 'month', or 'year'."}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT device_name, date_trunc('{trunc}', timestamp) AS period, {type.upper()}(write_bytes)
                FROM disk_io_metrics
                {time_query}
                GROUP BY device_name, date_trunc('{trunc}', timestamp)
                ORDER BY device_name, period
                """
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_write_bytes_timeseries": [
                    {"device_name": row[0], "period": row[1].isoformat(), "value": round(float(row[2]), 2)} for row in data
                ]})
            else:
                return jsonify({"error": f"Unable to grab {type} timeseries data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/read/time/timeseries")
def io_read_time_timeseries(type: str = 'avg', groupby: str = 'hour'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        # Set time window and truncation for grouping
        if groupby == 'minute':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
            trunc = "minute"
        elif groupby == 'hour':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
            trunc = "hour"
        elif groupby == 'day':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
            trunc = "day"
        elif groupby == 'month':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"
            trunc = "month"
        elif groupby == 'year':
            time_query = ""
            trunc = "year"
        else:
            return jsonify({"error": "Invalid groupby parameter. Use 'minute', 'hour', 'day', 'month', or 'year'."}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT device_name, date_trunc('{trunc}', timestamp) AS period, {type.upper()}(read_time)
                FROM disk_io_metrics
                {time_query}
                GROUP BY device_name, date_trunc('{trunc}', timestamp)
                ORDER BY device_name, period
                """
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_read_time_timeseries": [
                    {"device_name": row[0], "period": row[1].isoformat(), "value": round(float(row[2]), 2)} for row in data
                ]})
            else:
                return jsonify({"error": f"Unable to grab {type} timeseries data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/write/time/timeseries")
def io_write_time_timeseries(type: str = 'avg', groupby: str = 'hour'):
    try:
        if type not in ['max', 'min', 'avg']:
            return jsonify({"error": "Invalid type parameter. Use 'max', 'min', or 'avg'."}), 400

        # Set time window and truncation for grouping
        if groupby == 'minute':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 hour'"
            trunc = "minute"
        elif groupby == 'hour':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 day'"
            trunc = "hour"
        elif groupby == 'day':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 month'"
            trunc = "day"
        elif groupby == 'month':
            time_query = "WHERE timestamp >= NOW() - INTERVAL '1 year'"
            trunc = "month"
        elif groupby == 'year':
            time_query = ""
            trunc = "year"
        else:
            return jsonify({"error": "Invalid groupby parameter. Use 'minute', 'hour', 'day', 'month', or 'year'."}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT device_name, date_trunc('{trunc}', timestamp) AS period, {type.upper()}(write_time)
                FROM disk_io_metrics
                {time_query}
                GROUP BY device_name, date_trunc('{trunc}', timestamp)
                ORDER BY device_name, period
                """
            )
            data = cursor.fetchall()
            if data:
                return jsonify({"io_write_time_timeseries": [
                    {"device_name": row[0], "period": row[1].isoformat(), "value": round(float(row[2]), 2)} for row in data
                ]})
            else:
                return jsonify({"error": f"Unable to grab {type} timeseries data for IO"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#Web Socket Routes
@app.websocket("/ws/metrics")
async def metric_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            system_info = {}

            # CPU
            system_info['cpu'] = {}
            user_time, system_time, idle_time = gather_cpu_times()
            system_info['cpu']['user_time'] = user_time
            system_info['cpu']['system_time'] = system_time
            system_info['cpu']['idle_time'] = idle_time
            system_info['cpu']['percent'] = gather_cpu_percents()

            # Memory
            system_info['memory'] = {}
            available_memory, percent_usage, used_memory = gather_virtual_memory_stats()
            system_info['memory']['available_memory'] = available_memory
            system_info['memory']['memory_percent_usage'] = percent_usage
            system_info['memory']['used_memory'] = used_memory

            # Swap memory
            system_info['swap_memory'] = {}
            swap_used_memory, swap_free_memory, swap_percent_usage = gather_swap_memory_stats()
            system_info['swap_memory']['used_memory'] = swap_used_memory
            system_info['swap_memory']['free_memory'] = swap_free_memory
            system_info['swap_memory']['percent_usage'] = swap_percent_usage

            # Disk usage
            system_info['disk_usage'] = get_disk_usage()

            # IO
            system_info['io'] = get_disk_io_counters()
            
            log_data(system_info)

            await ws.send_text(json.dumps(system_info))
            await asyncio.sleep(3)
    except Exception as e:
        print("WebSocket Disconnected", e)
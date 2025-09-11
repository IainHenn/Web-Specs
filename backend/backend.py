from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse as jsonify
from fastapi.middleware.cors import CORSMiddleware
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

from live_info import (
    get_db_connection,
    get_gpu_stats,
    get_ping,
    gather_cpu_times,
    gather_cpu_percents,
    gather_virtual_memory_stats,
    gather_swap_memory_stats,
    get_disk_usage,
    get_disk_io_counters,
    log_data,
)

from static_info import system_info

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

'''
PLANS:
- overall/monthly/yearly/daily/hourly average/max/min CPU (per CPU) /memory/swap memory percent usage --> backend done
- overall/monthly/yearly/daily/hourly average/max/min IO read/write --> backend routes done
- cpu/memory/swap memory distribution, read/write distribution --> done
- violin plot for disk io latency --> backend route done
- static info page (ip, system info, etc)
- notif system 
- config page + thresholds for notif
- possible RAG based chatbot......?
'''

#Rest-like Routes
@app.get("/system/static-info")
def static_info():
    return jsonify({"static-info": system_info()}), 200

@app.get("/memory/percent/distribution")
def memory_percent_dist(time: str = 'hour'):
    try:
        # Map time param to interval
        intervals = {
            'hour': "WHERE timestamp >= NOW() - INTERVAL '1 hour'",
            'day': "WHERE timestamp >= NOW() - INTERVAL '1 day'",
            'month': "WHERE timestamp >= NOW() - INTERVAL '1 month'",
            'year': "WHERE timestamp >= NOW() - INTERVAL '1 year'",
            'overall': ""
        }
        if time not in intervals:
            return jsonify({"error": "Invalid time parameter. Use 'hour', 'day', 'month', 'year', or 'overall'."}), 400

        time_query = intervals[time]
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT memory_percent_usage FROM memory_metrics {time_query}")
            data = cursor.fetchall()
            values = [float(row[0]) for row in data]
            return jsonify({"memory_percent_distribution": values})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/swap_memory/percent/distribution")
def swap_memory_percent_dist(time: str = 'hour'):
    try:
        intervals = {
            'hour': "WHERE timestamp >= NOW() - INTERVAL '1 hour'",
            'day': "WHERE timestamp >= NOW() - INTERVAL '1 day'",
            'month': "WHERE timestamp >= NOW() - INTERVAL '1 month'",
            'year': "WHERE timestamp >= NOW() - INTERVAL '1 year'",
            'overall': ""
        }
        if time not in intervals:
            return jsonify({"error": "Invalid time parameter. Use 'hour', 'day', 'month', 'year', or 'overall'."}), 400

        time_query = intervals[time]
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT percent_usage FROM swap_memory_metrics {time_query}")
            data = cursor.fetchall()
            values = [float(row[0]) for row in data]
            return jsonify({"swap_memory_percent_distribution": values})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/cpu/percent/distribution")
def cpu_percent_dist(time: str = 'hour'):
    try:
        intervals = {
            'hour': "WHERE timestamp >= NOW() - INTERVAL '1 hour'",
            'day': "WHERE timestamp >= NOW() - INTERVAL '1 day'",
            'month': "WHERE timestamp >= NOW() - INTERVAL '1 month'",
            'year': "WHERE timestamp >= NOW() - INTERVAL '1 year'",
            'overall': ""
        }
        if time not in intervals:
            return jsonify({"error": "Invalid time parameter. Use 'hour', 'day', 'month', 'year', or 'overall'."}), 400

        time_query = intervals[time]
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT AVG(percent_usage) FROM cpu_metrics {time_query} GROUP BY timestamp")
            data = cursor.fetchall()
            return jsonify({"cpu_percent_distribution": [float(row[0]) for row in data]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/read/bytes/distribution")
def io_read_bytes_dist(time: str = 'hour'):
    try:
        intervals = {
            'hour': "WHERE timestamp >= NOW() - INTERVAL '1 hour'",
            'day': "WHERE timestamp >= NOW() - INTERVAL '1 day'",
            'month': "WHERE timestamp >= NOW() - INTERVAL '1 month'",
            'year': "WHERE timestamp >= NOW() - INTERVAL '1 year'",
            'overall': ""
        }
        if time not in intervals:
            return jsonify({"error": "Invalid time parameter. Use 'hour', 'day', 'month', 'year', or 'overall'."}), 400

        time_query = intervals[time]
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT device_name, read_bytes FROM disk_io_metrics {time_query}")
            data = cursor.fetchall()
            dist = {}
            for device, value in data:
                dist.setdefault(device, []).append(float(value))
            return jsonify({"io_read_bytes_distribution": dist})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/io/write/bytes/distribution")
def io_write_bytes_dist(time: str = 'hour'):
    try:
        intervals = {
            'hour': "WHERE timestamp >= NOW() - INTERVAL '1 hour'",
            'day': "WHERE timestamp >= NOW() - INTERVAL '1 day'",
            'month': "WHERE timestamp >= NOW() - INTERVAL '1 month'",
            'year': "WHERE timestamp >= NOW() - INTERVAL '1 year'",
            'overall': ""
        }
        if time not in intervals:
            return jsonify({"error": "Invalid time parameter. Use 'hour', 'day', 'month', 'year', or 'overall'."}), 400

        time_query = intervals[time]
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT device_name, write_bytes FROM disk_io_metrics {time_query}")
            data = cursor.fetchall()
            dist = {}
            for device, value in data:
                dist.setdefault(device, []).append(float(value))
            return jsonify({"io_write_bytes_distribution": dist})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
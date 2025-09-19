# Web Specs

Web Specs is a live dashboard and monitoring system for computer/server specs, resource usage, and notifications. It provides real-time and historical data visualization, alerting, and email notifications for system metrics.

## Features
- Real-time monitoring of CPU, memory, swap, disk, IO, and GPU metrics
- Historical data visualization (time series, bar charts, distributions)
- Notification system with configurable thresholds
- Email alerting to subscribed users
- Static system info page
- WebSocket live updates
- Configurable via frontend modals

## Tech Stack
- **Frontend:** React (TypeScript), Plotly.js
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **Other:** APScheduler, psycopg2, smtplib, email, psutil, pynvml, pyadl, ping3, ifcfg

## Environment Variables
Set these in your environment (e.g., `.env` or system environment):
- `DB_USER`: PostgreSQL username
- `DB_PW`: PostgreSQL password
- `DB_HOST`: PostgreSQL host (e.g., `localhost`)
- (Port is hardcoded as `5433` in code)

## Installation
1. **Clone the repo**
2. **Backend dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```
3. **Frontend dependencies:**
   ```bash
   cd frontend/web-specs
   npm install
   ```
4. **Database:**
   - Requires PostgreSQL with tables for metrics and alerts (see below)

## Database Tables
- `cpu_metrics`, `memory_metrics`, `swap_memory_metrics`, `disk_io_metrics`, `disk_usage_metrics`, `alerts`, `email_subscriptions`
- Alerts table example:
  ```sql
  CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    component TEXT,
    value FLOAT,
    threshold_value FLOAT,
    sent BOOLEAN
  );
  CREATE TABLE email_subscriptions (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE
  );
  ```

## Database Table Definitions

```sql
-- Table: public.alerts
CREATE TABLE IF NOT EXISTS public.alerts
(
    id bigint NOT NULL DEFAULT nextval('alerts_id_seq'::regclass),
    "timestamp" timestamp without time zone,
    component text COLLATE pg_catalog."default",
    value double precision,
    threshold_value double precision,
    sent boolean,
    CONSTRAINT alerts_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.alerts OWNER to postgres;

-- Table: public.cpu_metrics
CREATE TABLE IF NOT EXISTS public.cpu_metrics
(
    id integer NOT NULL DEFAULT nextval('cpu_metrics_id_seq'::regclass),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    core_id integer NOT NULL,
    user_time double precision NOT NULL,
    system_time double precision NOT NULL,
    idle_time double precision NOT NULL,
    percent_usage double precision NOT NULL,
    CONSTRAINT cpu_metrics_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.cpu_metrics OWNER to postgres;

-- Table: public.disk_io_metrics
CREATE TABLE IF NOT EXISTS public.disk_io_metrics
(
    id integer NOT NULL DEFAULT nextval('disk_io_metrics_id_seq'::regclass),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    device_name text COLLATE pg_catalog."default" NOT NULL,
    read_count bigint NOT NULL,
    write_count bigint NOT NULL,
    read_bytes bigint NOT NULL,
    write_bytes bigint NOT NULL,
    read_time bigint NOT NULL,
    write_time bigint NOT NULL,
    CONSTRAINT disk_io_metrics_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.disk_io_metrics OWNER to postgres;

-- Table: public.disk_usage_metrics
CREATE TABLE IF NOT EXISTS public.disk_usage_metrics
(
    id integer NOT NULL DEFAULT nextval('disk_usage_metrics_id_seq'::regclass),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    device_name text COLLATE pg_catalog."default" NOT NULL,
    mountpoint text COLLATE pg_catalog."default" NOT NULL,
    fstype text COLLATE pg_catalog."default" NOT NULL,
    total_space bigint NOT NULL,
    used_space bigint NOT NULL,
    free_space bigint NOT NULL,
    percent_usage double precision NOT NULL,
    CONSTRAINT disk_usage_metrics_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.disk_usage_metrics OWNER to postgres;

-- Table: public.email_subscriptions
CREATE TABLE IF NOT EXISTS public.email_subscriptions
(
    id bigint NOT NULL DEFAULT nextval('email_subscriptions_seq'::regclass),
    email text COLLATE pg_catalog."default",
    CONSTRAINT email_subscriptions_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.email_subscriptions OWNER to postgres;

-- Table: public.memory_metrics
CREATE TABLE IF NOT EXISTS public.memory_metrics
(
    id integer NOT NULL DEFAULT nextval('memory_metrics_id_seq'::regclass),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    available_memory bigint NOT NULL,
    used_memory bigint NOT NULL,
    memory_percent_usage double precision NOT NULL,
    CONSTRAINT memory_metrics_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.memory_metrics OWNER to postgres;

-- Table: public.network_metrics
CREATE TABLE IF NOT EXISTS public.network_metrics
(
    id integer NOT NULL DEFAULT nextval('network_metrics_id_seq'::regclass),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ip_address text COLLATE pg_catalog."default" NOT NULL,
    latency_microseconds bigint,
    CONSTRAINT network_metrics_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.network_metrics OWNER to postgres;

-- Table: public.swap_memory_metrics
CREATE TABLE IF NOT EXISTS public.swap_memory_metrics
(
    id integer NOT NULL DEFAULT nextval('swap_memory_metrics_id_seq'::regclass),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    used_memory bigint NOT NULL,
    free_memory bigint NOT NULL,
    percent_usage double precision NOT NULL,
    CONSTRAINT swap_memory_metrics_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.swap_memory_metrics OWNER to postgres;
```

## Running the Project
- **Backend:**
  ```bash
  uvicorn backend.backend:app --reload
  ```
- **Frontend:**
  ```bash
  cd frontend/web-specs
  npm start
  ```

## Backend API Routes
### System Info
- `GET /system/static-info` — Returns static system info

### Metrics (examples)
- `GET /memory/percent/distribution?time=hour|day|month|year|overall`
- `GET /swap_memory/percent/distribution?time=...`
- `GET /cpu/percent/distribution?time=...`
- `GET /io/read/bytes/distribution?time=...`
- `GET /io/write/bytes/distribution?time=...`
- `GET /memory/percent?type=avg|max|min&time=hourly|daily|monthly|yearly|overall`
- `GET /cpu/percent?type=avg|max|min&time=...`
- `GET /memory/percent/timeseries?type=avg|max|min&groupby=minute|hour|day|month|year`
- `GET /cpu/percent/timeseries?type=...&groupby=...`
- Similar routes for IO and swap metrics

### Notification Settings
- `GET /notification-settings` — Get current notification thresholds
- `PATCH /notification-settings` — Update notification thresholds (JSON body: `{ changes: ... }`)

### Email System
- `POST /host-email` — Set host email and app password (JSON body: `{ email, app_password }`)
- `POST /emails/{email}` — Add a subscription email

### WebSocket
- `ws://127.0.0.1:8000/ws/metrics` — Live metrics stream

## Notification & Email System
- Thresholds for metrics are set in `notif_config.json` (editable via frontend modal)
- Alerts are logged in the `alerts` table when thresholds are exceeded
- Host email and app password are set via frontend modal and stored in `email_config.json`
- Subscribed emails are stored in `email_subscriptions` table
- APScheduler sends out alert emails every hour to all subscribed emails

## Frontend Usage
- Notification icon: open modal to set thresholds
- Email icon: open modal to set host email/app password and add subscription emails
- Data pages: real-time, time series, bar charts, distributions, static info

## Additional Notes
- Ensure PostgreSQL is running and accessible
- SMTP server is set to Gmail (`smtp.gmail.com:587`); host email must be Gmail and use an app password
- For disk IO metrics on Windows, run `diskperf -y` in cmd.exe
- Some system info commands may require elevated privileges (e.g., firewall rules)

## Troubleshooting
- Check environment variables for DB connection
- Check `notif_config.json` and `email_config.json` for correct format
- Check browser console and backend logs for errors

## License
MIT

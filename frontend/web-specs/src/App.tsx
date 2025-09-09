import { useState, useEffect, useRef } from 'react'
import Plot from 'react-plotly.js'
import './App.css'

// Helper to flatten metrics object to key-paths and values
function flattenMetrics(obj: any, prefix = ''): Record<string, number> {
  let result: Record<string, number> = {};
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'number') {
      result[path] = value;
    } else if (typeof value === 'object' && value !== null) {
      Object.assign(result, flattenMetrics(value, path));
    }
  }
  return result;
}

// Generic grid for a group of metrics
function MetricsGroup({ group, title, metric, data, history}: { group: string, title: string, metric: Record<string,string>, data: any, history: Record<string, number[]> }) {
  const flat = flattenMetrics(data, group);
  return (
    <div style={{ marginBottom: '2rem' }}>
      <h2 style={{
        color: '#00e676',
        fontWeight: 600,
        fontSize: '1.5rem',
        marginBottom: '1rem',
        textShadow: '0 2px 8px #0008'
      }}>{title}</h2>
      <div
        style={{
          width: '100%',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '2rem',
          background: '#181818',
          padding: '2rem',
          borderRadius: '1rem'
        }}
      >
        {Object.entries(flat).map(([key, value]) => (
            <div
            key={key}
            style={{
              background: '#23272f',
              border: '1px solid #333',
              borderRadius: '1rem',
              padding: '1.5rem',
              boxShadow: '0 2px 8px #0008',
              color: '#eee',
            }}
            >
            <div style={{ fontWeight: 600, fontSize: '1.1rem', marginBottom: '0.5rem' }}>{key.replace(`${group}.`, '')}</div>
            <div style={{ fontSize: '1.5rem', marginBottom: '1rem', color: '#00e676' }}>{value}</div>
            <Plot
              data={[
              {
                x: Array.from({ length: history[key]?.length ?? 0 }, (_, i) => i),
                y: history[key] ?? [],
                type: 'scatter',
                mode: 'lines',
                line: { color: '#00e676', width: 3, shape: 'spline' },
                fill: 'tozeroy',
                fillcolor: 'rgba(0,230,118,0.1)',
              },
              ]}
              layout={{
              paper_bgcolor: '#23272f',
              plot_bgcolor: '#23272f',
              font: { color: '#eee' },
              width: 380,
              height: 180,
              margin: { t: 30, r: 10, l: 40, b: 30 },
              xaxis: {
                showgrid: false,
                zeroline: false,
                color: '#aaa',
              },
              yaxis: {
                showgrid: true,
                automargin: true,
                gridcolor: '#333',
                zeroline: false,
                color: '#aaa',
                title: {
                text: metric[
                  Object.keys(metric).find(m =>
                  key.endsWith(m) ||
                  key.split('.').some(seg => seg === m)
                  ) ?? ''
                ] ?? '',
                font: { color: '#eee', size: 14 },
                standoff: 15
                },
              },
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%', height: '100%' }}
            />
            </div>
        ))}
      </div>
    </div>
  );
}

const groupbyOptions = [
  { label: 'Minute', value: 'minute' },
  { label: 'Hour', value: 'hour' },
  { label: 'Day', value: 'day' },
  { label: 'Month', value: 'month' },
  { label: 'Year', value: 'year' },
];
const typeOptions = [
  { label: 'Average', value: 'avg' },
  { label: 'Maximum', value: 'max' },
  { label: 'Minimum', value: 'min' },
];

// Add segmented control styles
const segmentedControlStyle = {
  display: 'inline-flex',
  borderRadius: '0.5rem',
  overflow: 'hidden',
  border: '1px solid #333',
  background: '#23272f',
};

const segmentedButtonStyle = (active: boolean) => ({
  padding: '0.5rem 1.2rem',
  background: active ? '#00e676' : 'transparent',
  color: active ? '#181818' : '#eee',
  border: 'none',
  outline: 'none',
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: '1rem',
  transition: 'background 0.2s, color 0.2s',
});

// TimeseriesGraph component
function TimeseriesGraph({
  title,
  endpoint,
  valueKey,
  deviceKey,
  periodKey,
  yLabel,
  multiDevice = false,
  refreshKey,
}: {
  title: string,
  endpoint: string,
  valueKey: string,
  deviceKey?: string,
  periodKey?: string,
  yLabel: string,
  multiDevice?: boolean,
  refreshKey?: number,
}) {
  const [groupby, setGroupby] = useState('minute'); // default to minute
  const [type, setType] = useState('avg'); // default to avg
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(
      `${endpoint}?type=${type}&groupby=${groupby}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    )
    .then(res => res.json())
    .then(json => {
      console.log("json: ", json);
      const key = Object.keys(json).find(k => k.endsWith('timeseries'));
      setData(json[key] || []);
      setLoading(false);
    });
  }, [endpoint, groupby, type, refreshKey]);

  // Prepare traces for Plotly
  let traces: any[] = [];
  if (multiDevice) {
    const devices = Array.from(new Set(data.map(d => d[deviceKey!])));
    traces = devices.map(device => ({
      x: data.filter(d => d[deviceKey!] === device).map(d => d[periodKey!]),
      y: data.filter(d => d[deviceKey!] === device).map(d => d[valueKey]),
      type: 'scatter',
      mode: 'lines+markers',
      name: device,
      line: { shape: 'spline' },
    }));
  } else {
    traces = [
      {
        x: data.map(d => d[periodKey!]),
        y: data.map(d => d[valueKey]),
        type: 'scatter',
        mode: 'lines+markers',
        line: { shape: 'spline', color: '#00e676', width: 3 },
        fill: 'tozeroy',
        fillcolor: 'rgba(0,230,118,0.1)',
        name: title,
      },
    ];
  }

  return (
    <div style={{
      background: '#23272f',
      border: '1px solid #333',
      borderRadius: '1rem',
      padding: '1.5rem',
      color: '#eee',
      boxShadow: '0 2px 8px #0008',
      maxWidth: 800,
      width: '150%',
    }}>
      <div style={{ fontWeight: 600, fontSize: '1.2rem', marginBottom: '1rem', color: '#00e676' }}>{title}</div>
      <div style={{ display: 'flex', gap: '2rem', marginBottom: '1rem', alignItems: 'center' }}>
        <div>
          <span style={{ marginRight: '0.5rem', fontWeight: 500 }}>Group by:</span>
          <span style={segmentedControlStyle}>
            {groupbyOptions.map(opt => (
              <button
                key={opt.value}
                style={segmentedButtonStyle(groupby === opt.value)}
                onClick={() => setGroupby(opt.value)}
                type="button"
              >
                {opt.label}
              </button>
            ))}
          </span>
        </div>
        <div>
          <span style={{ marginRight: '0.5rem', fontWeight: 500 }}>Type:</span>
          <span style={segmentedControlStyle}>
            {typeOptions.map(opt => (
              <button
                key={opt.value}
                style={segmentedButtonStyle(type === opt.value)}
                onClick={() => setType(opt.value)}
                type="button"
              >
                {opt.label}
              </button>
            ))}
          </span>
        </div>
      </div>
      {loading ? <div>Loading...</div> :
        <Plot
          data={traces}
          layout={{
            paper_bgcolor: '#23272f',
            plot_bgcolor: '#23272f',
            font: { color: '#eee' },
            width: 760,
            height: 320,
            margin: { t: 30, r: 10, l: 40, b: 30 },
            xaxis: {
              title: 'Time',
              color: '#aaa',
              showgrid: false,
              zeroline: false,
              type: 'date',
            },
            yaxis: {
              title: yLabel,
              color: '#aaa',
              showgrid: true,
              gridcolor: '#333',
              zeroline: false,
            },
            legend: { orientation: 'h', y: -0.2, font: { color: '#eee' } },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%', height: '100%' }}
        />
      }
    </div>
  );
}

function BarChartSingleMetric({
  title,
  endpoint,
  valueKey,
  labelKey,
  color = '#00e676',
}: {
  title: string,
  endpoint: string,
  valueKey: string,
  labelKey?: string,
  color?: string,
}) {
  const [type, setType] = useState('avg');
  const [time, setTime] = useState('hourly');
  const [data, setData] = useState<any>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${endpoint}?type=${type}&time=${time}`)
      .then(res => res.json())
      .then(json => {
        setData(json[valueKey] || {});
        setLoading(false);
      });
  }, [endpoint, type, time, valueKey]);

  // Prepare bar chart data
  const labels = Object.keys(data);
  const values = Object.values(data);

  return (
    <div style={{
      background: 'linear-gradient(135deg, #23272f 60%, #181818 100%)',
      border: '1px solid #222',
      borderRadius: '1.2rem',
      padding: '2rem 1.5rem 1.5rem 1.5rem',
      marginBottom: '2rem',
      color: '#eee',
      boxShadow: '0 4px 24px #000a',
      maxWidth: 900,
      width: '130%',
      minWidth: 0,
      boxSizing: 'border-box',
      overflow: 'hidden',
      wordBreak: 'break-word',
      transition: 'box-shadow 0.2s',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{ fontWeight: 700, fontSize: '1.3rem', marginBottom: '1rem', color, letterSpacing: '0.02em', textShadow: '0 2px 8px #0008', textAlign: 'center', width: '100%' }}>{title}</div>
      <div style={{ display: 'flex', gap: '2rem', marginBottom: '1.2rem', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
        <div>
          <span style={{ marginRight: '0.5rem', fontWeight: 500 }}>Time:</span>
          <span style={segmentedControlStyle}>
            {['hourly', 'daily', 'monthly', 'yearly'].map(opt => (
              <button
                key={opt}
                style={segmentedButtonStyle(time === opt)}
                onClick={() => setTime(opt)}
                type="button"
              >
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </button>
            ))}
          </span>
        </div>
        <div>
          <span style={{ marginRight: '0.5rem', fontWeight: 500 }}>Type:</span>
          <span style={segmentedControlStyle}>
            {typeOptions.map(opt => (
              <button
                key={opt.value}
                style={segmentedButtonStyle(type === opt.value)}
                onClick={() => setType(opt.value)}
                type="button"
              >
                {opt.label}
              </button>
            ))}
          </span>
        </div>
      </div>
      {loading ? <div>Loading...</div> :
        <div style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Plot
            data={[{
              x: labels,
              y: values,
              type: 'bar',
              marker: { color },
            }]}
            layout={{
              paper_bgcolor: '#181818',
              plot_bgcolor: '#181818',
              font: { color: '#eee' },
              width: undefined,
              height: 320,
              margin: { t: 30, r: 10, l: 40, b: 80 },
              xaxis: {
                title: 'Device',
                color: '#aaa',
                tickangle: -30,
                automargin: true,
              },
              yaxis: {
                title: title,
                color: '#aaa',
                showgrid: true,
                gridcolor: '#333',
                zeroline: false,
              },
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      }
    </div>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState<any>(null);
  const [history, setHistory] = useState<Record<string, number[]>>({});
  const historyRef = useRef<Record<string, number[]>>({});
  const [refreshKey, setRefreshKey] = useState(0);

  const unitMappings: Record<string, string> = {
    // CPU
    'user_time': 'Seconds',
    'system_time': 'Seconds',
    'idle_time': 'Seconds',
    'percent': 'Percent (%)',
    // Memory, Swap Memory
    'available_memory': 'Bytes',
    'used_memory': 'Bytes',
    'memory_percent_usage': 'Percent (%)',
    'free_memory': 'Bytes',
    'percent_usage': 'Percent (%)',
    // Disk Usage
    'total': 'Bytes',
    'used': 'Bytes',
    'free': 'Bytes',
    //'percent': 'Percent (%)',
    // IO
    'read_count': 'Count',
    'write_count': 'Count',
    'read_bytes': 'Bytes',
    'write_bytes': 'Bytes',
    'read_time': 'Ms',
    'write_time': 'Ms',
    // Ping
    'ping': 'Ms'
    // GPU (example, add as needed)
  };


  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/metrics");
    ws.onopen = () => {
      console.log("Connected");
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMetrics(data);
        // Update history for each numeric metric
        const flat = flattenMetrics(data);
        const newHistory = { ...historyRef.current };
        for (const [key, value] of Object.entries(flat)) {
          if (!newHistory[key]) newHistory[key] = [];
          newHistory[key].push(value);
          // Limit history length for performance
          if (newHistory[key].length > 100) newHistory[key].shift();
        }
        historyRef.current = newHistory;
        setHistory({ ...newHistory });
        console.log("history ref: ", historyRef.current);
      } catch {
        setMetrics({ message: event.data });
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div
      style={{
        minWidth: '95vw',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #181818 0%, #23272f 100%)',
        color: '#eee',
        fontFamily: 'Inter, Segoe UI, Arial, sans-serif',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '2rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          maxWidth: '1400px',
          width: 'auto',
        }}
      >
        <h1 style={{
          textAlign: 'center',
          fontWeight: 700,
          fontSize: '2.5rem',
          margin: '2rem 0 1rem 0',
          letterSpacing: '0.05em',
          color: '#00e676',
          textShadow: '0 2px 8px #0008'
        }}>
          Web Specs
        </h1>
        <button
          style={{
            marginBottom: '2rem',
            padding: '0.7rem 2rem',
            fontSize: '1.1rem',
            fontWeight: 600,
            borderRadius: '0.7rem',
            border: 'none',
            background: '#00e676',
            color: '#181818',
            boxShadow: '0 2px 8px #0008',
            cursor: 'pointer',
            transition: 'background 0.2s, color 0.2s',
          }}
          onClick={() => setRefreshKey(k => k + 1)}
        >
          Refresh Timeseries Graphs
        </button>
        {/* Bar charts for CPU, Memory, Swap, IO metrics */}
        <div style={{ width: '100%', marginBottom: '2rem' }}>
          <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>CPU Usage (%)</h2>
            <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              width: '100%',
            }}
            >
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              width: '100%',
            }}>
              <BarChartSingleMetric
              title=""
              endpoint="http://127.0.0.1:8000/cpu/percent"
              valueKey="cpu_percent"
              color="#00e676"
              />
            </div>
            </div>
        </div>
        <div style={{ width: '100%', marginBottom: '2rem' }}>
          <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>Memory</h2>
          <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '15rem', // smaller gap
              justifyItems: 'center', // center items horizontally
              alignItems: 'center',    // center items vertically
              margin: '0 auto',        // center grid in parent
            }}>
            <BarChartSingleMetric
              title="Memory Usage (%)"
              endpoint="http://127.0.0.1:8000/memory/percent"
              valueKey="memory_percent"
              color="#29b6f6"
            />
            <BarChartSingleMetric
              title="Swap Memory Usage (%)"
              endpoint="http://127.0.0.1:8000/swap_memory/percent"
              valueKey="memory_percent"
              color="#ab47bc"
            />
          </div>
        </div>
        {/* Bar charts for IO metrics */}
        <div style={{ width: '100%', marginBottom: '2rem' }}>
          <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>IO Bytes</h2>
          <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '15rem', // smaller gap
              justifyItems: 'center', // center items horizontally
              alignItems: 'center',    // center items vertically
              margin: '0 auto',        // center grid in parent
            }}>
            <BarChartSingleMetric
              title="IO Read Bytes"
              endpoint="http://127.0.0.1:8000/io/read/bytes"
              valueKey="io_read_bytes"
              color="#29b6f6"
            />
            <BarChartSingleMetric
              title="IO Write Bytes"
              endpoint="http://127.0.0.1:8000/io/write/bytes"
              valueKey="io_write_bytes"
              color="#ef5350"
            />
          </div>
        </div>
        <div style={{ width: '100%', marginBottom: '2rem' }}>
          <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>IO Time</h2>
          <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '15rem', // smaller gap
              justifyItems: 'center', // center items horizontally
              alignItems: 'center',    // center items vertically
              margin: '0 auto',        // center grid in parent
            }}>
            <BarChartSingleMetric
              title="IO Read Time"
              endpoint="http://127.0.0.1:8000/io/read/time"
              valueKey="io_read_time"
              color="#ab47bc"
            />
            <BarChartSingleMetric
              title="IO Write Time"
              endpoint="http://127.0.0.1:8000/io/write/time"
              valueKey="io_write_time"
              color="#ffb300"
            />
          </div>
        </div>
        {/* Timeseries graphs */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
            gap: '20rem',
            width: '100%',
            justifyItems: 'center',
            justifyContent: 'center',
            margin: '0 auto',
          }}
        >
          <TimeseriesGraph
            title="Memory Usage (%)"
            endpoint="http://127.0.0.1:8000/memory/percent/timeseries"
            valueKey="value"
            periodKey="period"
            yLabel="Percent (%)"
            refreshKey={refreshKey}
          />
          <TimeseriesGraph
            title="Swap Memory Usage (%)"
            endpoint="http://127.0.0.1:8000/swap_memory/percent/timeseries"
            valueKey="value"
            periodKey="period"
            yLabel="Percent (%)"
            refreshKey={refreshKey}
          />
          <TimeseriesGraph
            title="CPU Usage (%)"
            endpoint="http://127.0.0.1:8000/cpu/percent/timeseries"
            valueKey="value"
            periodKey="period"
            deviceKey="core_id"
            yLabel="Percent (%)"
            multiDevice={true}
            refreshKey={refreshKey}
          />
          <TimeseriesGraph
            title="IO Read Bytes"
            endpoint="http://127.0.0.1:8000/io/read/bytes/timeseries"
            valueKey="value"
            periodKey="period"
            deviceKey="device_name"
            yLabel="Bytes"
            multiDevice={true}
            refreshKey={refreshKey}
          />
          <TimeseriesGraph
            title="IO Write Bytes"
            endpoint="http://127.0.0.1:8000/io/write/bytes/timeseries"
            valueKey="value"
            periodKey="period"
            deviceKey="device_name"
            yLabel="Bytes"
            multiDevice={true}
            refreshKey={refreshKey}
          />
          <TimeseriesGraph
            title="IO Read Time"
            endpoint="http://127.0.0.1:8000/io/read/time/timeseries"
            valueKey="value"
            periodKey="period"
            deviceKey="device_name"
            yLabel="Ms"
            multiDevice={true}
            refreshKey={refreshKey}
          />
          <TimeseriesGraph
            title="IO Write Time"
            endpoint="http://127.0.0.1:8000/io/write/time/timeseries"
            valueKey="value"
            periodKey="period"
            deviceKey="device_name"
            yLabel="Ms"
            multiDevice={true}
            refreshKey={refreshKey}
          />
        </div>
        {/* Live metrics groups */}
        {metrics && (
          <>
            {metrics.cpu && <MetricsGroup metric={unitMappings} group="cpu" title="CPU" data={metrics.cpu} history={history} />}
            {metrics.memory && <MetricsGroup metric={unitMappings} group="memory" title="Memory" data={metrics.memory} history={history} />}
            {metrics.swap_memory && <MetricsGroup metric={unitMappings} group="swap_memory" title="Swap Memory" data={metrics.swap_memory} history={history} />}
            {metrics.disk_usage && <MetricsGroup metric={unitMappings} group="disk_usage" title="Disk Usage" data={metrics.disk_usage} history={history} />}
            {metrics.io && <MetricsGroup metric={unitMappings} group="io" title="IO" data={metrics.io} history={history} />}
            {metrics.ping !== undefined && <MetricsGroup metric={unitMappings} group="ping" title="ping" data={{ ping: metrics.ping }} history={history} />}
            {metrics.gpu && <MetricsGroup metric={unitMappings} group="gpu" title="gpu" data={metrics.gpu} history={history} />}
          </>
        )}
      </div>
    </div>
  );
}
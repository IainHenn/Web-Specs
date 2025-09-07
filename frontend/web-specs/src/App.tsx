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

export default function App() {
  const [metrics, setMetrics] = useState<any>(null);
  const [history, setHistory] = useState<Record<string, number[]>>({});
  const historyRef = useRef<Record<string, number[]>>({});

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
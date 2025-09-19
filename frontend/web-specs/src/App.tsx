import { useState, useEffect, useRef } from 'react'
import Plot from 'react-plotly.js'
import './App.css'

function NotifIcon({ onClick }: { onClick: () => void }) {
  return (
    <button
      style={{
        position: 'absolute',
        top: '2rem',
        left: '2rem',
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        zIndex: 1000,
      }}
      onClick={onClick}
      title="Notification Settings"
    >
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="15" stroke="#00e676" strokeWidth="2" fill="#23272f" />
        <path d="M10 12v6c0 2.2 1.8 4 4 4s4-1.8 4-4v-6" stroke="#00e676" strokeWidth="2" fill="none" />
        <circle cx="16" cy="22" r="2" fill="#00e676" />
      </svg>
    </button>
  );
}

function NotifSettingsModal({ open, onClose }: { open: boolean, onClose: () => void }) {
  const [settings, setSettings] = useState<any>(null);
  const [edited, setEdited] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      fetch('http://127.0.0.1:8000/notification-settings')
        .then(res => res.json())
        .then(json => {
          setSettings(json);
          setEdited(JSON.parse(JSON.stringify(json)));
          setLoading(false);
        });
    }
  }, [open]);

  function handleChange(path: string[], value: any) {
    const newEdited = JSON.parse(JSON.stringify(edited));
    let obj = newEdited;
    for (let i = 0; i < path.length - 1; i++) {
      obj = obj[path[i]];
    }
    obj[path[path.length - 1]] = value;
    setEdited(newEdited);
  }

  function renderFields(obj: any, path: string[] = []) {
    return Object.entries(obj).map(([key, value]) => {
      const fullPath = [...path, key];
      if (typeof value === 'object' && value !== null) {
        return (
          <div key={fullPath.join('.')} style={{ marginBottom: '1rem', marginLeft: path.length * 16 }}>
            <div style={{ fontWeight: 600, color: '#00e676', marginBottom: '0.5rem' }}>{key}</div>
            {renderFields(value, fullPath)}
          </div>
        );
      } else if (typeof value === 'number' || value === "") {
        // Get value from edited using fullPath
        let editedValue = edited;
        for (let i = 0; i < fullPath.length; i++) {
          if (editedValue && editedValue[fullPath[i]] !== undefined) {
            editedValue = editedValue[fullPath[i]];
          } else {
            editedValue = undefined;
            break;
          }
        }
        return (
          <div key={fullPath.join('.')} style={{ marginBottom: '1rem', marginLeft: path.length * 16 }}>
            <label style={{ color: '#eee', marginRight: '1rem' }}>{key}:</label>
            <input
              type="number"
              step="0.01"
              value={editedValue !== undefined && editedValue !== "" ? editedValue : ""}
              onChange={e => handleChange(fullPath, e.target.value === "" ? "" : parseFloat(e.target.value))}
              style={{ width: 80, padding: '0.3rem', borderRadius: '0.4rem', border: '1px solid #00e676', background: '#23272f', color: '#eee' }}
              placeholder={value === "" ? "Enter value" : undefined}
            />
          </div>
        );
      } else {
        return null;
      }
    });
  }

  function handleSave() {
    setSaving(true);
    fetch('http://127.0.0.1:8000/notification-settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ changes: edited }),
    }).then(() => {
      setSaving(false);
      onClose();
    });
  }

  if (!open) return null;
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      background: 'rgba(0,0,0,0.7)',
      zIndex: 2000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{ background: '#23272f', borderRadius: '1.2rem', padding: '2rem', minWidth: 400, maxWidth: 600, color: '#eee', boxShadow: '0 4px 24px #000a', maxHeight: '70vh', overflowY: 'auto' }}>
        <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 700 }}>Notification Settings</h2>
        {loading ? <div>Loading...</div> : (
          <form onSubmit={e => { e.preventDefault(); handleSave(); }}>
            {renderFields(settings)}
            <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem', justifyContent: 'flex-end' }}>
              <button type="button" onClick={onClose} style={{ padding: '0.7rem 2rem', borderRadius: '0.7rem', border: 'none', background: '#333', color: '#eee', fontWeight: 600, cursor: 'pointer' }}>Cancel</button>
              <button type="submit" disabled={saving} style={{ padding: '0.7rem 2rem', borderRadius: '0.7rem', border: 'none', background: '#00e676', color: '#181818', fontWeight: 600, cursor: 'pointer' }}>{saving ? 'Saving...' : 'Save'}</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

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
  refreshKey,
}: {
  title: string,
  endpoint: string,
  valueKey: string,
  labelKey?: string,
  color?: string,
  refreshKey?: number,
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
        let val = json[valueKey];
        if (typeof val === 'number') {
          setData({ [title]: val });
        } else {
          setData(val || {});
        }
        setLoading(false);
      });
  }, [endpoint, type, time, valueKey, refreshKey]);

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

function Page({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ width: '100%', maxWidth: 1200, margin: '0 auto', padding: '2rem 0' }}>
      {children}
    </div>
  );
}

function EmailIcon({ onClick }: { onClick: () => void }) {
  return (
    <button
      style={{
        position: 'absolute',
        top: '5rem',
        left: '2rem',
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        zIndex: 1000,
      }}
      onClick={onClick}
      title="Email Settings"
    >
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <rect x="4" y="8" width="24" height="16" rx="3" fill="#23272f" stroke="#00e676" strokeWidth="2" />
        <polyline points="4,8 16,20 28,8" fill="none" stroke="#00e676" strokeWidth="2" />
      </svg>
    </button>
  );
}

function EmailSettingsModal({ open, onClose }: { open: boolean, onClose: () => void }) {
  const [hostEmail, setHostEmail] = useState('');
  const [appPassword, setAppPassword] = useState('');
  const [subEmail, setSubEmail] = useState('');
  const [subStatus, setSubStatus] = useState('');
  const [hostStatus, setHostStatus] = useState('');
  const [loading, setLoading] = useState(false);

  function handleAddHostEmail(e: any) {
    e.preventDefault();
    setLoading(true);
    fetch('http://127.0.0.1:8000/host-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: hostEmail, app_password: appPassword })
    })
      .then(res => res.json())
      .then(json => {
        console.log(json);
        setHostStatus(json.success ? 'Host email saved!' : json.error || 'Error');
        setLoading(false);
      });
  }

  function handleAddSubEmail(e: any) {
    e.preventDefault();
    setLoading(true);
    fetch(`http://127.0.0.1:8000/emails/${encodeURIComponent(subEmail)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
      .then(res => res.json())
      .then(json => {
        setSubStatus(json.success ? 'Subscription email added!' : json.error || 'Error');
        setLoading(false);
      });
  }

  if (!open) return null;
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      background: 'rgba(0,0,0,0.7)',
      zIndex: 2000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{ background: '#23272f', borderRadius: '1.2rem', padding: '2rem', minWidth: 400, maxWidth: 600, color: '#eee', boxShadow: '0 4px 24px #000a', maxHeight: '70vh', overflowY: 'auto' }}>
        <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 700 }}>Email Settings</h2>
        <form onSubmit={handleAddHostEmail} style={{ marginBottom: '2rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ color: '#eee', marginRight: '1rem' }}>Host Email:</label>
            <input type="email" value={hostEmail} onChange={e => setHostEmail(e.target.value)} style={{ width: 220, padding: '0.3rem', borderRadius: '0.4rem', border: '1px solid #00e676', background: '#23272f', color: '#eee' }} required />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ color: '#eee', marginRight: '1rem' }}>App Password:</label>
            <input type="password" value={appPassword} onChange={e => setAppPassword(e.target.value)} style={{ width: 220, padding: '0.3rem', borderRadius: '0.4rem', border: '1px solid #00e676', background: '#23272f', color: '#eee' }} required />
          </div>
          <button type="submit" style={{ padding: '0.7rem 2rem', borderRadius: '0.7rem', border: 'none', background: '#00e676', color: '#181818', fontWeight: 600, cursor: 'pointer' }}>Save Host Email</button>
          {hostStatus && <div style={{ color: hostStatus.includes('saved') ? '#00e676' : '#ef5350', marginTop: '0.5rem' }}>{hostStatus}</div>}
        </form>
        <form onSubmit={handleAddSubEmail}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ color: '#eee', marginRight: '1rem' }}>Subscription Email:</label>
            <input type="email" value={subEmail} onChange={e => setSubEmail(e.target.value)} style={{ width: 220, padding: '0.3rem', borderRadius: '0.4rem', border: '1px solid #00e676', background: '#23272f', color: '#eee' }} required />
          </div>
          <button type="submit" style={{ padding: '0.7rem 2rem', borderRadius: '0.7rem', border: 'none', background: '#00e676', color: '#181818', fontWeight: 600, cursor: 'pointer' }}>Add Subscription Email</button>
          {subStatus && <div style={{ color: subStatus.includes('added') ? '#00e676' : '#ef5350', marginTop: '0.5rem' }}>{subStatus}</div>}
        </form>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem', justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{ padding: '0.7rem 2rem', borderRadius: '0.7rem', border: 'none', background: '#333', color: '#eee', fontWeight: 600, cursor: 'pointer' }}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState<any>(null);
  const [history, setHistory] = useState<Record<string, number[]>>({});
  const historyRef = useRef<Record<string, number[]>>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedPage, setSelectedPage] = useState('realtime');
  const [barRefreshKey, setBarRefreshKey] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);

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

  const menuItems = [
    { label: 'Real Time Data', value: 'realtime' },
    { label: 'Past Data (Time Series)', value: 'timeseries' },
    { label: 'Past Data (Bar Charts)', value: 'barcharts' },
    { label: 'Past Data (Distributions)', value: 'distributions' },
    { label: 'Static Info', value: 'staticinfo' },
  ];

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
        position: 'relative',
      }}
    >
      <NotifIcon onClick={() => setNotifOpen(true)} />
      <EmailIcon onClick={() => setEmailOpen(true)} />
      <NotifSettingsModal open={notifOpen} onClose={() => setNotifOpen(false)} />
      <EmailSettingsModal open={emailOpen} onClose={() => setEmailOpen(false)} />
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
        {/* Overhead menu */}
        <div style={{ display: 'flex', gap: '2rem', marginBottom: '2rem', justifyContent: 'center' }}>
          {menuItems.map(item => (
            <button
              key={item.value}
              style={{
                padding: '0.7rem 2rem',
                fontSize: '1.1rem',
                fontWeight: 600,
                borderRadius: '0.7rem',
                border: selectedPage === item.value ? '2px solid #00e676' : 'none',
                background: selectedPage === item.value ? '#00e676' : '#23272f',
                color: selectedPage === item.value ? '#181818' : '#eee',
                boxShadow: '0 2px 8px #0008',
                cursor: 'pointer',
                transition: 'background 0.2s, color 0.2s',
              }}
              onClick={() => setSelectedPage(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {/* Pages */}
        {selectedPage === 'realtime' && (
          <Page>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '2.5rem',
              width: '100%',
              maxWidth: '1100px',
              margin: '0 auto',
            }}>
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
          </Page>
        )}
        {selectedPage === 'timeseries' && (
          <Page>
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
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '3rem',
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
          </Page>
        )}
        {selectedPage === 'barcharts' && (
          <Page>
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
              onClick={() => setBarRefreshKey(k => k + 1)}
            >
              Refresh Bar Charts
            </button>
            <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>CPU Usage (%)</h2>
            <BarChartSingleMetric
              title="CPU Usage (%)"
              endpoint="http://127.0.0.1:8000/cpu/percent"
              valueKey="cpu_percent"
              color="#00e676"
              refreshKey={barRefreshKey}
            />
            <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>Memory</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15rem', justifyItems: 'center', alignItems: 'center', margin: '0 auto' }}>
              <BarChartSingleMetric
                title="Memory Usage (%)"
                endpoint="http://127.0.0.1:8000/memory/percent"
                valueKey="memory_percent"
                color="#29b6f6"
                refreshKey={barRefreshKey}
              />
              <BarChartSingleMetric
                title="Swap Memory Usage (%)"
                endpoint="http://127.0.0.1:8000/swap_memory/percent"
                valueKey="memory_percent"
                color="#ab47bc"
                refreshKey={barRefreshKey}
              />
            </div>
            <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>IO Bytes</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15rem', justifyItems: 'center', alignItems: 'center', margin: '0 auto' }}>
              <BarChartSingleMetric
                title="IO Read Bytes"
                endpoint="http://127.0.0.1:8000/io/read/bytes"
                valueKey="io_read_bytes"
                color="#29b6f6"
                refreshKey={barRefreshKey}
              />
              <BarChartSingleMetric
                title="IO Write Bytes"
                endpoint="http://127.0.0.1:8000/io/write/bytes"
                valueKey="io_write_bytes"
                color="#ef5350"
                refreshKey={barRefreshKey}
              />
            </div>
            <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>IO Time</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15rem', justifyItems: 'center', alignItems: 'center', margin: '0 auto' }}>
              <BarChartSingleMetric
                title="IO Read Time"
                endpoint="http://127.0.0.1:8000/io/read/time"
                valueKey="io_read_time"
                color="#ab47bc"
                refreshKey={barRefreshKey}
              />
              <BarChartSingleMetric
                title="IO Write Time"
                endpoint="http://127.0.0.1:8000/io/write/time"
                valueKey="io_write_time"
                color="#ffb300"
                refreshKey={barRefreshKey}
              />
            </div>
          </Page>
        )}
        {selectedPage === 'distributions' && (
          <DistributionPage />
        )}
        {selectedPage === 'staticinfo' && (
          <StaticInfoPage />
        )}
      </div>
    </div>
  );
}

function StaticInfoPage() {
  const [info, setInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/system/static-info')
      .then(res => res.json())
      .then(json => {
        const body = JSON.parse(json[0].body);
        console.log(body['static-info']);
        setInfo(body['static-info']);
        setLoading(false);
      });
  }, []);

  return (
    <Page>
      <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>Static System Info</h2>
      {loading ? <div>Loading...</div> : (
        <pre style={{ background: '#23272f', color: '#eee', padding: '2rem', borderRadius: '1rem', fontSize: '1.1rem', overflowX: 'auto' }}>
          {JSON.stringify(info, null, 2)}
        </pre>
      )}
    </Page>
  );
}

function DensityPlot({ title, data, color }: {
  title: string,
  data: number[],
  color?: string,
}) {
  return (
    <div style={{
      background: '#23272f',
      border: '1px solid #333',
      borderRadius: '1rem',
      padding: '2rem 1.5rem 1.5rem 1.5rem',
      marginBottom: '2rem',
      color: '#eee',
      boxShadow: '0 4px 24px #000a',
      maxWidth: 900,
      width: '100%',
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
      <Plot
        data={[{
          x: data,
          type: 'histogram',
          histnorm: 'probability density',
          marker: { color },
          opacity: 0.7,
          name: title,
        }]}
        layout={{
          paper_bgcolor: '#23272f',
          plot_bgcolor: '#23272f',
          font: { color: '#eee' },
          width: undefined,
          height: 320,
          margin: { t: 30, r: 10, l: 40, b: 80 },
          xaxis: {
            title: title,
            color: '#aaa',
            automargin: true,
          },
          yaxis: {
            title: 'Density',
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
  );
}

function CPUDistributionPlots({ time, refreshKey }: { time: string, refreshKey?: number }) {
  const [data, setData] = useState<any>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`http://127.0.0.1:8000/cpu/percent/distribution?time=${time}`)
      .then(res => res.json())
      .then(json => {
        setData(json['cpu_percent_distribution'] || {});
        setLoading(false);
      });
  }, [time, refreshKey]);

  const colors = [
    '#00e676', '#29b6f6', '#ab47bc', '#ef5350', '#ffb300', '#8d6e63', '#26a69a', '#d4e157', '#5c6bc0', '#ec407a', '#789262', '#ffa726', '#7e57c2', '#66bb6a', '#ff7043', '#26c6da', '#c62828', '#ad1457', '#6d4c41', '#0097a7'
  ];
  const coreKeys = Object.keys(data);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem' }}>
      {loading ? <div>Loading...</div> :
        coreKeys.map((core, idx) => (
          <DensityPlot
            key={core}
            title={`CPU Core ${core} Usage (%)`}
            data={data[core]}
            color={colors[idx % colors.length]}
          />
        ))
      }
    </div>
  );
}

function DistributionPage() {
  const [time, setTime] = useState('hour');
  const [memoryData, setMemoryData] = useState<number[]>([]);
  const [swapData, setSwapData] = useState<number[]>([]);
  const [ioReadData, setIOReadData] = useState<any>({});
  const [ioWriteData, setIOWriteData] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`http://127.0.0.1:8000/memory/percent/distribution?time=${time}`).then(res => res.json()),
      fetch(`http://127.0.0.1:8000/swap_memory/percent/distribution?time=${time}`).then(res => res.json()),
      fetch(`http://127.0.0.1:8000/io/read/bytes/distribution?time=${time}`).then(res => res.json()),
      fetch(`http://127.0.0.1:8000/io/write/bytes/distribution?time=${time}`).then(res => res.json()),
    ]).then(([mem, swap, ioRead, ioWrite]) => {
      setMemoryData(mem.memory_percent_distribution || []);
      setSwapData(swap.swap_memory_percent_distribution || []);
      setIOReadData(ioRead.io_read_bytes_distribution || {});
      setIOWriteData(ioWrite.io_write_bytes_distribution || {});
      setLoading(false);
    });
  }, [time, refreshKey]);

  return (
    <Page>
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
        Refresh Distributions
      </button>
      <div style={{ display: 'flex', gap: '2rem', marginBottom: '1.2rem', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
        <div>
          <span style={{ marginRight: '0.5rem', fontWeight: 500 }}>Time:</span>
          <span style={segmentedControlStyle}>
            {['hour', 'day', 'month', 'year', 'overall'].map(opt => (
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
      </div>
      {loading ? <div>Loading...</div> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3rem', width: '100%', maxWidth: '1400px', margin: '0 auto' }}>
          <div>
            <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>Memory</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '2rem' }}>
              <DensityPlot title="Memory Usage (%)" data={memoryData} color="#29b6f6" />
              <DensityPlot title="Swap Memory Usage (%)" data={swapData} color="#ab47bc" />
            </div>
          </div>
          <div>
            {/*<h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>CPU</h2>*/}
            {/*<CPUDistributionPlots time={time} refreshKey={refreshKey} />*/}
          </div>
          <div>
            <h2 style={{ color: '#00e676', marginBottom: '1rem', fontWeight: 600 }}>IO</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '2rem' }}>
              {Object.entries(ioReadData).map(([dev, arr]) => (
                <DensityPlot key={dev} title={`IO Read Bytes (${dev})`} data={arr} color="#29b6f6" />
              ))}
              {Object.entries(ioWriteData).map(([dev, arr]) => (
                <DensityPlot key={dev} title={`IO Write Bytes (${dev})`} data={arr} color="#ef5350" />
              ))}
            </div>
          </div>
        </div>
      )}
    </Page>
  );
}
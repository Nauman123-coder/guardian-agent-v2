import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API = '';  // uses CRA proxy to localhost:8000

export function useStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/stats`);
      setStats(res.data);
    } catch (e) { console.error('Stats fetch failed', e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); const t = setInterval(fetch, 5000); return () => clearInterval(t); }, [fetch]);
  return { stats, loading, refresh: fetch };
}

export function useIncidents(filters = {}) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const params = new URLSearchParams(filters).toString();
      const res = await axios.get(`${API}/api/incidents?${params}`);
      setIncidents(res.data.incidents || []);
    } catch (e) { console.error('Incidents fetch failed', e); }
    finally { setLoading(false); }
  }, [JSON.stringify(filters)]);

  useEffect(() => { fetch(); const t = setInterval(fetch, 3000); return () => clearInterval(t); }, [fetch]);
  return { incidents, loading, refresh: fetch };
}

export function useIncident(id) {
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    if (!id) return;
    try {
      const res = await axios.get(`${API}/api/incidents/${id}`);
      setIncident(res.data);
    } catch (e) { console.error('Incident fetch failed', e); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { fetch(); }, [fetch]);
  return { incident, loading, refresh: fetch };
}

export function useWebSocket(incidentId) {
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    const wsUrl = incidentId
      ? `ws://localhost:8000/ws/incidents/${incidentId}`
      : `ws://localhost:8000/ws/incidents`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setEvents(prev => [...prev.slice(-99), data]);
      } catch {}
    };
    ws.onerror = (e) => console.warn('WS error', e);

    return () => ws.close();
  }, [incidentId]);

  return { events };
}

export async function submitLog(rawLog, logSource = 'dashboard') {
  const res = await axios.post(`${API}/api/incidents`, { raw_log: rawLog, log_source: logSource });
  return res.data;
}

export async function approveIncident(id) {
  const res = await axios.post(`${API}/api/incidents/${id}/approve`);
  return res.data;
}

export async function denyIncident(id) {
  const res = await axios.post(`${API}/api/incidents/${id}/deny`);
  return res.data;
}

export async function getSystemState() {
  const res = await axios.get(`${API}/api/state`);
  return res.data;
}
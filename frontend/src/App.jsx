import React, { useState, useEffect } from 'react';
import './index.css';
import Dashboard from './pages/Dashboard';
import IncidentDetail from './pages/IncidentDetail';
import SubmitLog from './pages/SubmitLog';
import SystemState from './pages/SystemState';
import Login from './pages/Login';

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: '◈' },
  { id: 'submit', label: 'Submit Log', icon: '⊕' },
  { id: 'state', label: 'System State', icon: '⬡' },
];

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [connected, setConnected] = useState(false);
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const authEnabled = true // Set to true when GUARDIAN_AUTH_ENABLED=true in .env

  useEffect(() => {
    if (!authEnabled) { setAuthChecked(true); setUser('operator'); return; }
    const token = localStorage.getItem('guardian_token');
    const savedUser = localStorage.getItem('guardian_user');
    if (token && savedUser) { setUser(savedUser); }
    setAuthChecked(true);
  }, []);

  useEffect(() => {
    const check = () => fetch('/api/stats').then(() => setConnected(true)).catch(() => setConnected(false));
    check();
    const t = setInterval(check, 10000);
    return () => clearInterval(t);
  }, []);

  const openIncident = (id) => {
    if (!id) return;
    setSelectedIncident(id);
    setPage('incident');
  };

  const handleLogout = () => {
    localStorage.removeItem('guardian_token');
    localStorage.removeItem('guardian_user');
    setUser(null);
  };

  if (!authChecked) return null;
  if (authEnabled && !user) return <Login onLogin={setUser} />;

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      {/* Nav */}
      <nav style={{
        display: 'flex', alignItems: 'center',
        background: 'rgba(5,8,16,0.95)',
        borderBottom: '1px solid var(--border)',
        padding: '0 24px',
        position: 'sticky', top: 0, zIndex: 100,
        backdropFilter: 'blur(10px)',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginRight: 40, padding: '14px 0' }}>
          <div style={{
            width: 32, height: 32,
            background: 'linear-gradient(135deg, var(--cyan), var(--purple))',
            clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
            boxShadow: 'var(--glow-cyan)',
          }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 16, color: 'var(--cyan)', letterSpacing: '0.1em', textShadow: 'var(--glow-cyan)' }}>GUARDIAN</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.15em' }}>v2.1</span>
        </div>

        {/* Nav links */}
        {NAV.map(n => (
          <button key={n.id} onClick={() => setPage(n.id)} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            padding: '18px 20px',
            color: page === n.id ? 'var(--cyan)' : 'var(--text-secondary)',
            fontFamily: 'var(--font-ui)', fontSize: 13, fontWeight: 600, letterSpacing: '0.05em',
            borderBottom: page === n.id ? '2px solid var(--cyan)' : '2px solid transparent',
            transition: 'all 0.15s',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', opacity: 0.7 }}>{n.icon}</span>
            {n.label.toUpperCase()}
          </button>
        ))}

        {/* Right side */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: connected ? 'var(--green)' : 'var(--red)',
              boxShadow: connected ? 'var(--glow-green)' : 'var(--glow-red)',
            }} />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
              {connected ? 'API ONLINE' : 'API OFFLINE'}
            </span>
          </div>
          {authEnabled && user && (
            <button onClick={handleLogout} style={{
              background: 'none', border: '1px solid var(--border)', borderRadius: 4,
              color: 'var(--text-dim)', cursor: 'pointer', padding: '5px 12px',
              fontFamily: 'var(--font-mono)', fontSize: 11,
            }}>
              {user} ✕
            </button>
          )}
        </div>
      </nav>

      {/* Page */}
      <main style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
        {page === 'dashboard' && <Dashboard onSelectIncident={openIncident} />}
        {page === 'incident' && selectedIncident
          ? <IncidentDetail id={selectedIncident} onBack={() => setPage('dashboard')} />
          : page === 'incident' && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 400, gap: 16 }}>
                <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--red)', fontSize: 14 }}>⚠ No incident selected</div>
                <button className="btn btn-primary" onClick={() => setPage('dashboard')}>← Back to Dashboard</button>
              </div>
            )
        }
        {page === 'submit' && <SubmitLog onSubmitted={(id) => { setSelectedIncident(id); setPage('incident'); }} />}
        {page === 'state' && <SystemState />}
      </main>
    </div>
  );
}
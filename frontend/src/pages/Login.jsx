import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || '';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!username || !password) { setError('Enter username and password'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await axios.post(`${API_BASE}/api/auth/login`, { username, password });
      localStorage.setItem('guardian_token', res.data.access_token);
      localStorage.setItem('guardian_user', res.data.username);
      onLogin(res.data.username);
    } catch (e) {
      setError(e.response?.data?.detail || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-deep)',
      position: 'relative',
    }}>
      {/* Background glow */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,100,200,0.08) 0%, transparent 70%)',
      }} />

      <div style={{ width: '100%', maxWidth: 420, padding: '0 24px', position: 'relative', zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            width: 64, height: 64, margin: '0 auto 16px',
            background: 'linear-gradient(135deg, var(--cyan), var(--purple))',
            clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
            boxShadow: '0 0 40px rgba(0, 212, 255, 0.4)',
          }} />
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, color: 'var(--cyan)', letterSpacing: '0.15em', textShadow: 'var(--glow-cyan)' }}>
            GUARDIAN
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', letterSpacing: '0.1em', marginTop: 4 }}>
            AUTONOMOUS THREAT HUNTER v2
          </div>
        </div>

        {/* Login card */}
        <div className="panel" style={{ padding: 32 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 24, textAlign: 'center' }}>
            OPERATOR AUTHENTICATION
          </div>

          {/* Username */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.1em', display: 'block', marginBottom: 6 }}>
              USERNAME
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="admin"
              style={{
                width: '100%', padding: '10px 14px',
                background: 'var(--bg-deep)',
                border: '1px solid var(--border)',
                borderRadius: 4,
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                outline: 'none',
                boxSizing: 'border-box',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--cyan-dim)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: 24 }}>
            <label style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.1em', display: 'block', marginBottom: 6 }}>
              PASSWORD
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="••••••••"
              style={{
                width: '100%', padding: '10px 14px',
                background: 'var(--bg-deep)',
                border: '1px solid var(--border)',
                borderRadius: 4,
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                outline: 'none',
                boxSizing: 'border-box',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--cyan-dim)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'}
            />
          </div>

          {error && (
            <div style={{ padding: '10px 14px', background: 'rgba(255,51,85,0.1)', border: '1px solid rgba(255,51,85,0.3)', borderRadius: 4, color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 12, marginBottom: 16 }}>
              ✕ {error}
            </div>
          )}

          <div
            onClick={handleSubmit}
            style={{
              width: '100%', padding: '12px',
              background: loading ? 'rgba(0,212,255,0.08)' : 'rgba(0,212,255,0.15)',
              color: 'var(--cyan)', border: '1px solid rgba(0,212,255,0.4)',
              borderRadius: 4, cursor: 'pointer',
              fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700,
              letterSpacing: '0.1em', textAlign: 'center',
              boxSizing: 'border-box',
            }}
          >
            {loading ? '⟳ AUTHENTICATING...' : '→ ACCESS SYSTEM'}
          </div>

          <div style={{ marginTop: 16, fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)', textAlign: 'center' }}>
            Default: admin / guardian123 — change in .env
          </div>
        </div>
      </div>
    </div>
  );
}
import React, { useState, useEffect } from 'react';
import { getSystemState } from '../hooks/useApi';

const Section = ({ title, icon, children }) => (
  <div className="panel" style={{ padding: 20 }}>
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
      <span>{icon}</span> {title}
    </div>
    {children}
  </div>
);

const EmptyState = ({ msg }) => (
  <div style={{ color: 'var(--green)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>✓ {msg}</div>
);

export default function SystemState() {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = async () => {
    try { const s = await getSystemState(); setState(s); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); const t = setInterval(fetch, 5000); return () => clearInterval(t); }, []);

  if (loading) return <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>Loading system state...</div>;

  const firewall = state?.firewall?.deny_rules || [];
  const blocklist = state?.blocklist?.blocked_hashes || [];
  const users = Object.entries(state?.directory?.users || {});
  const hosts = state?.isolation?.isolated_hosts || [];
  const alerts = state?.alerts?.alerts || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: 18, color: 'var(--cyan)', letterSpacing: '0.1em', textShadow: 'var(--glow-cyan)' }}>
          SYSTEM ENFORCEMENT STATE
        </h2>
        <button className="btn btn-primary" onClick={fetch} style={{ fontSize: 12 }}>↺ REFRESH</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Firewall */}
        <Section title={`FIREWALL DENY RULES (${firewall.length})`} icon="🔥">
          {firewall.length === 0 ? <EmptyState msg="No IPs blocked" /> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
              <thead><tr>{['IP', 'REASON', 'BLOCKED AT'].map(h => <th key={h} style={{ textAlign: 'left', color: 'var(--text-dim)', padding: '4px 8px 8px 0', fontSize: 10 }}>{h}</th>)}</tr></thead>
              <tbody>
                {firewall.map((r, i) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--red)' }}>{r.ip}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.reason}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-dim)' }}>{r.blocked_at?.slice(0, 19).replace('T', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        {/* Hash blocklist */}
        <Section title={`HASH BLOCKLIST (${blocklist.length})`} icon="🚫">
          {blocklist.length === 0 ? <EmptyState msg="No hashes blocked" /> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
              <thead><tr>{['HASH', 'THREAT', 'BLOCKED AT'].map(h => <th key={h} style={{ textAlign: 'left', color: 'var(--text-dim)', padding: '4px 8px 8px 0', fontSize: 10 }}>{h}</th>)}</tr></thead>
              <tbody>
                {blocklist.map((r, i) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--orange)', fontFamily: 'var(--font-mono)' }}>{r.hash?.slice(0, 16)}...</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-secondary)' }}>{r.threat_name?.slice(0, 30)}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-dim)' }}>{r.blocked_at?.slice(0, 19).replace('T', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        {/* Disabled users */}
        <Section title={`DISABLED ACCOUNTS (${users.length})`} icon="🔒">
          {users.length === 0 ? <EmptyState msg="No accounts disabled" /> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
              <thead><tr>{['USER', 'PROVIDER', 'REASON', 'DISABLED AT'].map(h => <th key={h} style={{ textAlign: 'left', color: 'var(--text-dim)', padding: '4px 8px 8px 0', fontSize: 10 }}>{h}</th>)}</tr></thead>
              <tbody>
                {users.map(([username, data], i) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--red)' }}>{username}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--cyan-dim)' }}>{data.provider || 'local'}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-secondary)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data.reason}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-dim)' }}>{data.disabled_at?.slice(0, 19).replace('T', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        {/* Isolated hosts */}
        <Section title={`ISOLATED HOSTS (${hosts.length})`} icon="🏥">
          {hosts.length === 0 ? <EmptyState msg="No hosts in quarantine" /> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
              <thead><tr>{['HOST', 'VLAN', 'REASON', 'ISOLATED AT'].map(h => <th key={h} style={{ textAlign: 'left', color: 'var(--text-dim)', padding: '4px 8px 8px 0', fontSize: 10 }}>{h}</th>)}</tr></thead>
              <tbody>
                {hosts.map((h, i) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--orange)' }}>{h.hostname}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--purple)' }}>{h.vlan}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-secondary)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.reason}</td>
                    <td style={{ padding: '8px 8px 8px 0', color: 'var(--text-dim)' }}>{h.isolated_at?.slice(0, 19).replace('T', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>
      </div>

      {/* Alerts */}
      <Section title={`ALERTS (${alerts.length})`} icon="📢">
        {alerts.length === 0 ? <EmptyState msg="No alerts" /> : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[...alerts].reverse().slice(0, 20).map((a, i) => (
              <div key={i} style={{ display: 'flex', gap: 16, padding: 12, background: 'var(--bg-deep)', borderRadius: 4, border: '1px solid var(--border)', alignItems: 'flex-start' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, padding: '2px 8px', borderRadius: 2, flexShrink: 0,
                  background: a.severity === 'HIGH' ? 'rgba(255,51,85,0.15)' : 'rgba(255,140,0,0.15)',
                  color: a.severity === 'HIGH' ? 'var(--red)' : 'var(--orange)',
                  border: `1px solid ${a.severity === 'HIGH' ? 'rgba(255,51,85,0.3)' : 'rgba(255,140,0,0.3)'}`,
                }}>{a.severity}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-primary)' }}>{a.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>{a.created_at?.slice(0, 19).replace('T', ' ')}</div>
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>{a.id}</span>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
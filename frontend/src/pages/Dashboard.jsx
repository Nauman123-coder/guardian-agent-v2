import React from 'react';
import { useStats, useIncidents } from '../hooks/useApi';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import IncidentRow from '../components/IncidentRow';

const StatCard = ({ label, value, sub, color = 'var(--cyan)', glow }) => (
  <div className="panel" style={{ padding: '20px 24px', flex: 1, minWidth: 160 }}>
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.1em', marginBottom: 8 }}>
      {label}
    </div>
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 36, color, textShadow: glow, fontWeight: 'bold', lineHeight: 1 }}>
      {value ?? '—'}
    </div>
    {sub && <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6 }}>{sub}</div>}
  </div>
);

const riskColor = (score) => {
  if (score >= 9) return 'var(--red)';
  if (score >= 7) return 'var(--orange)';
  if (score >= 4) return 'var(--yellow)';
  return 'var(--green)';
};

const statusLabel = {
  pending: 'PENDING',
  analyzing: 'ANALYZING',
  awaiting_approval: 'AWAITING APPROVAL',
  executing: 'EXECUTING',
  complete: 'COMPLETE',
  error: 'ERROR',
};

export default function Dashboard({ onSelectIncident }) {
  const { stats } = useStats();
  const { incidents } = useIncidents();

  const pending = incidents.filter(i => i.status === 'awaiting_approval');
  const byStatus = stats?.by_status || {};

  const statusData = Object.entries(byStatus).map(([k, v]) => ({ name: statusLabel[k] || k, count: v }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
        <h1 style={{ fontFamily: 'var(--font-mono)', fontSize: 22, color: 'var(--cyan)', letterSpacing: '0.1em', textShadow: 'var(--glow-cyan)' }}>
          THREAT OPERATIONS CENTER
        </h1>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
          {new Date().toUTCString().toUpperCase()}
        </span>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <StatCard label="TOTAL INCIDENTS" value={stats?.total ?? 0} color="var(--cyan)" glow="var(--glow-cyan)" />
        <StatCard label="AWAITING APPROVAL" value={stats?.pending_approval ?? 0} color={stats?.pending_approval > 0 ? 'var(--orange)' : 'var(--text-secondary)'} sub={stats?.pending_approval > 0 ? '⚠ Action required' : 'None pending'} />
        <StatCard label="HIGH RISK (≥7)" value={stats?.high_risk ?? 0} color={stats?.high_risk > 0 ? 'var(--red)' : 'var(--green)'} glow={stats?.high_risk > 0 ? 'var(--glow-red)' : undefined} />
        <StatCard label="AVG RISK SCORE" value={stats?.avg_risk_score ?? '—'} sub="out of 10.0" color={stats?.avg_risk_score >= 7 ? 'var(--red)' : stats?.avg_risk_score >= 4 ? 'var(--yellow)' : 'var(--green)'} />
      </div>

      {/* Pending approvals banner */}
      {pending.length > 0 && (
        <div style={{
          background: 'rgba(255,140,0,0.08)',
          border: '1px solid rgba(255,140,0,0.4)',
          borderRadius: 6,
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          position: 'relative',
          zIndex: 10,
        }}>
          <span style={{ fontSize: 20, pointerEvents: 'none' }}>⚠️</span>
          <div style={{ pointerEvents: 'none' }}>
            <div style={{ color: 'var(--orange)', fontWeight: 700, fontSize: 14, fontFamily: 'var(--font-mono)' }}>
              {pending.length} INCIDENT{pending.length > 1 ? 'S' : ''} AWAITING YOUR APPROVAL
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 2 }}>
              High-risk mitigation actions require manual authorization before execution
            </div>
          </div>
          <div
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const inc = pending[0];
              const incId = inc?.id || inc?.incident_id;
              if (incId) onSelectIncident(incId);
            }}
            style={{
              marginLeft: 'auto',
              background: 'rgba(0,255,136,0.15)',
              color: '#00ff88',
              border: '1px solid rgba(0,255,136,0.4)',
              borderRadius: 4,
              padding: '10px 20px',
              cursor: 'pointer',
              fontFamily: 'var(--font-ui)',
              fontSize: 13,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            Review Now →
          </div>
        </div>
      )}

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
        {/* Incidents list */}
        <div className="panel">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)', letterSpacing: '0.08em' }}>
              RECENT INCIDENTS
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
              {incidents.length} total
            </span>
          </div>
          <div>
            {incidents.length === 0 && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                No incidents yet. Submit a log to get started.
              </div>
            )}
            {incidents.map(inc => (
              <IncidentRow key={inc.id} incident={inc} onClick={() => onSelectIncident(inc.id)} />
            ))}
          </div>
        </div>

        {/* Right sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Status breakdown */}
          <div className="panel" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 16 }}>
              STATUS BREAKDOWN
            </div>
            {statusData.length === 0 ? (
              <div style={{ color: 'var(--text-dim)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>No data</div>
            ) : (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={statusData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fill: 'var(--text-dim)', fontSize: 9, fontFamily: 'var(--font-mono)' }} />
                  <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: 12 }} />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {statusData.map((entry, i) => (
                      <Cell key={i} fill={entry.name.includes('APPROVAL') ? 'var(--orange)' : entry.name === 'COMPLETE' ? 'var(--green-dim)' : 'var(--cyan-dim)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Recent high-risk */}
          <div className="panel" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
              HIGH RISK INCIDENTS
            </div>
            {incidents.filter(i => i.risk_score >= 7).slice(0, 5).map(inc => (
              <div key={inc.id} onClick={() => onSelectIncident(inc.id)}
                style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
              >
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 20, color: riskColor(inc.risk_score), minWidth: 32, textAlign: 'center' }}>
                  {inc.risk_score}
                </span>
                <div>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {inc.id.slice(0, 8).toUpperCase()}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                    {inc.found_indicators?.slice(0, 2).join(', ')}
                  </div>
                </div>
              </div>
            ))}
            {incidents.filter(i => i.risk_score >= 7).length === 0 && (
              <div style={{ color: 'var(--green)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>✓ No high-risk incidents</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
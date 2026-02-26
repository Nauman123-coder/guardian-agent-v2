import React from 'react';

const riskColor = (s) => s >= 9 ? 'var(--red)' : s >= 7 ? 'var(--orange)' : s >= 4 ? 'var(--yellow)' : s > 0 ? 'var(--green)' : 'var(--text-dim)';

const statusLabel = {
  pending: '⬤', analyzing: '⟳', awaiting_approval: '⚠',
  executing: '▶', complete: '✓', error: '✕',
};
const statusColor = {
  pending: 'var(--text-dim)', analyzing: 'var(--cyan)', awaiting_approval: 'var(--orange)',
  executing: 'var(--purple)', complete: 'var(--green)', error: 'var(--red)',
};

export default function IncidentRow({ incident, onClick }) {
  const id = incident.id || incident.incident_id || '';
  const isAwaiting = incident.status === 'awaiting_approval';

  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: '40px 1fr 180px 90px 120px',
        gap: 16,
        alignItems: 'center',
        padding: '12px 20px',
        borderBottom: '1px solid var(--border)',
        cursor: 'pointer',
        userSelect: 'none',
        background: isAwaiting ? 'rgba(255,140,0,0.04)' : 'transparent',
      }}
      onMouseEnter={e => e.currentTarget.style.background = isAwaiting ? 'rgba(255,140,0,0.10)' : 'var(--bg-hover)'}
      onMouseLeave={e => e.currentTarget.style.background = isAwaiting ? 'rgba(255,140,0,0.04)' : 'transparent'}
    >
      {/* Risk score */}
      <div style={{ pointerEvents: 'none', fontFamily: 'var(--font-mono)', fontWeight: 900, fontSize: 18, color: riskColor(incident.risk_score), textAlign: 'center' }}>
        {incident.risk_score || '—'}
      </div>

      {/* ID + indicators */}
      <div style={{ pointerEvents: 'none', overflow: 'hidden' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-primary)', marginBottom: 3 }}>
          {id.slice(0, 8).toUpperCase()}
          <span style={{ color: 'var(--text-dim)', fontSize: 10, marginLeft: 8 }}>{incident.log_source}</span>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {incident.found_indicators?.slice(0, 3).join(' · ') || 'No indicators yet'}
        </div>
      </div>

      {/* Timestamp */}
      <div style={{ pointerEvents: 'none', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
        {incident.created_at?.slice(0, 19).replace('T', ' ')}
      </div>

      {/* Actions count */}
      <div style={{ pointerEvents: 'none', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', textAlign: 'right' }}>
        {incident.executed_actions?.length > 0 ? `${incident.executed_actions.length} actions` : ''}
      </div>

      {/* Status */}
      <div style={{ pointerEvents: 'none', textAlign: 'right' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: statusColor[incident.status] || 'var(--text-dim)' }}>
          {statusLabel[incident.status] || '?'} {incident.status?.replace(/_/g, ' ').toUpperCase()}
        </span>
      </div>
    </div>
  );
}
import React, { useState, useEffect } from 'react';
import { useIncident, useWebSocket, approveIncident, denyIncident } from '../hooks/useApi';

const riskColor = (s) => s >= 9 ? 'var(--red)' : s >= 7 ? 'var(--orange)' : s >= 4 ? 'var(--yellow)' : 'var(--green)';
const riskGlow = (s) => s >= 9 ? 'var(--glow-red)' : s >= 7 ? '0 0 20px rgba(255,140,0,0.4)' : s >= 4 ? '0 0 20px rgba(255,215,0,0.3)' : 'var(--glow-green)';

const StatusBadge = ({ status }) => {
  const cls = {
    analyzing: 'badge-analyzing', awaiting_approval: 'badge-awaiting',
    complete: 'badge-complete', error: 'badge-error', executing: 'badge-executing',
  }[status] || 'badge-analyzing';
  const labels = {
    pending: '⬤ PENDING', analyzing: '⟳ ANALYZING', awaiting_approval: '⚠ AWAITING APPROVAL',
    executing: '▶ EXECUTING', complete: '✓ COMPLETE', error: '✕ ERROR',
  };
  return <span className={`badge ${cls}`}>{labels[status] || status?.toUpperCase()}</span>;
};

const NodeStep = ({ name, active, done }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
    <div style={{
      width: 28, height: 28, borderRadius: 4,
      background: done ? 'rgba(0,255,136,0.15)' : active ? 'rgba(0,212,255,0.15)' : 'var(--bg-card)',
      border: `1px solid ${done ? 'var(--green-dim)' : active ? 'var(--cyan-dim)' : 'var(--border)'}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 14, flexShrink: 0,
      boxShadow: active ? 'var(--glow-cyan)' : done ? 'var(--glow-green)' : 'none',
      transition: 'all 0.3s',
    }}>
      {done ? '✓' : active ? '◈' : '○'}
    </div>
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: 12,
      color: done ? 'var(--green)' : active ? 'var(--cyan)' : 'var(--text-dim)',
      transition: 'color 0.3s',
    }}>
      {name}
    </span>
  </div>
);

const NODES = ['analyzer', 'investigator', 'mitigator', 'human_approval', 'executor', 'report'];

export default function IncidentDetail({ id, onBack }) {
  const { incident, refresh } = useIncident(id);
  const { events } = useWebSocket(id);
  const [approving, setApproving] = useState(false);
  const [actionDone, setActionDone] = useState(false);

  // Refresh when WS events arrive
  useEffect(() => { if (events.length > 0) refresh(); }, [events.length]);

  const handleApprove = async () => {
    setApproving(true);
    try { await approveIncident(id); setActionDone(true); refresh(); }
    catch (e) { alert('Error: ' + e.message); }
    finally { setApproving(false); }
  };

  const handleDeny = async () => {
    setApproving(true);
    try { await denyIncident(id); setActionDone(true); refresh(); }
    catch (e) { alert('Error: ' + e.message); }
    finally { setApproving(false); }
  };

  if (!incident) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
      Loading incident...
    </div>
  );

  const currentNodeIdx = NODES.indexOf(incident.current_node);
  const isAwaiting = incident.status === 'awaiting_approval';

  // Parse actions from mitigation_plan
  let actions = [];
  try {
    if (incident.mitigation_plan?.includes('__ACTIONS__')) {
      actions = JSON.parse(incident.mitigation_plan.split('__ACTIONS__\n')[1]);
    }
  } catch {}

  const displayPlan = incident.mitigation_plan?.split('__ACTIONS__\n')[0] || incident.mitigation_plan || '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <button className="btn btn-primary" onClick={onBack} style={{ padding: '6px 14px', fontSize: 12 }}>
          ← BACK
        </button>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', letterSpacing: '0.1em' }}>INCIDENT</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, color: 'var(--cyan)', letterSpacing: '0.08em' }}>
            {id.slice(0, 8).toUpperCase()}
            <span style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 8 }}>{id}</span>
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 12, alignItems: 'center' }}>
          <a
            href={`http://localhost:8000/api/incidents/${id}/report.pdf`}
            target="_blank"
            rel="noreferrer"
            style={{
              background: 'rgba(139,92,246,0.15)',
              color: 'var(--purple)',
              border: '1px solid rgba(139,92,246,0.4)',
              borderRadius: 4, padding: '7px 16px',
              textDecoration: 'none',
              fontFamily: 'var(--font-ui)', fontSize: 12, fontWeight: 600,
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}
          >
            ⬇ Export PDF
          </a>
          <StatusBadge status={incident.status} />
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 900,
            color: riskColor(incident.risk_score),
            textShadow: riskGlow(incident.risk_score),
          }}>
            {incident.risk_score}/10
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 20 }}>
        {/* Left: Pipeline progress */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="panel" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
              PIPELINE STATUS
            </div>
            {NODES.map((node, i) => (
              <NodeStep key={node}
                name={node.replace('_', ' ').toUpperCase()}
                active={i === currentNodeIdx}
                done={i < currentNodeIdx || incident.status === 'complete'}
              />
            ))}
          </div>

          {/* Indicators */}
          <div className="panel" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
              INDICATORS ({incident.found_indicators?.length || 0})
            </div>
            {(incident.found_indicators || []).map((ind, i) => {
              const tiResult = (incident.investigation_results || []).find(r => r.indicator === ind);
              const isMalicious = tiResult?.is_malicious;
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 10, color: isMalicious === true ? 'var(--red)' : isMalicious === false ? 'var(--green)' : 'var(--text-dim)' }}>
                    {isMalicious === true ? '🔴' : isMalicious === false ? '🟢' : '⚪'}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)', wordBreak: 'break-all' }}>{ind}</span>
                </div>
              );
            })}
            {!incident.found_indicators?.length && (
              <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>None found</div>
            )}
          </div>
        </div>

        {/* Right: Main content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* HITL Approval UI */}
          {isAwaiting && !actionDone && (
            <div className={`panel card-active`} style={{
              padding: 24,
              background: 'rgba(255,140,0,0.05)',
              border: '1px solid rgba(255,140,0,0.4)',
            }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--orange)', marginBottom: 16, letterSpacing: '0.06em' }}>
                ⚠ HUMAN AUTHORIZATION REQUIRED
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 20, lineHeight: 1.6 }}>
                Risk score <strong style={{ color: 'var(--red)' }}>{incident.risk_score}/10</strong> exceeds the auto-execute threshold.
                Review the proposed actions below and authorize or deny.
              </p>

              {/* Proposed actions table */}
              <div style={{ background: 'var(--bg-deep)', borderRadius: 4, overflow: 'hidden', marginBottom: 20 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-card)' }}>
                      {['#', 'ACTION', 'TARGET', 'URGENCY', 'REASON'].map(h => (
                        <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-dim)', fontWeight: 600, letterSpacing: '0.06em', fontSize: 10 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {actions.map((a, i) => (
                      <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                        <td style={{ padding: '10px 12px', color: 'var(--text-dim)' }}>{i + 1}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--cyan)' }}>{a.action_type}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-primary)' }}>{a.target}</td>
                        <td style={{ padding: '10px 12px', color: a.urgency === 'IMMEDIATE' ? 'var(--red)' : 'var(--orange)' }}>{a.urgency}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.justification}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ display: 'flex', gap: 12 }}>
                <button className="btn btn-approve" onClick={handleApprove} disabled={approving} style={{ fontSize: 14, padding: '10px 24px' }}>
                  ✓ APPROVE & EXECUTE
                </button>
                <button className="btn btn-deny" onClick={handleDeny} disabled={approving} style={{ fontSize: 14, padding: '10px 24px' }}>
                  ✕ DENY — ALERT ONLY
                </button>
              </div>
            </div>
          )}

          {/* Mitigation plan */}
          <div className="panel" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
              MITIGATION PLAN
            </div>
            <p style={{ color: 'var(--text-primary)', fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {displayPlan || <span style={{ color: 'var(--text-dim)' }}>Generating...</span>}
            </p>
          </div>

          {/* Executed actions */}
          {incident.executed_actions?.length > 0 && (
            <div className="panel" style={{ padding: 20 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
                EXECUTED ACTIONS ({incident.executed_actions.length})
              </div>
              {incident.executed_actions.map((a, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--border)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                  <span style={{ color: a.includes('success') || a.includes('already') ? 'var(--green)' : 'var(--red)' }}>✓</span>
                  <span style={{ color: 'var(--text-primary)' }}>{a}</span>
                </div>
              ))}
            </div>
          )}

          {/* Raw log */}
          <div className="panel" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
              RAW LOG — SOURCE: {incident.log_source?.toUpperCase()}
            </div>
            <pre style={{
              fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)',
              background: 'var(--bg-deep)', padding: 16, borderRadius: 4,
              overflow: 'auto', maxHeight: 300, lineHeight: 1.6,
              border: '1px solid var(--border)',
            }}>
              {incident.raw_log}
            </pre>
          </div>

          {/* Live event stream */}
          {events.length > 0 && (
            <div className="panel" style={{ padding: 20 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
                LIVE EVENT STREAM
              </div>
              <div style={{ maxHeight: 200, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
                {[...events].reverse().map((e, i) => (
                  <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', display: 'flex', gap: 12 }}>
                    <span style={{ color: 'var(--cyan-dim)', flexShrink: 0 }}>{e.timestamp?.slice(11, 19)}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{e.type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
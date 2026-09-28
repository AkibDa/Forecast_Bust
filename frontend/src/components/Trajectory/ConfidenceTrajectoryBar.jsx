import React from 'react';
import { TrendingUp, AlertCircle, Info } from 'lucide-react';

export const ConfidenceTrajectoryBar = ({
  selectedGrid,
  timeseriesData,
  loading,
  error,
  currentLeadDay,
  onSelectLeadDay,
}) => {
  const leadTimes = timeseriesData?.lead_times || [];
  const isSingleDay = leadTimes.length === 1;

  return (
    <section className="dashboard-trajectory">
      <div className="trajectory-card">
        {/* Trajectory Header */}
        <div className="trajectory-header">
          <div className="trajectory-title">
            <TrendingUp size={13} style={{ color: 'var(--accent-cyan)' }} />
            <span>CONFIDENCE TRAJECTORY (10-DAY HORIZON)</span>
            {selectedGrid && (
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10px',
                  color: 'var(--accent-cyan)',
                  border: '1px solid var(--border-main)',
                  padding: '1px 6px',
                  borderRadius: '2px',
                }}
              >
                GRID {selectedGrid}
              </span>
            )}
          </div>

          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--text-muted)',
            }}
          >
            {selectedGrid ? `${leadTimes.length} HORIZONS LOADED` : 'NO CELL SELECTED'}
          </span>
        </div>

        {/* Content Area */}
        {!selectedGrid ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              height: '56px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
            }}
          >
            <Info size={13} style={{ color: 'var(--accent-cyan)' }} />
            <span>Select any forecast cell on the map to evaluate its 10-day lead-time trajectory.</span>
          </div>
        ) : loading ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '56px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
            }}
          >
            Loading trajectory vectors...
          </div>
        ) : error ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              height: '56px',
              color: 'var(--risk-red)',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
            }}
          >
            <AlertCircle size={13} />
            <span>{error}</span>
          </div>
        ) : isSingleDay ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: '56px',
              padding: '0 12px',
              background: 'var(--bg-app)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '2px',
            }}
          >
            <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  HORIZON
                </span>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                  D+{leadTimes[0].lead_day} (+24h)
                </div>
              </div>

              <div>
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  CONFIDENCE
                </span>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--status-green)', fontFamily: 'var(--font-mono)' }}>
                  {(leadTimes[0].confidence_score * 100).toFixed(1)}%
                </div>
              </div>

              <div>
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  BUST RISK
                </span>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--risk-red)', fontFamily: 'var(--font-mono)' }}>
                  {(leadTimes[0].bust_probability * 100).toFixed(2)}%
                </div>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '10px',
                color: 'var(--warning-amber)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <AlertCircle size={12} />
              <span>Operational live GFS cycle stores Day 1 (f024). Switch to an archive date for D1–D10 trajectory.</span>
            </div>
          </div>
        ) : (
          /* Scientific Timeline Axis for D1 - D10 */
          <div className="trajectory-axis-container">
            {leadTimes.map((lt) => {
              const confPct = lt.confidence_score * 100;
              const bustPct = lt.bust_probability * 100;
              const isCurrent = lt.lead_day === currentLeadDay;

              return (
                <div
                  key={`timeline-node-${lt.lead_day}`}
                  onClick={() => onSelectLeadDay && onSelectLeadDay(lt.lead_day)}
                  className={`trajectory-node ${isCurrent ? 'active' : ''}`}
                  title={`Horizon D+${lt.lead_day} (+${lt.lead_day * 24}h): ${confPct.toFixed(1)}% Confidence, ${bustPct.toFixed(2)}% Bust Risk`}
                >
                  <span className="node-day">D+{lt.lead_day}</span>
                  <div className="node-tick" />
                  <span
                    className="node-val"
                    style={{
                      color: confPct < 80 ? 'var(--warning-amber)' : 'var(--status-green)',
                    }}
                  >
                    {confPct.toFixed(0)}%
                  </span>
                  <span className="node-risk">
                    {bustPct.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};

export default ConfidenceTrajectoryBar;

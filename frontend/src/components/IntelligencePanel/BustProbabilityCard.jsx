import React from 'react';

export const BustProbabilityCard = ({
  confidenceScore = 0.985,
  bustProbability = 0.015,
  stats,
}) => {
  const confPct = (confidenceScore * 100).toFixed(1);
  const bustPct = (bustProbability * 100).toFixed(2);

  let riskLabel = 'NOMINAL RISK';
  let riskColor = 'var(--status-green)';

  if (stats && stats.p75) {
    if (bustProbability >= stats.p90) {
      riskLabel = 'HIGH BUST RISK';
      riskColor = 'var(--risk-red)';
    } else if (bustProbability >= stats.p75) {
      riskLabel = 'ELEVATED RISK';
      riskColor = 'var(--warning-amber)';
    } else {
      riskLabel = 'LOW BUST RISK';
      riskColor = 'var(--status-green)';
    }
  }

  return (
    <div className="station-card">
      <div className="station-card-header">
        <span className="card-heading">
          <span>RELIABILITY INDEX</span>
        </span>
        <span
          className="card-heading-tag"
          style={{ color: riskColor, borderColor: riskColor }}
        >
          {riskLabel}
        </span>
      </div>

      <div className="metric-grid">
        <div className="metric-cell">
          <div className="metric-cell-label">CALIBRATED CONFIDENCE</div>
          <div className="metric-cell-val" style={{ color: 'var(--status-green)' }}>
            {confPct}%
          </div>
        </div>

        <div className="metric-cell">
          <div className="metric-cell-label">BUST TAIL PROBABILITY</div>
          <div
            className="metric-cell-val"
            style={{
              color: bustProbability >= (stats?.p75 ?? 0.015) ? 'var(--risk-red)' : 'var(--text-primary)',
            }}
          >
            {bustPct}%
          </div>
        </div>
      </div>

      {/* Segmented confidence bar */}
      <div style={{ marginTop: '4px' }}>
        <div
          style={{
            height: '4px',
            borderRadius: '1px',
            background: 'var(--bg-app)',
            border: '1px solid var(--border-subtle)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, Math.max(5, parseFloat(confPct)))}%`,
              backgroundColor: 'var(--accent-cyan)',
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default BustProbabilityCard;

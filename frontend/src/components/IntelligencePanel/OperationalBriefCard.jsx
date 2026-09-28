import React, { useMemo } from 'react';

export const OperationalBriefCard = ({
  leadDay,
  bustProbability = 0.015,
  drivers = [],
  analogs = [],
  dataSource = 'historical',
}) => {
  const brief = useMemo(() => {
    let riskLevel = 'LOW';
    let advisory = 'Numerical models show tight synoptic consensus. Atmospheric bust probability is low.';
    let riskColor = 'var(--status-green)';

    if (bustProbability > 0.04) {
      riskLevel = 'ELEVATED';
      advisory = 'Elevated bust tail probability. Numerical guidance diverges substantially from historical analogues.';
      riskColor = 'var(--risk-red)';
    } else if (bustProbability > 0.018) {
      riskLevel = 'MODERATE';
      advisory = 'Moderate bust tendency detected. Increased variance in convective and boundary layer parameters.';
      riskColor = 'var(--warning-amber)';
    }

    let driverText = 'No dominant atmospheric driver flagged.';
    if (drivers.length > 0) {
      const top = drivers[0];
      const effect = top.direction === 'lowers_confidence' ? 'destabilizing reliability' : 'stabilizing forecast';
      driverText = `Primary driver: ${top.feature.toUpperCase()} (${top.contribution > 0 ? '+' : ''}${top.contribution.toFixed(3)} SHAP), ${effect}.`;
    }

    let analogText = 'Analogs pending.';
    if (analogs.length > 0) {
      const topAna = analogs[0];
      const sim = (topAna.similarity_score * 100).toFixed(0);
      analogText = `Closest analog: ${topAna.case_date} (${sim}% similarity).`;
    }

    return {
      riskLevel,
      advisory,
      driverText,
      analogText,
      riskColor,
    };
  }, [bustProbability, drivers, analogs]);

  const { riskLevel, advisory, driverText, analogText, riskColor } = brief;

  return (
    <div className="station-card">
      <div className="station-card-header">
        <span className="card-heading">
          <span>SYNOPTIC OPERATIONAL BRIEF</span>
        </span>
        <span className="card-heading-tag">DERIVED</span>
      </div>

      <div className="brief-box" style={{ marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
          <strong style={{ color: riskColor, letterSpacing: '0.4px' }}>
            STATUS: {riskLevel} BUST RISK (+{leadDay * 24}h)
          </strong>
          <span style={{ fontSize: '9px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
            {dataSource}
          </span>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '10px', lineHeight: 1.4, margin: 0 }}>
          {advisory}
        </p>
      </div>

      <div className="brief-box" style={{ fontSize: '9px', color: 'var(--text-muted)' }}>
        <div>• <span style={{ color: 'var(--text-primary)' }}>Driver:</span> {driverText}</div>
        <div style={{ marginTop: '2px' }}>• <span style={{ color: 'var(--text-primary)' }}>Analog:</span> {analogText}</div>
      </div>
    </div>
  );
};

export default OperationalBriefCard;

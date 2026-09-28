import React from 'react';

export const AnalogCasesCard = ({ analogs = [], loading = false, error = null }) => {
  if (loading) {
    return (
      <div className="station-card">
        <div className="station-card-header">
          <span className="card-heading">
            <span>HISTORICAL ANALOGS</span>
          </span>
          <span className="card-heading-tag">ERA5 PCA</span>
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '10px', fontFamily: 'var(--font-mono)', padding: '6px 0' }}>
          Searching 32-dim ERA5 PCA embedding space...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="station-card">
        <div className="station-card-header">
          <span className="card-heading">
            <span>HISTORICAL ANALOGS</span>
          </span>
          <span className="card-heading-tag">ERA5 PCA</span>
        </div>
        <div style={{ color: 'var(--risk-red)', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
          {error}
        </div>
      </div>
    );
  }

  const formatLocation = (loc) => {
    if (!loc) return '--';
    const parts = loc.split('_');
    if (parts.length === 2) {
      const lat = parseFloat(parts[0]);
      const lon = parseFloat(parts[1]);
      if (!isNaN(lat) && !isNaN(lon)) {
        return `${lat.toFixed(1)}°N / ${lon.toFixed(1)}°E`;
      }
    }
    return loc;
  };

  return (
    <div className="station-card">
      <div className="station-card-header">
        <span className="card-heading">
          <span>HISTORICAL ANALOGS</span>
        </span>
        <span className="card-heading-tag">ERA5 PCA</span>
      </div>

      {analogs.length === 0 ? (
        <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontStyle: 'italic', fontFamily: 'var(--font-mono)', textAlign: 'center', padding: '6px 0' }}>
          No analogs retrieved.
        </div>
      ) : (
        analogs.map((ana, i) => {
          const simPct = (ana.similarity_score * 100).toFixed(0);

          return (
            <div key={`analog-${ana.case_date}-${i}`} className="analog-entry">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderBottom: '1px solid var(--border-subtle)',
                  paddingBottom: '3px',
                  marginBottom: '5px',
                }}
              >
                <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '11px' }}>
                  {ana.case_date}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    color: 'var(--accent-cyan)',
                  }}
                >
                  {simPct}% SIMILAR
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '9px', color: 'var(--text-muted)' }}>
                <div>
                  <span>MAX PRECIP: </span>
                  <strong style={{ color: 'var(--text-primary)' }}>
                    {ana.domain_max_precip !== null && typeof ana.domain_max_precip === 'number'
                      ? `${ana.domain_max_precip.toFixed(1)} mm`
                      : '--'}
                  </strong>
                </div>

                <div>
                  <span>MEAN PRECIP: </span>
                  <strong style={{ color: 'var(--text-primary)' }}>
                    {ana.domain_mean_precip !== null && typeof ana.domain_mean_precip === 'number'
                      ? `${ana.domain_mean_precip.toFixed(1)} mm`
                      : '--'}
                  </strong>
                </div>
              </div>

              <div
                style={{
                  fontSize: '9px',
                  color: 'var(--text-muted)',
                  marginTop: '3px',
                  paddingTop: '3px',
                  borderTop: '1px solid rgba(255, 255, 255, 0.04)',
                }}
              >
                <span>CORE: </span>
                <strong style={{ color: 'var(--text-primary)' }}>
                  {formatLocation(ana.max_precip_location)}
                </strong>
                {ana.forecast_error_outcome && (
                  <span style={{ marginLeft: '8px', color: 'var(--text-dim)' }}>
                    ({ana.forecast_error_outcome})
                  </span>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};

export default AnalogCasesCard;

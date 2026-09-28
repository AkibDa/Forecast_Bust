import React from 'react';

const FEATURE_METADATA = {
  mslp: { label: 'MSLP', name: 'Pressure' },
  u10: { label: 'U10', name: 'Zonal Wind' },
  v10: { label: 'V10', name: 'Meridional Wind' },
  t2m: { label: 'T2M', name: 'Temperature' },
  precip: { label: 'PRECIP', name: 'Precipitation' },
};

export const DriversCard = ({ drivers = [], loading = false, error = null }) => {
  if (loading) {
    return (
      <div className="station-card">
        <div className="station-card-header">
          <span className="card-heading">
            <span>ATMOSPHERIC DRIVERS</span>
          </span>
          <span className="card-heading-tag">SHAP</span>
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '10px', fontFamily: 'var(--font-mono)', padding: '6px 0' }}>
          Computing TreeExplainer vectors...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="station-card">
        <div className="station-card-header">
          <span className="card-heading">
            <span>ATMOSPHERIC DRIVERS</span>
          </span>
          <span className="card-heading-tag">SHAP</span>
        </div>
        <div style={{ color: 'var(--risk-red)', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="station-card">
      <div className="station-card-header">
        <span className="card-heading">
          <span>ATMOSPHERIC DRIVERS</span>
        </span>
        <span className="card-heading-tag">SHAP TREEEXPLAINER</span>
      </div>

      {drivers.length === 0 ? (
        <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontStyle: 'italic', fontFamily: 'var(--font-mono)', textAlign: 'center', padding: '6px 0' }}>
          No drivers returned.
        </div>
      ) : (
        drivers.map((drv, i) => {
          const meta = FEATURE_METADATA[drv.feature] || {
            label: drv.feature.toUpperCase(),
            name: drv.feature,
          };
          const isLowers = drv.direction === 'lowers_confidence';

          return (
            <div key={`driver-${drv.feature}-${i}`} className={`driver-entry ${drv.direction}`}>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '10px' }}>
                  {meta.label}{' '}
                  <span style={{ fontWeight: 400, color: 'var(--text-dim)', fontSize: '9px' }}>
                    ({meta.name})
                  </span>
                </div>
                <div
                  style={{
                    fontSize: '9px',
                    fontWeight: 600,
                    letterSpacing: '0.4px',
                    color: isLowers ? 'var(--risk-red)' : 'var(--status-green)',
                  }}
                >
                  {isLowers ? 'LOWERS CONFIDENCE' : 'RAISES CONFIDENCE'}
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    fontWeight: 700,
                    color: isLowers ? 'var(--risk-red)' : 'var(--status-green)',
                  }}
                >
                  {drv.contribution > 0 ? `+${drv.contribution.toFixed(3)}` : drv.contribution.toFixed(3)}
                </span>
                <span style={{ fontSize: '8px', color: 'var(--text-dim)', marginLeft: '4px' }}>SHAP</span>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};

export default DriversCard;

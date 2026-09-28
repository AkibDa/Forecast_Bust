import React from 'react';
import { X } from 'lucide-react';

export const GridHeaderCard = ({ gridId, leadDay, dataSource = 'historical', onDeselect }) => {
  const parts = gridId ? gridId.split('_') : ['--', '--'];
  const lat = parseFloat(parts[0]);
  const lon = parseFloat(parts[1]);

  return (
    <div className="station-card">
      <div className="station-card-header">
        <span className="card-heading">
          <span>SELECTED GRID CELL</span>
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className="card-heading-tag" style={{ color: 'var(--accent-cyan)' }}>
            D+{leadDay} ({leadDay * 24}h)
          </span>
          <span className="card-heading-tag" style={{ textTransform: 'uppercase' }}>
            {dataSource}
          </span>
          {onDeselect && (
            <button
              onClick={onDeselect}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '2px',
              }}
              title="Deselect cell"
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {!isNaN(lat) ? `${lat.toFixed(2)}°N` : '--'} / {!isNaN(lon) ? `${lon.toFixed(2)}°E` : '--'}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>
          ID: {gridId}
        </div>
      </div>
    </div>
  );
};

export default GridHeaderCard;

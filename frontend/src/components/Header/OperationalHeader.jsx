import React from 'react';
import { RefreshCw, Download, Activity } from 'lucide-react';

export const OperationalHeader = ({
  health,
  healthLoading,
  healthError,
  isIngesting,
  onIngest,
  onRefresh,
  isRefreshing,
}) => {
  // Determine operational telemetry status
  let statusState = 'checking';
  let statusTitle = 'CHECKING';
  let statusSubtitle = 'TELEMETRY';

  if (!health && healthLoading) {
    statusState = 'checking';
    statusTitle = 'CHECKING';
    statusSubtitle = 'TELEMETRY';
  } else if (health && health.status === 'ok') {
    statusState = 'online';
    if (health.ingestion_mode === 'live') {
      statusTitle = 'LIVE';
      statusSubtitle = 'GFS CYCLE';
    } else {
      statusTitle = 'HISTORICAL';
      statusSubtitle = 'DATA AVAILABLE';
    }
  } else {
    statusState = 'offline';
    statusTitle = 'BACKEND CONNECTION FAILED';
    statusSubtitle = healthError || 'http://localhost:8000/api/v1/health unreachable';
  }

  const formatCycle = (iso) => {
    if (!iso) return 'PENDING';
    try {
      const parts = iso.split('T');
      const date = parts[0];
      const time = (parts[1] || '').slice(0, 5);
      return `${date} ${time}Z`;
    } catch {
      return 'OK';
    }
  };

  const modelVersion = health?.model_version ? health.model_version.toUpperCase() : 'V1';
  const dataSource = health?.ingestion_mode === 'live' ? 'LIVE GFS' : 'ARCHIVE';

  return (
    <header className="dashboard-header">
      {/* Left: Meteorological Station Identifier */}
      <div className="header-brand-group">
        <div className="header-brand-title">
          <Activity size={14} style={{ color: 'var(--accent-cyan)' }} />
          <span>FORECAST-BUST</span>
        </div>
        <div className="header-brand-subtitle">
          Atmospheric Reliability Analysis
        </div>
      </div>

      {/* Center: Operational Telemetry Bar */}
      <div className="header-telemetry-bar">
        <div className="telemetry-item">
          <span className="telemetry-label">MODEL</span>
          <span className="telemetry-value">{modelVersion}</span>
        </div>

        <span className="telemetry-sep">/</span>

        <div className="telemetry-item">
          <span className="telemetry-label">DOMAIN</span>
          <span className="telemetry-value">5°–35°N / 65°–100°E (0.5°)</span>
        </div>

        <span className="telemetry-sep">/</span>

        <div className="telemetry-item">
          <span className="telemetry-label">DATA</span>
          <span className="telemetry-value">{dataSource}</span>
        </div>

        <span className="telemetry-sep">/</span>

        <div className="telemetry-item">
          <span className="telemetry-label">CYCLE</span>
          <span className="telemetry-value" style={{ color: 'var(--accent-cyan)' }}>
            {formatCycle(health?.last_success_time)}
          </span>
        </div>
      </div>

      {/* Right: Station Status & Operational Controls */}
      <div className="header-actions-group">
        <div className={`station-status-indicator ${statusState}`}>
          <span className="station-status-dot" />
          <span>{statusTitle}</span>
          <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>{statusSubtitle}</span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isRefreshing || isIngesting}
          className="station-btn"
          title="Refresh forecast telemetry"
        >
          <RefreshCw size={12} className={isRefreshing ? 'spin-anim' : ''} />
          <span>REFRESH</span>
        </button>

        <button
          onClick={onIngest}
          disabled={isIngesting}
          className={`station-btn ${isIngesting ? 'btn-active' : ''}`}
          title="Trigger NOAA NOMADS live GFS cycle download"
        >
          <Download size={12} className={isIngesting ? 'spin-anim' : ''} />
          <span>{isIngesting ? 'INGESTING...' : 'INGEST'}</span>
        </button>
      </div>
    </header>
  );
};

export default OperationalHeader;

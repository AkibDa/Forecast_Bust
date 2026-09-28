import React, { useMemo } from 'react';

export const DashboardControls = ({
  coverage,
  currentDate,
  onDateChange,
  currentLeadDay,
  supportedLeadDays = [1],
  onSelectLeadDay,
  isLiveMode,
}) => {
  const { liveDates, historicalDates } = useMemo(() => {
    let live = [];
    let hist = [];

    if (coverage) {
      if (Array.isArray(coverage)) {
        hist = coverage;
      } else {
        live = coverage.live || [];
        hist = coverage.historical || [];
      }
    }

    return { liveDates: live, historicalDates: hist };
  }, [coverage]);

  const leadDays = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  return (
    <div className="dashboard-controls">
      {/* Left: Operational Strip (Date, Mode, Horizon) */}
      <div className="controls-left-strip">
        <div className="control-item">
          <span className="control-label">FORECAST DATE</span>
          <select
            value={currentDate || ''}
            onChange={(e) => onDateChange(e.target.value)}
            className="station-select"
          >
            {liveDates.length > 0 && (
              <optgroup label="Operational Live GFS">
                {liveDates.map((d) => (
                  <option key={`live-${d}`} value={d}>
                    {d} (Live GFS)
                  </option>
                ))}
              </optgroup>
            )}

            {historicalDates.length > 0 && (
              <optgroup label="TIGGE Historical Archive">
                {historicalDates.map((d) => (
                  <option key={`hist-${d}`} value={d}>
                    {d} (TIGGE Archive)
                  </option>
                ))}
              </optgroup>
            )}

            {currentDate &&
              !liveDates.includes(currentDate) &&
              !historicalDates.includes(currentDate) && (
                <option value={currentDate}>{currentDate} (Selected)</option>
              )}
          </select>
        </div>

        <div className="control-item">
          <span className="control-label">MODE</span>
          {isLiveMode ? (
            <span className="mode-badge">LIVE GFS</span>
          ) : (
            <span className="mode-badge archive">TIGGE ARCHIVE</span>
          )}
        </div>

        <div className="control-item">
          <span className="control-label">HORIZON</span>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            D+{currentLeadDay} (+{currentLeadDay * 24}h)
          </span>
        </div>
      </div>

      {/* Right: Lead Day Selection Strip */}
      <div className="controls-right-strip">
        <span className="control-label">LEAD HORIZONS</span>
        <div className="lead-day-strip">
          {leadDays.map((day) => {
            const isSupported = supportedLeadDays.includes(day);
            const isSelected = currentLeadDay === day;

            return (
              <button
                key={`lead-${day}`}
                type="button"
                onClick={() => isSupported && onSelectLeadDay(day)}
                disabled={!isSupported}
                className={`lead-day-btn ${isSelected ? 'active' : ''}`}
                title={
                  !isSupported
                    ? 'D+2 through D+10 unavailable for current live cycle.'
                    : `Horizon +${day * 24}h (D+${day})`
                }
              >
                D+{day}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DashboardControls;

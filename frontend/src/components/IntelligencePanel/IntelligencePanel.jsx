import React from 'react';
import { Target, Layers } from 'lucide-react';
import GridHeaderCard from './GridHeaderCard';
import BustProbabilityCard from './BustProbabilityCard';
import DriversCard from './DriversCard';
import AnalogCasesCard from './AnalogCasesCard';
import OperationalBriefCard from './OperationalBriefCard';

export const IntelligencePanel = ({
  selectedGrid,
  onDeselectGrid,
  currentLeadDay,
  featureProps,
  explanationData,
  explanationLoading,
  explanationError,
  stats,
  dataSource = 'live',
}) => {
  if (!selectedGrid) {
    return (
      <aside className="dashboard-intelligence">
        <div className="station-empty-state">
          <div
            style={{
              width: '40px',
              height: '40px',
              border: '1px solid var(--border-main)',
              borderRadius: '2px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-cyan)',
              marginBottom: '12px',
              background: 'var(--bg-app)',
            }}
          >
            <Target size={20} />
          </div>

          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '0.6px',
              textTransform: 'uppercase',
              marginBottom: '6px',
            }}
          >
            NO FORECAST CELL SELECTED
          </div>

          <p
            style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              lineHeight: 1.5,
              maxWidth: '260px',
              marginBottom: '16px',
            }}
          >
            Select any 0.5° grid point on the map to evaluate point-level reliability metrics:
          </p>

          <div
            style={{
              width: '100%',
              maxWidth: '260px',
              background: 'var(--bg-app)',
              border: '1px solid var(--border-main)',
              borderRadius: '2px',
              padding: '10px',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              textAlign: 'left',
              color: 'var(--text-muted)',
              lineHeight: 1.6,
            }}
          >
            <div
              style={{
                color: 'var(--text-primary)',
                fontWeight: 600,
                marginBottom: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Layers size={11} style={{ color: 'var(--accent-cyan)' }} />
              <span>DIAGNOSTIC SUITE</span>
            </div>
            <div>• Calibrated confidence & bust tail</div>
            <div>• Atmospheric SHAP drivers</div>
            <div>• Historical ERA5 regime analogs</div>
            <div>• Synoptic operational brief</div>
            <div>• 10-day horizon trajectory</div>
          </div>
        </div>
      </aside>
    );
  }

  const confScore = featureProps?.confidence_score ?? 0.985;
  const bustProb = featureProps?.bust_probability ?? 0.015;

  return (
    <aside className="dashboard-intelligence">
      {/* 1. Grid Coordinates & Horizon Header */}
      <GridHeaderCard
        gridId={selectedGrid}
        leadDay={currentLeadDay}
        dataSource={dataSource}
        onDeselect={onDeselectGrid}
      />

      {/* 2. Reliability Index & Bust Tail Probability */}
      <BustProbabilityCard
        confidenceScore={confScore}
        bustProbability={bustProb}
        stats={stats}
      />

      {/* 3. Atmospheric SHAP Drivers */}
      <DriversCard
        drivers={explanationData?.top_drivers || []}
        loading={explanationLoading}
        error={explanationError}
      />

      {/* 4. Historical Analog Regimes */}
      <AnalogCasesCard
        analogs={explanationData?.analogs || []}
        loading={explanationLoading}
        error={explanationError}
      />

      {/* 5. Synoptic Operational Brief */}
      <OperationalBriefCard
        leadDay={currentLeadDay}
        bustProbability={bustProb}
        drivers={explanationData?.top_drivers || []}
        analogs={explanationData?.analogs || []}
        dataSource={dataSource}
      />
    </aside>
  );
};

export default IntelligencePanel;

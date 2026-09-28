import React, { useState, useEffect, useMemo, useCallback } from 'react';
import useSystemHealth from './hooks/useSystemHealth';
import useConfidenceMap from './hooks/useConfidenceMap';
import useGridDetails from './hooks/useGridDetails';

import OperationalHeader from './components/Header/OperationalHeader';
import DashboardControls from './components/Controls/DashboardControls';
import LeafletConfidenceMap from './components/Map/LeafletConfidenceMap';
import IntelligencePanel from './components/IntelligencePanel/IntelligencePanel';
import ConfidenceTrajectoryBar from './components/Trajectory/ConfidenceTrajectoryBar';
import { X } from 'lucide-react';
import './App.css';

export function App() {
  useEffect(() => {
    console.log('[APP] mounted');
  }, []);

  // 1. Backend Health & Coverage State
  const {
    health,
    coverage,
    loading: healthLoading,
    ingesting,
    error: healthError,
    refreshHealth,
    triggerManualIngest,
  } = useSystemHealth();

  // 2. Active Query State
  const [forecastDate, setForecastDate] = useState('');
  const [currentLeadDay, setCurrentLeadDay] = useState(1);
  const [selectedGrid, setSelectedGrid] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [dismissedAlert, setDismissedAlert] = useState(false);

  // 3. Dynamic Date Initialization (from backend coverage)
  useEffect(() => {
    if (!forecastDate && coverage) {
      if (coverage.live && coverage.live.length > 0) {
        setForecastDate(coverage.live[0]);
      } else if (coverage.historical && coverage.historical.length > 0) {
        const latestHist = coverage.historical[coverage.historical.length - 1];
        setForecastDate(latestHist);
      } else if (Array.isArray(coverage) && coverage.length > 0) {
        setForecastDate(coverage[coverage.length - 1]);
      }
    }
  }, [coverage, forecastDate]);

  // 4. Mode Determination (Live GFS vs TIGGE Archive)
  const isLiveMode = useMemo(() => {
    if (!forecastDate) return true;
    if (coverage?.live && coverage.live.includes(forecastDate)) {
      return true;
    }
    try {
      const dt = new Date(forecastDate);
      const now = new Date();
      const diffDays = (now - dt) / (1000 * 60 * 60 * 24);
      return diffDays <= 5 && dt.getFullYear() >= 2026;
    } catch {
      return false;
    }
  }, [forecastDate, coverage]);

  // 5. Supported Lead Days Enforcing (Live mode supports D1 only; Archive supports D1-D10)
  const supportedLeadDays = useMemo(() => {
    if (isLiveMode) {
      return [1];
    }
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  }, [isLiveMode]);

  // Automatically reset to Day 1 if switching to live mode while on Day > 1
  useEffect(() => {
    if (isLiveMode && currentLeadDay > 1) {
      setCurrentLeadDay(1);
    }
  }, [isLiveMode, currentLeadDay]);

  // 6. Confidence Map Query Hook (Do not request map too early before health & coverage are ready)
  const isReady = Boolean(health && coverage && forecastDate);

  const {
    mapData,
    loading: mapLoading,
    error: mapError,
    stats,
    getBustColor,
    refetchMap,
  } = useConfidenceMap(forecastDate, currentLeadDay, isReady);

  // 7. Grid Details Query Hook
  const {
    timeseriesData,
    explanationData,
    timeseriesLoading,
    explanationLoading,
    timeseriesError,
    explanationError,
    clearSelection,
    refetchTimeseries,
    refetchExplanation,
  } = useGridDetails(selectedGrid, forecastDate, currentLeadDay);

  // 8. Find feature properties for currently selected grid
  const selectedFeatureProps = useMemo(() => {
    if (!selectedGrid || !mapData?.features) return null;
    const match = mapData.features.find(
      (f) => f.properties?.grid_id === selectedGrid
    );
    return match ? match.properties : null;
  }, [selectedGrid, mapData]);

  // 9. Manual Ingestion Handler
  const handleIngest = async () => {
    try {
      setDismissedAlert(false);
      await triggerManualIngest();
      await refetchMap();
    } catch (err) {
      console.error('Manual ingest error:', err);
    }
  };

  // 10. Dashboard Refresh Handler
  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      await Promise.all([
        refreshHealth(),
        refetchMap(),
        selectedGrid ? refetchTimeseries() : Promise.resolve(),
        selectedGrid ? refetchExplanation() : Promise.resolve(),
      ]);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleSelectGrid = useCallback((gridId) => {
    setSelectedGrid(gridId);
  }, []);

  const handleDeselectGrid = useCallback(() => {
    setSelectedGrid(null);
    clearSelection();
  }, [clearSelection]);

  const activeSource = mapData?.metadata?.data_source || (isLiveMode ? 'live' : 'historical');

  return (
    <div className="dashboard-app">
      {/* 1. Operational Telemetry Header */}
      <OperationalHeader
        health={health}
        healthLoading={healthLoading}
        healthError={healthError}
        isIngesting={ingesting}
        onIngest={handleIngest}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* 2. Forecast Control Strip: Date, Mode, Horizon, D1–D10 */}
      <DashboardControls
        coverage={coverage}
        currentDate={forecastDate}
        onDateChange={(newDate) => {
          setForecastDate(newDate);
          setDismissedAlert(false);
        }}
        currentLeadDay={currentLeadDay}
        supportedLeadDays={supportedLeadDays}
        onSelectLeadDay={(day) => {
          setCurrentLeadDay(day);
          setDismissedAlert(false);
        }}
        isLiveMode={isLiveMode}
      />

      {/* Operational Message / Alert Strip */}
      {(mapError || healthError) && !dismissedAlert && (
        <div
          style={{
            background: 'var(--bg-panel)',
            borderBottom: '1px solid var(--border-main)',
            borderLeft: '3px solid var(--warning-amber)',
            padding: '4px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '10px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-primary)',
            zIndex: 80,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--warning-amber)', fontWeight: 700 }}>⚠ OPERATIONAL ALERT:</span>
            <span>
              {mapError?.includes('timed out') || healthError?.includes('timed out')
                ? 'DATA REQUEST DELAY — Confidence field retained from previous state.'
                : mapError || healthError}
            </span>
          </div>
          <button
            onClick={() => setDismissedAlert(true)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '2px',
            }}
            title="Dismiss alert"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* 3. Main Workstation Space: Leaflet Map (Left) + Intelligence Panel (Right) */}
      <main className="dashboard-main">
        {/* Leaflet Map: The primary visual hero */}
        <LeafletConfidenceMap
          mapData={mapData}
          loading={mapLoading}
          stats={stats}
          getBustColor={getBustColor}
          selectedGrid={selectedGrid}
          onSelectGrid={handleSelectGrid}
          currentLeadDay={currentLeadDay}
        />

        {/* Intelligence Panel: Independently vertically scrollable */}
        <IntelligencePanel
          selectedGrid={selectedGrid}
          onDeselectGrid={handleDeselectGrid}
          currentLeadDay={currentLeadDay}
          featureProps={selectedFeatureProps}
          explanationData={explanationData}
          explanationLoading={explanationLoading}
          explanationError={explanationError}
          stats={stats}
          dataSource={activeSource}
        />
      </main>

      {/* 4. Full-Width Forecast Horizon Trajectory Timeline */}
      <ConfidenceTrajectoryBar
        selectedGrid={selectedGrid}
        timeseriesData={timeseriesData}
        loading={timeseriesLoading}
        error={timeseriesError}
        currentLeadDay={currentLeadDay}
        onSelectLeadDay={(day) => {
          if (supportedLeadDays.includes(day)) {
            setCurrentLeadDay(day);
          }
        }}
      />
    </div>
  );
}

export default App;

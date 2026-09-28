import { useState, useEffect, useCallback, useRef } from 'react';
import { getHealth, getCoverage, triggerIngestion } from '../services/api';

export const useSystemHealth = () => {
  const [health, setHealth] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const fetchHealthAndCoverage = useCallback(async () => {
    // Abort previous in-flight request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    console.log('[HEALTH] request started');
    console.log('[COVERAGE] request started');
    setLoading(true);
    setError(null);

    try {
      const [healthRes, coverageRes] = await Promise.allSettled([
        getHealth(controller.signal),
        getCoverage(null, controller.signal),
      ]);

      if (controller.signal.aborted) {
        console.log('[HEALTH/COVERAGE] requests aborted');
        return null;
      }

      console.log('[HEALTH] request finished', healthRes.status);
      console.log('[COVERAGE] request finished', coverageRes.status);

      let lastErr = null;

      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value);
        if (healthRes.value?.data_coverage_range) {
          setCoverage(healthRes.value.data_coverage_range);
        }
      } else if (healthRes.reason?.name !== 'CanceledError') {
        lastErr = healthRes.reason;
        console.error('getHealth failed:', healthRes.reason);
      }

      if (coverageRes.status === 'fulfilled') {
        setCoverage(coverageRes.value);
      } else if (coverageRes.reason?.name !== 'CanceledError') {
        if (!lastErr) lastErr = coverageRes.reason;
        console.error('getCoverage failed:', coverageRes.reason);
      }

      if (healthRes.status !== 'fulfilled' && coverageRes.status !== 'fulfilled') {
        const errorMsg = lastErr?.message || 'Failed to connect to backend telemetry.';
        setError(errorMsg);
        return null;
      }

      return {
        health: healthRes.status === 'fulfilled' ? healthRes.value : null,
        coverage: coverageRes.status === 'fulfilled' ? coverageRes.value : healthRes.value?.data_coverage_range,
      };
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === '__CANCELLED__') return null;
      console.error('System health check error:', err);
      setError(err.message || 'Failed to connect to backend telemetry.');
      return null;
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchHealthAndCoverage();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchHealthAndCoverage]);

  const handleManualIngest = async () => {
    try {
      setIngesting(true);
      setError(null);
      await triggerIngestion();
      // Re-fetch system health and coverage after ingestion
      const result = await fetchHealthAndCoverage();
      return result;
    } catch (err) {
      console.error('Ingestion failed:', err);
      setError(err.message || 'NOAA GFS ingestion failed.');
      throw err;
    } finally {
      setIngesting(false);
    }
  };

  return {
    health,
    coverage,
    loading,
    ingesting,
    error,
    refreshHealth: fetchHealthAndCoverage,
    triggerManualIngest: handleManualIngest,
  };
};

export default useSystemHealth;

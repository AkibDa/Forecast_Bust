import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { getConfidenceMap } from '../services/api';

export const useConfidenceMap = (forecastDate, leadDay, enabled = true) => {
  const [mapData, setMapData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const fetchMap = useCallback(async () => {
    if (!enabled || !forecastDate || !leadDay) {
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    console.log(`[CONFIDENCE MAP] request started forecastDate=${forecastDate} leadDay=${leadDay}`);
    setLoading(true);
    setError(null);

    try {
      const data = await getConfidenceMap(forecastDate, leadDay, controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      console.log(`[CONFIDENCE MAP] request finished forecastDate=${forecastDate} leadDay=${leadDay}`);
      setMapData(data);
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === '__CANCELLED__' || err.name === 'AbortError') {
        console.log(`[CONFIDENCE MAP] request cancelled forecastDate=${forecastDate} leadDay=${leadDay}`);
        return;
      }
      console.error('Failed to load confidence map:', err);
      setError(err.message || 'Failed to load geospatial confidence map.');
      setMapData(null);
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, [enabled, forecastDate, leadDay]);

  useEffect(() => {
    fetchMap();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchMap]);

  // Compute distribution metrics across grid cells to enable dynamic, high-variance color mapping
  const stats = useMemo(() => {
    if (!mapData?.features || mapData.features.length === 0) {
      return null;
    }

    const bustProbs = [];
    const confScores = [];

    for (const f of mapData.features) {
      const p = f.properties?.bust_probability;
      const c = f.properties?.confidence_score;
      if (typeof p === 'number' && !isNaN(p)) bustProbs.push(p);
      if (typeof c === 'number' && !isNaN(c)) confScores.push(c);
    }

    if (bustProbs.length === 0) return null;

    bustProbs.sort((a, b) => a - b);
    const n = bustProbs.length;

    const getP = (p) => bustProbs[Math.min(Math.floor((p / 100) * n), n - 1)];

    return {
      count: n,
      min: bustProbs[0],
      p10: getP(10),
      p25: getP(25),
      p50: getP(50),
      p75: getP(75),
      p90: getP(90),
      p95: getP(95),
      max: bustProbs[n - 1],
      avg: bustProbs.reduce((a, b) => a + b, 0) / n,
    };
  }, [mapData]);

  /**
   * Percentile-based color scale for bust probability.
   * Maps low bust risk to deep cyan/blue and higher relative bust risk to amber/coral/red.
   */
  const getBustColor = useCallback(
    (bustProb) => {
      if (typeof bustProb !== 'number' || isNaN(bustProb)) return '#334155';
      if (!stats) return '#0ea5e9';

      const { min, p25, p50, p75, p90, max } = stats;

      // Handle narrow distribution case
      if (max - min < 0.0001) {
        return '#06b6d4'; // Uniform cyan
      }

      if (bustProb <= p25) {
        // Lowest quartile: Deep Blue (Highest confidence)
        return '#075985';
      } else if (bustProb <= p50) {
        // Second quartile: Blue-Cyan
        return '#0e7490';
      } else if (bustProb <= p75) {
        // Third quartile: Muted Amber (Moderate risk)
        return '#92400e';
      } else if (bustProb <= p90) {
        // High risk: Muted Orange
        return '#b45309';
      } else {
        // Peak risk: Brick Red
        return '#991b1b';
      }
    },
    [stats]
  );

  return {
    mapData,
    loading,
    error,
    stats,
    getBustColor,
    refetchMap: fetchMap,
  };
};

export default useConfidenceMap;

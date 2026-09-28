import { useState, useEffect, useCallback, useRef } from 'react';
import { getTimeseries, getExplanation } from '../services/api';

export const useGridDetails = (selectedGrid, forecastDate, leadDay) => {
  const [timeseriesData, setTimeseriesData] = useState(null);
  const [explanationData, setExplanationData] = useState(null);
  const [timeseriesLoading, setTimeseriesLoading] = useState(false);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [timeseriesError, setTimeseriesError] = useState(null);
  const [explanationError, setExplanationError] = useState(null);
  const tsAbortRef = useRef(null);
  const expAbortRef = useRef(null);

  const fetchTimeseries = useCallback(async () => {
    if (!selectedGrid || !forecastDate) {
      setTimeseriesData(null);
      return;
    }

    if (tsAbortRef.current) {
      tsAbortRef.current.abort();
    }
    const controller = new AbortController();
    tsAbortRef.current = controller;

    console.log(`[GRID DETAILS] timeseries request started grid=${selectedGrid} date=${forecastDate}`);
    setTimeseriesLoading(true);
    setTimeseriesError(null);

    try {
      const data = await getTimeseries(selectedGrid, forecastDate, controller.signal);
      if (controller.signal.aborted) return;
      console.log(`[GRID DETAILS] timeseries request finished grid=${selectedGrid}`);
      setTimeseriesData(data);
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === '__CANCELLED__' || err.name === 'AbortError') return;
      console.error('Failed to load timeseries for', selectedGrid, err);
      setTimeseriesError(err.message || 'Timeseries unavailable for this cell.');
      setTimeseriesData(null);
    } finally {
      if (tsAbortRef.current === controller) {
        setTimeseriesLoading(false);
      }
    }
  }, [selectedGrid, forecastDate]);

  const fetchExplanation = useCallback(async () => {
    if (!selectedGrid || !forecastDate || !leadDay) {
      setExplanationData(null);
      return;
    }

    if (expAbortRef.current) {
      expAbortRef.current.abort();
    }
    const controller = new AbortController();
    expAbortRef.current = controller;

    console.log(`[GRID DETAILS] explanation request started grid=${selectedGrid} date=${forecastDate} lead=${leadDay}`);
    setExplanationLoading(true);
    setExplanationError(null);

    try {
      const data = await getExplanation(selectedGrid, forecastDate, leadDay, controller.signal);
      if (controller.signal.aborted) return;
      console.log(`[GRID DETAILS] explanation request finished grid=${selectedGrid}`);
      setExplanationData(data);
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === '__CANCELLED__' || err.name === 'AbortError') return;
      console.error('Failed to load explanation for', selectedGrid, err);
      setExplanationError(err.message || 'Explainability payload unavailable.');
      setExplanationData(null);
    } finally {
      if (expAbortRef.current === controller) {
        setExplanationLoading(false);
      }
    }
  }, [selectedGrid, forecastDate, leadDay]);

  useEffect(() => {
    fetchTimeseries();
    return () => {
      if (tsAbortRef.current) {
        tsAbortRef.current.abort();
      }
    };
  }, [fetchTimeseries]);

  useEffect(() => {
    fetchExplanation();
    return () => {
      if (expAbortRef.current) {
        expAbortRef.current.abort();
      }
    };
  }, [fetchExplanation]);

  const clearSelection = () => {
    setTimeseriesData(null);
    setExplanationData(null);
    setTimeseriesError(null);
    setExplanationError(null);
  };

  return {
    timeseriesData,
    explanationData,
    timeseriesLoading,
    explanationLoading,
    timeseriesError,
    explanationError,
    loading: timeseriesLoading || explanationLoading,
    clearSelection,
    refetchTimeseries: fetchTimeseries,
    refetchExplanation: fetchExplanation,
  };
};

export default useGridDetails;

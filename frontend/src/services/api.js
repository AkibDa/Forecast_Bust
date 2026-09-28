import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60s timeout for data loading and parquet operations
  headers: {
    'Accept': 'application/json, application/geo+json',
  },
});

console.log('[Forecast-Bust API] BASE URL:', client.defaults.baseURL);

/**
 * Standardize error messages from backend FastAPI responses
 */
export const parseApiError = (error) => {
  if (axios.isCancel(error) || error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
    return '__CANCELLED__';
  }

  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return 'Request timed out while waiting for server response.';
    }
    return 'Cannot connect to backend server. Ensure FastAPI is running on ' + API_BASE_URL;
  }

  const { status, data } = error.response;

  // Extract message from standard FastAPI / custom formats
  let serverMessage = '';
  if (data?.error?.message) {
    serverMessage = data.error.message;
  } else if (data?.detail) {
    serverMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
  } else if (typeof data === 'string') {
    serverMessage = data;
  }

  // Exact meteorological workstation operational error mapping
  if (status === 422) {
    if (
      serverMessage.toLowerCase().includes('supported_lead_days=[1]') ||
      serverMessage.toLowerCase().includes('live mode') ||
      serverMessage.toLowerCase().includes('lead_day')
    ) {
      return 'D+2 unavailable for current live cycle';
    }
    return serverMessage || 'Invalid parameter (HTTP 422).';
  }

  if (status === 503) {
    return 'LIVE DATA UNAVAILABLE — Using available historical/cache data.';
  }

  if (status === 404) {
    return 'NO FORECAST DATA FOR THIS GRID / DATE';
  }

  if (status === 501) {
    return 'Operational regime clustering is not yet available.';
  }

  return serverMessage || `Server returned status ${status}.`;
};

/**
 * API service endpoints with AbortSignal support
 */
export const getHealth = async (signal) => {
  try {
    const res = await client.get('/api/v1/health', { signal });
    return res.data;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
      throw err;
    }
    throw new Error(parseApiError(err));
  }
};

export const getCoverage = async (mode = null, signal) => {
  try {
    const params = mode ? { mode } : {};
    const res = await client.get('/api/v1/coverage', { params, signal });
    return res.data;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
      throw err;
    }
    throw new Error(parseApiError(err));
  }
};

export const triggerIngestion = async () => {
  try {
    const res = await client.post('/api/v1/ingest');
    return res.data;
  } catch (err) {
    throw new Error(parseApiError(err));
  }
};

export const getConfidenceMap = async (forecastDate, leadDay, signal) => {
  try {
    const res = await client.get('/api/v1/confidence-map', {
      params: {
        forecast_date: forecastDate,
        lead_day: leadDay,
      },
      signal,
    });
    return res.data;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
      throw err;
    }
    throw new Error(parseApiError(err));
  }
};

export const getTimeseries = async (gridId, forecastDate, signal) => {
  try {
    const res = await client.get(`/api/v1/grid/${gridId}/timeseries`, {
      params: {
        forecast_date: forecastDate,
      },
      signal,
    });
    return res.data;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
      throw err;
    }
    throw new Error(parseApiError(err));
  }
};

export const getExplanation = async (gridId, forecastDate, leadDay, signal) => {
  try {
    const res = await client.get(`/api/v1/grid/${gridId}/explanation`, {
      params: {
        forecast_date: forecastDate,
        lead_day: leadDay,
      },
      signal,
    });
    return res.data;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
      throw err;
    }
    throw new Error(parseApiError(err));
  }
};

export default {
  getHealth,
  getCoverage,
  triggerIngestion,
  getConfidenceMap,
  getTimeseries,
  getExplanation,
  parseApiError,
};

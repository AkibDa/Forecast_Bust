import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Maximize2, Target, Loader2, HelpCircle } from 'lucide-react';
import indiaStatesGeoJson from '../../assets/india_states.json';

const DOMAIN_BOUNDS = [
  [5.0, 65.0],
  [37.5, 100.0],
];
const DEFAULT_CENTER = [23.5, 82.0];
const DEFAULT_ZOOM = 5;

const GRID_ROWS = 61; // Model grid: Lat 35.0 (row 0) to 5.0 (row 60)
const GRID_COLS = 71; // Model grid: Lon 65.0 (col 0) to 100.0 (col 70)
const LAT_GRID_MAX = 35.0;
const LAT_GRID_MIN = 5.0;
const LON_GRID_MIN = 65.0;
const LON_GRID_MAX = 100.0;
const RES = 0.5;

// India administrative overlay boundaries covering entire national geometry (up to ~37.10°N)
const LAT_MASK_MAX = 37.5;
const LAT_MASK_MIN = 5.0;
const LON_MASK_MIN = 65.0;
const LON_MASK_MAX = 100.0;

const BASE_ALPHA = 225; // Rich 88% central data opacity

function latToMerc(lat) {
  const rad = (lat * Math.PI) / 180;
  return Math.log(Math.tan(Math.PI / 4 + rad / 2));
}

function mercToLat(merc) {
  return ((2 * Math.atan(Math.exp(merc)) - Math.PI / 2) * 180) / Math.PI;
}

const MERC_MAX = latToMerc(LAT_MASK_MAX);
const MERC_MIN = latToMerc(LAT_MASK_MIN);
const MERC_SPAN = MERC_MAX - MERC_MIN;
const LON_SPAN = LON_MASK_MAX - LON_MASK_MIN;

function lonToCanvasX(lon, width) {
  return ((lon - LON_MASK_MIN) / LON_SPAN) * (width - 1);
}

function latToCanvasY(lat, height) {
  const m = latToMerc(lat);
  return ((MERC_MAX - m) / MERC_SPAN) * (height - 1);
}

function canvasYToLat(py, height) {
  const frac = py / (height - 1);
  const m = MERC_MAX - frac * MERC_SPAN;
  return mercToLat(m);
}

// Precompute bounding boxes and polygons for ray casting against India boundaries
const INDIA_POLYGONS = [];
if (indiaStatesGeoJson?.features) {
  for (const feature of indiaStatesGeoJson.features) {
    const geom = feature.geometry;
    if (!geom) continue;
    const polygons =
      geom.type === 'Polygon'
        ? [geom.coordinates]
        : geom.type === 'MultiPolygon'
        ? geom.coordinates
        : [];
    for (const poly of polygons) {
      if (!poly || !poly[0] || poly[0].length < 3) continue;
      const outerRing = poly[0];
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;
      for (let i = 0; i < outerRing.length; i++) {
        const x = outerRing[i][0];
        const y = outerRing[i][1];
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
      INDIA_POLYGONS.push({ bbox: [minX, minY, maxX, maxY], poly });
    }
  }
}

function pointInRing(x, y, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function isPointInIndia(lat, lon) {
  for (let p = 0; p < INDIA_POLYGONS.length; p++) {
    const item = INDIA_POLYGONS[p];
    const bbox = item.bbox;
    if (lon < bbox[0] || lon > bbox[2] || lat < bbox[1] || lat > bbox[3]) {
      continue;
    }
    const poly = item.poly;
    if (pointInRing(lon, lat, poly[0])) {
      let inHole = false;
      for (let h = 1; h < poly.length; h++) {
        if (pointInRing(lon, lat, poly[h])) {
          inHole = true;
          break;
        }
      }
      if (!inHole) return true;
    }
  }
  return false;
}

// Ocean labels definitions for subtle cartographic context
const OCEAN_LABELS = [
  { name: 'ARABIAN SEA', coords: [16.0, 68.0] },
  { name: 'BAY OF BENGAL', coords: [15.0, 89.0] },
  { name: 'INDIAN OCEAN', coords: [4.5, 78.5] },
];

// Programmatic map movement controller
const MapViewController = ({ selectedCoords, resetTrigger }) => {
  const map = useMap();

  useEffect(() => {
    if (resetTrigger > 0) {
      map.flyToBounds(DOMAIN_BOUNDS, { padding: [16, 16], duration: 0.6 });
    }
  }, [resetTrigger, map]);

  useEffect(() => {
    if (selectedCoords && selectedCoords.length === 2) {
      map.flyTo(selectedCoords, Math.max(map.getZoom(), 7), { duration: 0.5 });
    }
  }, [selectedCoords, map]);

  return null;
};

// Initialize custom z-index Leaflet panes with pointer-events: none to allow clicks to bubble
const MapPaneInitializer = () => {
  const map = useMap();

  useEffect(() => {
    if (!map) return;
    window._leaflet_map = map;
    if (!map.getPane('forecastPane')) {
      const p = map.createPane('forecastPane');
      p.style.zIndex = '400';
      p.style.pointerEvents = 'none';
    }
    if (!map.getPane('boundariesPane')) {
      const p = map.createPane('boundariesPane');
      p.style.zIndex = '450';
      p.style.pointerEvents = 'none';
    }
    if (!map.getPane('annotationsPane')) {
      const p = map.createPane('annotationsPane');
      p.style.zIndex = '500';
      p.style.pointerEvents = 'none';
    }
  }, [map]);

  return null;
};

/**
 * Global Map Click Handler
 * Restricts cell selection to clicks INSIDE India's administrative boundaries.
 * Snaps to nearest 0.5° canonical grid ID.
 */
const MapClickHandler = ({ onSelectGrid }) => {
  useMapEvents({
    click(e) {
      const clickedLat = e.latlng.lat;
      const clickedLon = e.latlng.lng;

      // Only handle clicks inside India administrative boundaries
      if (!isPointInIndia(clickedLat, clickedLon)) {
        console.log(`[MAP CLICK] (${clickedLat.toFixed(2)}, ${clickedLon.toFixed(2)}) is outside India - ignoring.`);
        return;
      }

      // Convert to nearest 0.5° coordinate
      let lat = Math.round(clickedLat / 0.5) * 0.5;
      let lon = Math.round(clickedLon / 0.5) * 0.5;

      // Clamp to LAT 5.0–35.0, LON 65.0–100.0
      lat = Math.max(5.0, Math.min(35.0, lat));
      lon = Math.max(65.0, Math.min(100.0, lon));

      // Construct canonical grid ID
      const latNum = Number(lat.toFixed(2));
      const lonNum = Number(lon.toFixed(2));
      const gridId = `${latNum.toFixed(2)}_${lonNum.toFixed(2)}`;

      console.log(`[MAP CLICK] inside India (${clickedLat.toFixed(2)}, ${clickedLon.toFixed(2)}) -> snapped to ${gridId}`);

      if (onSelectGrid) {
        onSelectGrid(gridId);
      }
    },
  });

  return null;
};

/**
 * LAYER 2: Bilinearly Interpolated India-Clipped Meteorological Skin
 * Numerically interpolates the 61x71 0.5° forecast values across a high-resolution canvas (1401x1201),
 * projects vertices to match Web Mercator coordinates, and composites with an India GeoJSON alpha mask
 * (destination-in) so the weather field is painted strictly inside India's administrative boundaries.
 */
const SmoothBilinearForecastField = ({ mapData, stats }) => {
  const map = useMap();
  const layerRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }

    if (!mapData?.features || !mapData.features.length) return;

    // 1. Populate raw 61x71 grid (preserve NaN for unpopulated/missing cells)
    const rawGrid = new Float32Array(GRID_ROWS * GRID_COLS);
    rawGrid.fill(NaN);

    let observedMin = Infinity;
    let observedMax = -Infinity;

    for (let i = 0; i < mapData.features.length; i++) {
      const f = mapData.features[i];
      const coords = f.geometry?.coordinates;
      if (!coords || coords.length < 2) continue;
      const lon = coords[0];
      const lat = coords[1];

      const r = Math.round((LAT_GRID_MAX - lat) / RES);
      const c = Math.round((lon - LON_GRID_MIN) / RES);
      if (r >= 0 && r < GRID_ROWS && c >= 0 && c < GRID_COLS) {
        const val = f.properties?.bust_probability;
        if (typeof val === 'number' && !isNaN(val)) {
          rawGrid[r * GRID_COLS + c] = val;
          if (val < observedMin) observedMin = val;
          if (val > observedMax) observedMax = val;
        }
      }
    }

    if (observedMin === Infinity) observedMin = 0.0;
    if (observedMax === -Infinity) observedMax = 1.0;

    // 2. High-resolution output canvas (1401 x 1301 px covers up to 37.5°N)
    const outW = 1401;
    const outH = 1301;

    const canvas = document.createElement('canvas');
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext('2d');
    const imgData = ctx.createImageData(outW, outH);
    const data = imgData.data;

    // Continuous percentile thresholds
    const pMin = stats?.min ?? observedMin;
    const p25 = stats?.p25 ?? (pMin + 0.25 * (observedMax - pMin));
    const p50 = stats?.p50 ?? (pMin + 0.50 * (observedMax - pMin));
    const p75 = stats?.p75 ?? (pMin + 0.75 * (observedMax - pMin));
    const p90 = stats?.p90 ?? (pMin + 0.90 * (observedMax - pMin));
    const pMax = stats?.max ?? observedMax;

    // 3. Numerical Smoothstep Bilinear Interpolation across Web Mercator coordinates
    for (let py = 0; py < outH; py++) {
      const lat = canvasYToLat(py, outH);
      const clampedLat = Math.max(LAT_GRID_MIN, Math.min(LAT_GRID_MAX, lat));
      const v = (LAT_GRID_MAX - clampedLat) / RES;
      const y0 = Math.max(0, Math.min(GRID_ROWS - 2, Math.floor(v)));
      const y1 = y0 + 1;
      const uy = Math.max(0, Math.min(1, v - y0));
      const sy = uy * uy * (3 - 2 * uy);
      const y0_off = y0 * GRID_COLS;
      const y1_off = y1 * GRID_COLS;

      for (let px = 0; px < outW; px++) {
        const lon = LON_MASK_MIN + (px / (outW - 1)) * LON_SPAN;
        const clampedLon = Math.max(LON_GRID_MIN, Math.min(LON_GRID_MAX, lon));
        const u = (clampedLon - LON_GRID_MIN) / RES;
        const x0 = Math.max(0, Math.min(GRID_COLS - 2, Math.floor(u)));
        const x1 = x0 + 1;
        const ux = Math.max(0, Math.min(1, u - x0));
        const sx = ux * ux * (3 - 2 * ux);

        const idx = (py * outW + px) * 4;

        const v00 = rawGrid[y0_off + x0];
        const v10 = rawGrid[y0_off + x1];
        const v01 = rawGrid[y1_off + x0];
        const v11 = rawGrid[y1_off + x1];

        const ok00 = !isNaN(v00);
        const ok10 = !isNaN(v10);
        const ok01 = !isNaN(v01);
        const ok11 = !isNaN(v11);

        const w00 = (1 - sx) * (1 - sy);
        const w10 = sx * (1 - sy);
        const w01 = (1 - sx) * sy;
        const w11 = sx * sy;

        let interpolatedVal = 0;
        let validWeight = 0;

        if (ok00) { interpolatedVal += w00 * v00; validWeight += w00; }
        if (ok10) { interpolatedVal += w10 * v10; validWeight += w10; }
        if (ok01) { interpolatedVal += w01 * v01; validWeight += w01; }
        if (ok11) { interpolatedVal += w11 * v11; validWeight += w11; }

        if (validWeight < 0.25) {
          data[idx + 3] = 0;
          continue;
        }

        interpolatedVal = interpolatedVal / validWeight;
        const clampedVal = Math.max(pMin, Math.min(pMax, interpolatedVal));

        // Continuous color ramp across percentile stops
        let r, g, b;
        if (clampedVal <= p25) {
          const t = p25 > pMin ? (clampedVal - pMin) / (p25 - pMin) : 0;
          r = 4 + t * (7 - 4);
          g = 60 + t * (89 - 60);
          b = 95 + t * (133 - 95);
        } else if (clampedVal <= p50) {
          const t = p50 > p25 ? (clampedVal - p25) / (p50 - p25) : 0;
          r = 7 + t * (14 - 7);
          g = 89 + t * (116 - 89);
          b = 133 + t * (144 - 133);
        } else if (clampedVal <= p75) {
          const t = p75 > p50 ? (clampedVal - p50) / (p75 - p50) : 0;
          r = 14 + t * (146 - 14);
          g = 116 + t * (64 - 116);
          b = 144 + t * (14 - 144);
        } else if (clampedVal <= p90) {
          const t = p90 > p75 ? (clampedVal - p75) / (p90 - p75) : 0;
          r = 146 + t * (180 - 146);
          g = 64 + t * (83 - 64);
          b = 14 + t * (9 - 14);
        } else {
          const t = pMax > p90 ? Math.min(1, (clampedVal - p90) / (pMax - p90)) : 1;
          r = 180 + t * (153 - 180);
          g = 83 + t * (27 - 83);
          b = 9 + t * (27 - 9);
        }

        data[idx] = Math.round(r);
        data[idx + 1] = Math.round(g);
        data[idx + 2] = Math.round(b);
        data[idx + 3] = BASE_ALPHA;
      }
    }

    ctx.putImageData(imgData, 0, 0);

    // 4. Generate India Geographic Alpha Mask Canvas
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = outW;
    maskCanvas.height = outH;
    const maskCtx = maskCanvas.getContext('2d');
    maskCtx.fillStyle = '#ffffff';

    for (const feature of indiaStatesGeoJson.features) {
      const geom = feature.geometry;
      if (!geom) continue;

      const polygons =
        geom.type === 'Polygon'
          ? [geom.coordinates]
          : geom.type === 'MultiPolygon'
          ? geom.coordinates
          : [];

      for (const poly of polygons) {
        maskCtx.beginPath();
        for (const ring of poly) {
          if (!ring || ring.length < 3) continue;
          for (let i = 0; i < ring.length; i++) {
            const ptLon = ring[i][0];
            const ptLat = ring[i][1];
            const x = lonToCanvasX(ptLon, outW);
            const y = latToCanvasY(ptLat, outH);
            if (i === 0) maskCtx.moveTo(x, y);
            else maskCtx.lineTo(x, y);
          }
          maskCtx.closePath();
        }
        maskCtx.fill('evenodd');
      }
    }

    // 5. Composite: Clip Weather Field to India Administrative Geometry
    ctx.save();
    ctx.globalCompositeOperation = 'destination-in';
    ctx.drawImage(maskCanvas, 0, 0);
    ctx.restore();

    // 6. Attach as Leaflet ImageOverlay strictly clipped to meteorological domain
    const overlay = L.imageOverlay(canvas.toDataURL(), DOMAIN_BOUNDS, {
      pane: 'forecastPane',
      opacity: 1.0,
      interactive: false,
    });

    overlay.addTo(map);
    layerRef.current = overlay;

    return () => {
      if (layerRef.current && map) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map, mapData, stats]);

  return null;
};

/**
 * LAYER 3: India Administrative Boundaries Layer
 * Renders verified 36 states and union territories with uncropped Ladakh and J&K.
 * Above forecast field (boundariesPane), thin muted cyan/blue-grey boundary lines.
 */
const IndiaAdministrativeLayer = () => {
  const map = useMap();
  const layerRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }

    const adminLayer = L.geoJSON(indiaStatesGeoJson, {
      pane: 'boundariesPane',
      style: {
        fill: false,
        color: 'rgba(130, 200, 210, 0.45)',
        weight: 0.8,
        opacity: 0.8,
      },
    });

    adminLayer.addTo(map);
    layerRef.current = adminLayer;

    return () => {
      if (layerRef.current && map) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map]);

  return null;
};

/**
 * LAYER 4 & 5: State Codes, Ocean Labels, and Selected Cell Crosshair Locator
 */
const MapAnnotationsLayer = ({ selectedGrid, selectedCoords }) => {
  const map = useMap();
  const groupRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    if (groupRef.current) {
      map.removeLayer(groupRef.current);
      groupRef.current = null;
    }

    const group = L.layerGroup([], { pane: 'annotationsPane' });

    // 1. Subtle 2-letter state codes
    indiaStatesGeoJson.features.forEach((feat) => {
      const { code, label_lat, label_lon } = feat.properties;
      if (label_lat && label_lon && code) {
        // Skip tiny enclave labels to avoid visual clutter
        if (['CH', 'DL', 'DN', 'PY'].includes(code)) return;

        const labelIcon = L.divIcon({
          className: 'state-code-label',
          html: `<span>${code}</span>`,
          iconSize: [20, 14],
          iconAnchor: [10, 7],
        });

        L.marker([label_lat, label_lon], {
          icon: labelIcon,
          pane: 'annotationsPane',
          interactive: false,
        }).addTo(group);
      }
    });

    // 2. Subtle Ocean Cartographic Labels
    OCEAN_LABELS.forEach((ocean) => {
      const oceanIcon = L.divIcon({
        className: 'ocean-carto-label',
        html: `<span>${ocean.name}</span>`,
        iconSize: [120, 16],
        iconAnchor: [60, 8],
      });

      L.marker(ocean.coords, {
        icon: oceanIcon,
        pane: 'annotationsPane',
        interactive: false,
      }).addTo(group);
    });

    // 3. Selected cell precision crosshair locator
    if (selectedCoords && selectedCoords.length === 2) {
      const [lat, lon] = selectedCoords;
      const minLat = lat - 0.25;
      const maxLat = lat + 0.25;
      const minLon = lon - 0.25;
      const maxLon = lon + 0.25;

      // Cyan bounding box for active 0.5° cell
      L.polygon(
        [
          [minLat, minLon],
          [maxLat, minLon],
          [maxLat, maxLon],
          [minLat, maxLon],
        ],
        {
          pane: 'annotationsPane',
          color: '#18D8FF',
          weight: 2,
          fillColor: '#18D8FF',
          fillOpacity: 0.12,
          interactive: false,
        }
      ).addTo(group);

      // Precision crosshair center
      const crosshairIcon = L.divIcon({
        className: 'cell-crosshair',
        html: `
          <svg width="20" height="20" viewBox="0 0 20 20" style="overflow: visible;">
            <circle cx="10" cy="10" r="3" fill="#18D8FF" />
            <line x1="10" y1="2" x2="10" y2="7" stroke="#18D8FF" stroke-width="1.5" />
            <line x1="10" y1="13" x2="10" y2="18" stroke="#18D8FF" stroke-width="1.5" />
            <line x1="2" y1="10" x2="7" y2="10" stroke="#18D8FF" stroke-width="1.5" />
            <line x1="13" y1="10" x2="18" y2="10" stroke="#18D8FF" stroke-width="1.5" />
          </svg>
        `,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      });

      L.marker([lat, lon], {
        icon: crosshairIcon,
        pane: 'annotationsPane',
        interactive: false,
      }).addTo(group);
    }

    group.addTo(map);
    groupRef.current = group;

    return () => {
      if (groupRef.current && map) {
        map.removeLayer(groupRef.current);
        groupRef.current = null;
      }
    };
  }, [map, selectedGrid, selectedCoords]);

  return null;
};

export const LeafletConfidenceMap = ({
  mapData,
  loading,
  stats,
  _getBustColor,
  selectedGrid,
  onSelectGrid,
  _currentLeadDay = 1,
}) => {
  const [resetCount, setResetCount] = useState(0);
  const [showLegendInfo, setShowLegendInfo] = useState(false);

  const selectedCoords = useMemo(() => {
    if (!selectedGrid) return null;
    const parts = selectedGrid.split('_');
    if (parts.length === 2) {
      const lat = parseFloat(parts[0]);
      const lon = parseFloat(parts[1]);
      if (!isNaN(lat) && !isNaN(lon)) return [lat, lon];
    }
    return null;
  }, [selectedGrid]);

  const formatPct = (val) => {
    if (typeof val !== 'number' || isNaN(val)) return '-';
    return (val * 100).toFixed(2) + '%';
  };

  return (
    <div className="dashboard-map-panel">
      {/* Loading telemetry indicator */}
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: '10px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 600,
            background: 'rgba(16, 25, 35, 0.95)',
            border: '1px solid var(--accent-cyan)',
            padding: '4px 12px',
            borderRadius: '2px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--accent-cyan)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          }}
        >
          <Loader2 size={13} className="spin-anim" />
          <span>EVALUATING 4,331 GRID CELLS...</span>
        </div>
      )}

      {/* Map Control Buttons */}
      <div className="map-controls-overlay">
        <button
          onClick={() => setResetCount((c) => c + 1)}
          className="map-btn"
          title="Reset map view to India Subcontinent"
        >
          <Maximize2 size={13} />
        </button>
        {selectedCoords && (
          <button
            onClick={() => setResetCount((c) => c)}
            className="map-btn"
            style={{ color: '#18D8FF', borderColor: '#18D8FF' }}
            title="Recenter on selected forecast cell"
          >
            <Target size={13} />
          </button>
        )}
      </div>

      {/* Scientific Map Legend Overlay */}
      <div className="map-legend-overlay">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong style={{ color: 'var(--text-primary)', fontSize: '10px', letterSpacing: '0.4px' }}>
            BUST PROBABILITY (PERCENTILE SCALE)
          </strong>
          <button
            onClick={() => setShowLegendInfo(!showLegendInfo)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Percentile scale explanation"
          >
            <HelpCircle size={12} />
          </button>
        </div>

        <div className="legend-bar-container">
          <div style={{ flex: 1, background: '#075985' }} title="P0–P25 (Lowest risk / High confidence)" />
          <div style={{ flex: 1, background: '#0e7490' }} title="P25–P50 (Nominal)" />
          <div style={{ flex: 1, background: '#92400e' }} title="P50–P75 (Moderate risk)" />
          <div style={{ flex: 1, background: '#b45309' }} title="P75–P90 (Elevated bust risk)" />
          <div style={{ flex: 1, background: '#991b1b' }} title="P90–P100 (Highest bust risk)" />
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '9px',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span>LOW (P0)</span>
          <span>MED (P50)</span>
          <span>HIGH (P100)</span>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '9px',
            color: 'var(--text-dim)',
            fontFamily: 'var(--font-mono)',
            marginTop: '2px',
          }}
        >
          <span>{stats ? formatPct(stats.min) : '0.3%'}</span>
          <span>{stats ? formatPct(stats.p50) : '0.7%'}</span>
          <span>{stats ? formatPct(stats.max) : '1.5%'}</span>
        </div>

        {showLegendInfo && (
          <div
            style={{
              marginTop: '6px',
              paddingTop: '6px',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '9px',
              color: 'var(--text-muted)',
              lineHeight: 1.4,
            }}
          >
            Percentile scaling visualizes relative atmospheric risk across India. Calibrated model probabilities natively cluster between 0.3% and 1.5%.
          </div>
        )}
      </div>

      {/* Primary Leaflet Map Container */}
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        minZoom={4}
        maxZoom={10}
        preferCanvas={true}
        maxBounds={[
          [4.0, 60.0],
          [38.0, 105.0],
        ]}
        className="leaflet-container"
      >
        <MapPaneInitializer />

        {/* Map-Level Grid Click Handler (snaps lat/lon to nearest 0.5° grid) */}
        <MapClickHandler onSelectGrid={onSelectGrid} />

        <MapViewController
          selectedCoords={selectedCoords}
          resetTrigger={resetCount}
        />

        {/* LAYER 1: Geographic Dark Basemap */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* LAYER 2: Bilinearly Interpolated Smooth Weather Raster */}
        <SmoothBilinearForecastField
          mapData={mapData}
          stats={stats}
        />

        {/* LAYER 3: India Administrative Boundaries (Complete uncropped Ladakh & J&K) */}
        <IndiaAdministrativeLayer />

        {/* LAYER 4 & 5: State Codes, Ocean Labels & Selected Cell Crosshair Locator */}
        <MapAnnotationsLayer
          selectedGrid={selectedGrid}
          selectedCoords={selectedCoords}
        />
      </MapContainer>
    </div>
  );
};

export default LeafletConfidenceMap;

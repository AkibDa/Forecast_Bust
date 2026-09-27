import { useState, useEffect } from 'react'
import axios from 'axios'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const DEFAULT_DATE = "2026-09-26" // Using the date from API contract

// Utility to generate a gradient color based on confidence score (0 to 1)
// Red (0) -> Yellow (0.5) -> Green (1)
const getColor = (value) => {
  // Hue ranges from 0 (red) to 120 (green)
  const hue = value * 120;
  return `hsl(${hue}, 80%, 50%)`;
}

function App() {
  const [leadDay, setLeadDay] = useState(1)
  const [mapData, setMapData] = useState(null)
  const [selectedGrid, setSelectedGrid] = useState(null)
  const [timeseriesData, setTimeseriesData] = useState(null)
  const [explanationData, setExplanationData] = useState(null)

  // Fetch Confidence Map
  useEffect(() => {
    const fetchMap = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/v1/confidence-map`, {
          params: { forecast_date: DEFAULT_DATE, lead_day: leadDay }
        })
        setMapData(response.data)
      } catch (error) {
        console.error("Failed to fetch map data", error)
      }
    }
    fetchMap()
  }, [leadDay])

  // Fetch Grid Details
  useEffect(() => {
    if (!selectedGrid) {
      setTimeseriesData(null)
      setExplanationData(null)
      return
    }

    const fetchDetails = async () => {
      try {
        const [tsResponse, expResponse] = await Promise.all([
          axios.get(`${API_BASE_URL}/api/v1/grid/${selectedGrid}/timeseries`, {
            params: { forecast_date: DEFAULT_DATE }
          }),
          axios.get(`${API_BASE_URL}/api/v1/grid/${selectedGrid}/explanation`, {
            params: { forecast_date: DEFAULT_DATE, lead_day: leadDay }
          })
        ])
        setTimeseriesData(tsResponse.data)
        setExplanationData(expResponse.data)
      } catch (error) {
        console.error("Failed to fetch grid details", error)
      }
    }
    fetchDetails()
  }, [selectedGrid, leadDay])

  return (
    <div className="dashboard">
      <header className="header">
        <h1>Forecast Bust Detection</h1>
        <div className="slider-container">
          <span className="slider-label">LEAD DAY</span>
          <input 
            type="range" 
            min="1" 
            max="10" 
            value={leadDay} 
            onChange={(e) => setLeadDay(parseInt(e.target.value))}
          />
          <span className="slider-value">{leadDay}</span>
        </div>
      </header>

      <div className="main-content">
        <div className="map-panel">
          <MapContainer center={[23.0, 85.5]} zoom={5} scrollWheelZoom={true} className="map">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {mapData?.features?.map((feature, idx) => {
              const { grid_id, confidence_score } = feature.properties
              const [lng, lat] = feature.geometry.coordinates
              const color = getColor(confidence_score)
              
              return (
                <CircleMarker 
                  key={idx}
                  center={[lat, lng]} 
                  radius={7}
                  pathOptions={{ 
                    color: color, 
                    fillColor: color, 
                    fillOpacity: 0.8,
                    weight: 1
                  }}
                  eventHandlers={{
                    click: () => setSelectedGrid(grid_id)
                  }}
                >
                  <Popup>
                    <strong>Grid:</strong> {grid_id} <br/>
                    <strong>Confidence:</strong> {(confidence_score * 100).toFixed(1)}%
                  </Popup>
                </CircleMarker>
              )
            })}
          </MapContainer>
        </div>

        {selectedGrid && (
          <div className="side-panel">
            <h2>Grid: {selectedGrid}</h2>
            
            {timeseriesData ? (
              <div className="card">
                <h3>Confidence Trend</h3>
                <div className="trend-list">
                  {timeseriesData.lead_times.map(lt => (
                    <div key={lt.lead_day} className="trend-item">
                      <span className="trend-day">Day {lt.lead_day}</span>
                      <span className="trend-score" style={{ color: getColor(lt.confidence_score) }}>
                        {(lt.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : <p className="loading">Loading timeseries...</p>}

            {explanationData ? (
              <div className="card">
                <h3>Explanation (Day {leadDay})</h3>
                
                <h4>Top Drivers</h4>
                <div className="driver-list">
                  {explanationData.top_drivers.map((drv, i) => (
                    <div key={i} className={`driver-item ${drv.direction}`}>
                      <span className="driver-feat">{drv.feature}</span>
                      <span className="driver-val">{drv.contribution > 0 ? '+' : ''}{drv.contribution.toFixed(2)}</span>
                    </div>
                  ))}
                </div>

                <h4>Historical Analogs</h4>
                <div className="analog-list">
                  {explanationData.analogs.map((ana, i) => (
                    <div key={i} className="analog-item">
                      <div className="analog-header">
                        <span className="analog-name">{ana.event_name}</span>
                        <span className="analog-date">{ana.case_date}</span>
                      </div>
                      <div className="analog-score">Similarity: {(ana.similarity_score * 100).toFixed(1)}%</div>
                      <div className="analog-desc">{ana.historical_error_summary}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : <p className="loading">Loading explanation...</p>}
          </div>
        )}
      </div>
    </div>
  )
}

export default App

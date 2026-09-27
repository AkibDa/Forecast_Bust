import { useState, useEffect } from 'react'
import axios from 'axios'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const DEFAULT_DATE = "2026-09-26" // Using the date from API contract

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

  // Get color based on confidence (0 to 1) -> green for high, red for low
  const getColor = (confidence) => {
    if (confidence > 0.8) return 'green';
    if (confidence > 0.5) return 'orange';
    return 'red';
  }

  return (
    <div className="dashboard">
      <header className="header">
        <h1>Forecast Bust Detection</h1>
        <div className="slider-container">
          <label>Lead Day: {leadDay}</label>
          <input 
            type="range" 
            min="1" 
            max="10" 
            value={leadDay} 
            onChange={(e) => setLeadDay(parseInt(e.target.value))}
          />
        </div>
      </header>

      <div className="main-content">
        <div className="map-panel">
          <MapContainer center={[22.5, 88.25]} zoom={7} scrollWheelZoom={true} className="map">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {mapData?.features?.map((feature, idx) => {
              const { grid_id, confidence_score } = feature.properties
              const [lng, lat] = feature.geometry.coordinates
              return (
                <CircleMarker 
                  key={idx}
                  center={[lat, lng]} 
                  radius={8}
                  pathOptions={{ 
                    color: getColor(confidence_score), 
                    fillColor: getColor(confidence_score), 
                    fillOpacity: 0.6 
                  }}
                  eventHandlers={{
                    click: () => setSelectedGrid(grid_id)
                  }}
                >
                  <Popup>
                    Grid: {grid_id} <br/>
                    Confidence: {confidence_score}
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
                <h3>Trend (Days 1-10)</h3>
                <ul>
                  {timeseriesData.lead_times.map(lt => (
                    <li key={lt.lead_day}>
                      Day {lt.lead_day}: {lt.confidence_score}
                    </li>
                  ))}
                </ul>
              </div>
            ) : <p>Loading timeseries...</p>}

            {explanationData ? (
              <div className="card">
                <h3>Explanation (Day {leadDay})</h3>
                <h4>Top Drivers</h4>
                <ul>
                  {explanationData.top_drivers.map((drv, i) => (
                    <li key={i}>{drv.feature}: {drv.contribution} ({drv.direction})</li>
                  ))}
                </ul>
                <h4>Analogs</h4>
                <ul>
                  {explanationData.analogs.map((ana, i) => (
                    <li key={i}>
                      {ana.event_name} ({ana.case_date})<br/>
                      <small>Similarity: {ana.similarity_score}</small><br/>
                      <small>{ana.historical_error_summary}</small>
                    </li>
                  ))}
                </ul>
              </div>
            ) : <p>Loading explanation...</p>}
          </div>
        )}
      </div>
    </div>
  )
}

export default App

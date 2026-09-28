import React from 'react';
import { Database, Clock, Cpu, MapPin } from 'lucide-react';

export const SystemStatusBar = ({ health, selectedGrid, activeSource = 'live' }) => {
  const formatTime = (isoString) => {
    if (!isoString) return 'NEVER';
    try {
      const dt = new Date(isoString);
      return dt.toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
    } catch {
      return isoString;
    }
  };

  const domain = health?.grid_domain;
  const domainText = domain
    ? `${domain.lat_min}°-${domain.lat_max}°N, ${domain.lon_min}°-${domain.lon_max}°E (${domain.shape || '61x71'})`
    : '5°-35°N, 65°-100°E (0.5°)';

  return (
    <div className="system-status-bar flex flex-wrap items-center justify-between gap-3 px-4 py-1.5 bg-slate-950/80 border-b border-slate-800/80 text-[11px] font-mono text-slate-400">
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5 text-slate-300">
          <Cpu size={13} className="text-cyan-400" />
          <span>MODEL:</span>
          <span className="text-cyan-300 font-semibold">{health?.model_version ? health.model_version.toUpperCase() : 'V1'}</span>
          <span className="text-slate-600">|</span>
          <span className={health?.model_loaded ? 'text-emerald-400' : 'text-rose-400'}>
            {health?.model_loaded ? 'RESIDENT' : 'OFFLINE'}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <Database size={13} className="text-indigo-400" />
          <span>SOURCE:</span>
          <span className="text-indigo-300 font-medium uppercase">{activeSource}</span>
        </div>

        <div className="flex items-center gap-1.5 hidden sm:flex">
          <Clock size={13} className="text-slate-500" />
          <span>LAST CYCLE:</span>
          <span className="text-slate-300">{formatTime(health?.last_success_time)}</span>
        </div>
      </div>

      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5 hidden md:flex">
          <MapPin size={13} className="text-amber-400" />
          <span>DOMAIN:</span>
          <span className="text-slate-300">{domainText}</span>
        </div>

        {selectedGrid ? (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
            <span>GRID: {selectedGrid}</span>
          </div>
        ) : (
          <div className="text-slate-500 italic hidden lg:inline">
            No cell pinned
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemStatusBar;

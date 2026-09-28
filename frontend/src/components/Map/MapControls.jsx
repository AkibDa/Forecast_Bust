import React from 'react';
import { Target, Maximize2 } from 'lucide-react';

export const MapControls = ({ onResetView, onCenterSelected, hasSelectedGrid }) => {
  return (
    <div className="map-controls flex flex-col gap-1.5 select-none">
      <button
        onClick={onResetView}
        className="w-8 h-8 rounded bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-700/80 flex items-center justify-center shadow-lg transition-all cursor-pointer"
        title="Reset map view to India Subcontinent Domain"
      >
        <Maximize2 size={15} />
      </button>

      {hasSelectedGrid && (
        <button
          onClick={onCenterSelected}
          className="w-8 h-8 rounded bg-cyan-950/90 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/50 flex items-center justify-center shadow-lg transition-all cursor-pointer animate-pulse"
          title="Center on selected forecast cell"
        >
          <Target size={15} />
        </button>
      )}
    </div>
  );
};

export default MapControls;

import React from 'react';

export const LoadingSkeleton = ({ lines = 3, height = '1rem', className = '' }) => {
  return (
    <div className={`space-y-2 animate-pulse ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton-bar"
          style={{
            height,
            width: i === lines - 1 && lines > 1 ? '70%' : '100%',
          }}
        />
      ))}
    </div>
  );
};

export const CardSkeleton = ({ className = '' }) => {
  return (
    <div className={`panel-card animate-pulse ${className}`}>
      <div className="flex justify-between items-center mb-3">
        <div className="skeleton-bar" style={{ height: '14px', width: '40%' }} />
        <div className="skeleton-bar" style={{ height: '12px', width: '20%' }} />
      </div>
      <div className="space-y-2">
        <div className="skeleton-bar" style={{ height: '24px', width: '60%' }} />
        <div className="skeleton-bar" style={{ height: '12px', width: '90%' }} />
        <div className="skeleton-bar" style={{ height: '12px', width: '75%' }} />
      </div>
    </div>
  );
};

export default LoadingSkeleton;

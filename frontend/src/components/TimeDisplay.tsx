/**
 * Client-side only time display to avoid hydration errors
 */

'use client';

import { useEffect, useState } from 'react';

interface TimeDisplayProps {
  timestamp: Date;
  className?: string;
}

export default function TimeDisplay({ timestamp, className = '' }: TimeDisplayProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <span className={className}>&nbsp;</span>;
  }

  // Handle undefined or invalid timestamp
  if (!timestamp) {
    return <span className={className}>&nbsp;</span>;
  }

  // Convert string to Date if needed
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);

  // Check if date is valid
  if (isNaN(date.getTime())) {
    return <span className={className}>&nbsp;</span>;
  }

  return (
    <span className={className}>
      {date.toLocaleTimeString()}
    </span>
  );
}


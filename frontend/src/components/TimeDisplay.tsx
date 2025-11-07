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

  return (
    <span className={className}>
      {timestamp.toLocaleTimeString()}
    </span>
  );
}


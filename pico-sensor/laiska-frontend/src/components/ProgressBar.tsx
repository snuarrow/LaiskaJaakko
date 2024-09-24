import { useState, useEffect } from 'react';

// Define the prop types
interface ProgressBarProps {
  duration: number; // duration is in seconds
}

function reloadWrapper() {
    window.location.reload()
}

export default function ProgressBar({ duration: duration }: ProgressBarProps) {
  const [progress, setProgress] = useState<number>(0);

  useEffect(() => {
    if (progress < 100) {
      const interval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 100 / duration, 100));
      }, 1000); // update every second

      return () => clearInterval(interval);
    }
  }, [progress, duration]);

  

  if (progress == 100) {
    setTimeout(reloadWrapper, 1000);
  }

  return (
    <div className="progress-bar-container">
      <div
        className="progress-bar"
        style={{ width: `${progress}%` }}
      >
        {Math.floor(progress)}%
      </div>
    </div>
  );
};

import { useState, useEffect } from 'react';

export function useVideoPlayer({ durations }: { durations: Record<string, number> }) {
  const [currentScene, setCurrentScene] = useState(0);
  const sceneKeys = Object.keys(durations);

  useEffect(() => {
    let timeout: NodeJS.Timeout;
    
    if (typeof window !== 'undefined' && (window as any).startRecording && currentScene === 0) {
      (window as any).startRecording();
    }

    const playScene = (index: number) => {
      const key = sceneKeys[index];
      const duration = durations[key];
      
      timeout = setTimeout(() => {
        if (index === sceneKeys.length - 1) {
          if (typeof window !== 'undefined' && (window as any).stopRecording) {
            (window as any).stopRecording();
          }
          setCurrentScene(0); // loop
        } else {
          setCurrentScene(index + 1);
        }
      }, duration);
    };

    playScene(currentScene);

    return () => clearTimeout(timeout);
  }, [currentScene, durations, sceneKeys]);

  return { currentScene };
}
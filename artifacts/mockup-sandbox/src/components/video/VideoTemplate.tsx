import { motion, AnimatePresence } from 'framer-motion';
import { useVideoPlayer } from '../../lib/video/hooks';
import { Scene1 } from './video_scenes/Scene1';
import { Scene2 } from './video_scenes/Scene2';
import { Scene3 } from './video_scenes/Scene3';
import { Scene4 } from './video_scenes/Scene4';
import { Scene5 } from './video_scenes/Scene5';

const SCENE_DURATIONS = { open: 3500, build1: 5000, build2: 6000, build3: 5000, close: 5000 };

export default function VideoTemplate() {
  const { currentScene } = useVideoPlayer({ durations: SCENE_DURATIONS });

  return (
    <div className="relative w-full h-full overflow-hidden bg-deep-plum text-cream">
      {/* Persistent Background layer */}
      <div className="absolute inset-0 z-0">
        <motion.div 
          className="absolute w-[800px] h-[800px] rounded-full opacity-20 blur-[100px]"
          style={{ background: 'radial-gradient(circle, #6B3A6B, transparent)' }}
          animate={{ 
            x: ['-20%', '80%', '10%'], 
            y: ['10%', '60%', '-20%'], 
            scale: [1, 1.4, 0.8] 
          }}
          transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut' }} 
        />
        <motion.div 
          className="absolute w-[600px] h-[600px] rounded-full opacity-10 blur-[80px] right-0 bottom-0"
          style={{ background: 'radial-gradient(circle, #C9A84C, transparent)' }}
          animate={{ 
            x: ['10%', '-60%', '20%'], 
            y: ['-10%', '-80%', '0%'] 
          }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }} 
        />
      </div>

      {/* Persistent Gold Line Motif */}
      <motion.div
        className="absolute w-[2px] bg-gold z-10 opacity-60"
        animate={{
          height: ['0%', '100%', '30%', '80%', '0%'][currentScene],
          left: ['10%', '10%', '90%', '50%', '50%'][currentScene],
          top: ['0%', '0%', '35%', '10%', '50%'][currentScene],
        }}
        transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
      />

      <AnimatePresence mode="popLayout">
        {currentScene === 0 && <Scene1 key="open" />}
        {currentScene === 1 && <Scene2 key="build1" />}
        {currentScene === 2 && <Scene3 key="build2" />}
        {currentScene === 3 && <Scene4 key="build3" />}
        {currentScene === 4 && <Scene5 key="close" />}
      </AnimatePresence>
    </div>
  );
}

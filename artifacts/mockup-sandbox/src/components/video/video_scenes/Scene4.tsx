import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export function Scene4() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 400),
      setTimeout(() => setPhase(2), 4000),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex items-center justify-center p-12 z-20 text-center"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, filter: 'blur(20px)', scale: 1.2 }}
      transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
    >
      <motion.h2 
        className="text-5xl md:text-6xl font-display font-medium leading-tight"
        initial={{ y: 20, opacity: 0 }}
        animate={phase >= 1 ? { y: 0, opacity: 1 } : { y: 20, opacity: 0 }}
        transition={{ duration: 1, ease: "easeOut" }}
      >
        If your loved one has <br/>
        <span className="text-white font-bold">Medicare Part A</span> <br/>
        and a physician's prognosis of <br/>
        <span className="text-gold relative inline-block mt-4 mb-4">
          six months or less
          <motion.div 
            className="absolute -bottom-2 left-0 h-1 bg-gold w-full opacity-60"
            initial={{ scaleX: 0 }}
            animate={phase >= 1 ? { scaleX: 1 } : { scaleX: 0 }}
            transition={{ duration: 1, delay: 1, ease: "easeOut" }}
            style={{ originX: 0.5 }}
          />
        </span>
        <br/>
        — they are likely eligible.
      </motion.h2>
    </motion.div>
  );
}

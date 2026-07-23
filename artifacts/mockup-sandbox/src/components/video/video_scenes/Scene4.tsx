import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export function Scene4() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 400),
      setTimeout(() => setPhase(2), 3500),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div
      className="absolute inset-0 overflow-hidden z-20"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.8 }}
    >
      <motion.img
        src="/images/holistic-medicine.jpg"
        className="absolute inset-0 w-full h-full object-cover object-top"
        initial={{ scale: 1.1, x: '-3%' }}
        animate={{ scale: 1.0, x: '0%' }}
        transition={{ duration: 6, ease: 'linear' }}
      />
      <div style={{ backgroundColor: "rgba(59,31,58,0.82)" }} className="absolute inset-0" />

      <div className="relative z-10 flex items-center justify-center h-full p-12 text-center">
        <motion.h2
          className="text-5xl font-display font-medium leading-tight text-cream"
          initial={{ y: 20, opacity: 0 }}
          animate={phase >= 1 ? { y: 0, opacity: 1 } : { y: 20, opacity: 0 }}
          transition={{ duration: 1, ease: 'easeOut' }}
        >
          If your loved one has{' '}
          <span className="text-white font-bold">Medicare Part A</span>{' '}
          and a physician's prognosis of{' '}
          <span className="text-gold relative inline-block mt-3 mb-3">
            six months or less
            <motion.div
              className="absolute -bottom-2 left-0 h-1 bg-gold w-full opacity-70"
              initial={{ scaleX: 0 }}
              animate={phase >= 1 ? { scaleX: 1 } : { scaleX: 0 }}
              transition={{ duration: 1, delay: 1, ease: 'easeOut' }}
              style={{ originX: 0.5 }}
            />
          </span>
          {' '}— they are likely eligible.
        </motion.h2>
      </div>
    </motion.div>
  );
}

import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export function Scene1() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 300),
      setTimeout(() => setPhase(2), 2500),
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
        src="/images/medicare-hospice-benefit.jpg"
        className="absolute inset-0 w-full h-full object-cover object-center"
        initial={{ scale: 1.0 }}
        animate={{ scale: 1.1 }}
        transition={{ duration: 5, ease: 'linear' }}
      />
      <div style={{ backgroundColor: "rgba(59,31,58,0.82)" }} className="absolute inset-0" />

      <div className="relative z-10 flex items-center justify-center h-full p-12">
        <motion.h1
          className="text-6xl font-display font-medium text-center leading-tight tracking-tight text-cream"
          initial={{ y: 30, opacity: 0 }}
          animate={phase >= 1 ? { y: 0, opacity: 1 } : { y: 30, opacity: 0 }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
        >
          Did you know hospice care costs families{' '}
          <motion.span
            className="text-gold relative inline-block mt-4"
            animate={{ scale: [1, 1.04, 1] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          >
            nothing?
            <motion.div
              className="absolute -bottom-2 left-0 h-1 bg-gold w-full"
              initial={{ scaleX: 0 }}
              animate={phase >= 1 ? { scaleX: 1 } : { scaleX: 0 }}
              transition={{ duration: 0.8, delay: 0.8, ease: 'easeOut' }}
              style={{ originX: 0 }}
            />
          </motion.span>
        </motion.h1>
      </div>
    </motion.div>
  );
}

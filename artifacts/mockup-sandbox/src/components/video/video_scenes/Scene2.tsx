import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export function Scene2() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 200),
      setTimeout(() => setPhase(2), 1500),
      setTimeout(() => setPhase(3), 2200),
      setTimeout(() => setPhase(4), 2900),
      setTimeout(() => setPhase(5), 4200),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col justify-center p-12 z-20"
      initial={{ opacity: 0, x: 100 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, scale: 1.1, filter: 'blur(10px)' }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <motion.h2 
        className="text-5xl md:text-6xl font-display font-medium leading-tight mb-16"
      >
        Medicare <span className="text-gold">Part A</span> covers the hospice benefit completely.
      </motion.h2>

      <div className="space-y-6 font-body text-2xl md:text-3xl text-cream/80">
        <motion.p
          initial={{ opacity: 0, x: -20 }}
          animate={phase >= 2 ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          No deductible.
        </motion.p>
        <motion.p
          initial={{ opacity: 0, x: -20 }}
          animate={phase >= 3 ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          No copay.
        </motion.p>
        <motion.p
          className="text-white font-medium"
          initial={{ opacity: 0, x: -20 }}
          animate={phase >= 4 ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          No surprise bill.
        </motion.p>
      </div>
    </motion.div>
  );
}

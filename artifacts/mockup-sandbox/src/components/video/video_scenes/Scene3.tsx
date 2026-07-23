import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export function Scene3() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 300),
      setTimeout(() => setPhase(2), 2000),
      setTimeout(() => setPhase(3), 5000),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  const items = [
    "nursing visits", 
    "aide support", 
    "medications", 
    "medical equipment", 
    "chaplaincy", 
    "social work"
  ];

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col justify-center p-12 z-20"
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <p className="text-3xl font-body text-cream/70 mb-8 uppercase tracking-widest">
        That includes:
      </p>
      
      <div className="flex flex-wrap gap-4 mb-16">
        {items.map((item, i) => (
          <motion.div
            key={item}
            className="border border-gold/40 rounded-full px-6 py-3 text-2xl font-display"
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={phase >= 1 ? { opacity: 1, scale: 1, y: 0 } : { opacity: 0, scale: 0.8, y: 20 }}
            transition={{ duration: 0.5, delay: i * 0.15, type: 'spring' }}
          >
            {item}
          </motion.div>
        ))}
      </div>

      <motion.div
        className="bg-plum/30 p-8 rounded-2xl border-l-4 border-gold"
        initial={{ opacity: 0, x: -30 }}
        animate={phase >= 2 ? { opacity: 1, x: 0 } : { opacity: 0, x: -30 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <p className="text-3xl font-body text-cream/90 italic">
          "All related to the terminal diagnosis."
        </p>
      </motion.div>
    </motion.div>
  );
}

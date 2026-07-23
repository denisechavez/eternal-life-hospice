import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export function Scene3() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 300),
      setTimeout(() => setPhase(2), 2200),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  const items = [
    'nursing visits',
    'aide support',
    'medications',
    'medical equipment',
    'chaplaincy',
    'social work',
  ];

  return (
    <motion.div
      className="absolute inset-0 overflow-hidden z-20"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.7 }}
    >
      <motion.img
        src="/images/comfort-therapies.jpg"
        className="absolute inset-0 w-full h-full object-cover object-center"
        initial={{ scale: 1.0, y: '0%' }}
        animate={{ scale: 1.08, y: '-3%' }}
        transition={{ duration: 7, ease: 'linear' }}
      />
      <div style={{ backgroundColor: "rgba(59,31,58,0.82)" }} className="absolute inset-0" />

      <div className="relative z-10 flex flex-col justify-center h-full p-12">
        <motion.p
          className="text-2xl font-body text-cream/70 mb-6 uppercase tracking-widest"
          initial={{ opacity: 0 }}
          animate={phase >= 1 ? { opacity: 1 } : { opacity: 0 }}
          transition={{ duration: 0.6 }}
        >
          That includes:
        </motion.p>

        <div className="flex flex-wrap gap-3 mb-10">
          {items.map((item, i) => (
            <motion.div
              key={item}
              className="border border-gold/50 rounded-full px-5 py-2.5 text-xl font-display text-cream"
              initial={{ opacity: 0, scale: 0.8, y: 16 }}
              animate={phase >= 1 ? { opacity: 1, scale: 1, y: 0 } : { opacity: 0, scale: 0.8, y: 16 }}
              transition={{ duration: 0.45, delay: i * 0.12, type: 'spring', damping: 18 }}
            >
              {item}
            </motion.div>
          ))}
        </div>

        <motion.div
          className="bg-plum/30 p-7 rounded-2xl border-l-4 border-gold"
          initial={{ opacity: 0, x: -30 }}
          animate={phase >= 2 ? { opacity: 1, x: 0 } : { opacity: 0, x: -30 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <p className="text-2xl font-body text-cream/90 italic">
            "All related to the terminal diagnosis."
          </p>
        </motion.div>
      </div>
    </motion.div>
  );
}

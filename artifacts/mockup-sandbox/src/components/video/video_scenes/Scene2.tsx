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
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div
      className="absolute inset-0 overflow-hidden z-20"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.7 }}
    >
      <motion.img
        src="/images/first-48-hours.jpg"
        className="absolute inset-0 w-full h-full object-cover object-center"
        initial={{ scale: 1.08, x: '4%' }}
        animate={{ scale: 1.0, x: '0%' }}
        transition={{ duration: 6, ease: 'linear' }}
      />
      <div style={{ backgroundColor: "rgba(59,31,58,0.82)" }} className="absolute inset-0" />

      <div className="relative z-10 flex flex-col justify-center h-full p-12">
        <motion.h2
          className="text-5xl font-display font-medium leading-tight mb-10 text-cream"
          initial={{ x: 60, opacity: 0 }}
          animate={phase >= 1 ? { x: 0, opacity: 1 } : { x: 60, opacity: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          Medicare{' '}
          <span className="text-gold">Part A</span>{' '}
          covers the hospice benefit completely.
        </motion.h2>

        <div className="space-y-5 font-body text-3xl text-cream/85">
          {['No deductible.', 'No copay.', 'No surprise bill.'].map((line, i) => (
            <motion.p
              key={line}
              className={i === 2 ? 'text-white font-semibold' : ''}
              initial={{ opacity: 0, x: -20 }}
              animate={phase >= i + 2 ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            >
              {line}
            </motion.p>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

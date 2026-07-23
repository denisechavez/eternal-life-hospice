import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

const logoImg = '/images/logo.png';

export function Scene5() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1500),
      setTimeout(() => setPhase(3), 2500),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div
      className="absolute inset-0 overflow-hidden z-20"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 1 }}
    >
      <motion.img
        src="/images/aleksandra-dubina-founder.jpg"
        className="absolute inset-0 w-full h-full object-cover object-top"
        initial={{ scale: 1.05 }}
        animate={{ scale: 1.12 }}
        transition={{ duration: 6, ease: 'linear' }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-deep-plum via-deep-plum/75 to-deep-plum/50" />

      <div className="relative z-10 flex flex-col items-center justify-end h-full p-12 pb-16 text-center">
        <motion.img
          src={logoImg}
          alt="Eternal Life Hospice"
          className="w-64 object-contain mb-10"
          initial={{ opacity: 0, y: -16 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: -16 }}
          transition={{ duration: 0.9, type: 'spring', damping: 22 }}
        />

        <motion.p
          className="text-3xl font-display font-medium text-white mb-8 leading-snug"
          initial={{ opacity: 0, y: 14 }}
          animate={phase >= 2 ? { opacity: 1, y: 0 } : { opacity: 0, y: 14 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          We verify eligibility for every family.
        </motion.p>

        <motion.div
          className="bg-gold/15 px-8 py-4 rounded-full border border-gold/40"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={phase >= 3 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.8, type: 'spring', damping: 20 }}
        >
          <p className="text-3xl font-body font-bold text-gold tracking-widest">
            805.953.7273
          </p>
        </motion.div>
      </div>
    </motion.div>
  );
}

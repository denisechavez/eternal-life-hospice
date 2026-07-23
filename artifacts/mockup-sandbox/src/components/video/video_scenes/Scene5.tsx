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
      className="absolute inset-0 flex flex-col items-center justify-center p-12 z-20 text-center bg-deep-plum"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: 50 }}
      transition={{ duration: 1 }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.8, y: -20 }}
        animate={phase >= 1 ? { opacity: 1, scale: 1, y: 0 } : { opacity: 0, scale: 0.8, y: -20 }}
        transition={{ duration: 1, type: "spring", damping: 20 }}
        className="mb-16"
      >
        <img 
          src={logoImg} 
          alt="Eternal Life Hospice" 
          className="w-80 object-contain mx-auto"
        />
      </motion.div>

      <motion.h3
        className="text-4xl md:text-5xl font-display font-medium text-white mb-12"
        initial={{ opacity: 0, y: 20 }}
        animate={phase >= 2 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        We verify eligibility for every family.
      </motion.h3>

      <motion.div
        className="bg-gold/10 px-8 py-4 rounded-full border border-gold/30"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={phase >= 3 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.8, type: "spring", damping: 20 }}
      >
        <p className="text-4xl md:text-5xl font-body font-bold text-gold tracking-widest">
          805.953.7273
        </p>
      </motion.div>
    </motion.div>
  );
}

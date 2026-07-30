import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Hammer,
  Eye,
  Flame,
  MapPin,
  Clock,
  ArrowUpRight,
  MoveHorizontal,
} from 'lucide-react';

/* ---------------------------------- DATA ---------------------------------- */

const memes = [
  {
    tag: 'MEME_001 / EXPECTATION.GAP',
    top: 'WHAT THE CLIENT SAW:',
    topSub: 'a leaking warehouse with pigeon problems',
    img: 'https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=900&h=700&fit=crop',
    bottom: 'WHAT WE SAW:',
    bottomSub: 'a cathedral waiting for permission',
  },
  {
    tag: 'MEME_002 / NOBODY.ASKED',
    top: 'NOBODY:',
    topSub: 'absolutely no one:',
    img: 'https://images.unsplash.com/photo-1486718448742-163732cd1544?w=900&h=700&fit=crop',
    bottom: 'US AT 2:47 AM:',
    bottomSub: '"what if the staircase… floated"',
  },
  {
    tag: 'MEME_003 / POV.FORMAT',
    top: 'POV:',
    topSub: 'you said "just paint it white" in our studio',
    img: 'https://images.unsplash.com/photo-1517502884422-41eaead166d4?w=900&h=700&fit=crop',
    bottom: 'THE ROOM, 90 DAYS LATER:',
    bottomSub: 'unrecognizable. so are you.',
  },
  {
    tag: 'MEME_004 / DAY.1.VS.DAY.90',
    top: 'DAY 1:',
    topSub: 'concrete dust, exposed rebar, doubt',
    img: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=900&h=700&fit=crop',
    bottom: 'DAY 90:',
    bottomSub: 'guests refuse to leave the kitchen',
  },
];

const roles = [
  {
    code: 'ROLE / 01',
    title: 'SPATIAL CONJURER',
    plain: '(Senior Interior Architect)',
    desc: 'You see load-bearing walls as suggestions. 6+ yrs turning industrial shells into places people whisper about.',
    salary: '$110–135K',
    type: 'Full-time',
    loc: 'Detroit Foundry District',
    accent: '#e8632c',
  },
  {
    code: 'ROLE / 02',
    title: 'LIGHTING ALCHEMIST',
    plain: '(Lighting Designer)',
    desc: 'Sodium glow, raw filament, the exact hour shadows go soft. You make 4,000 sq ft of concrete feel like a held breath.',
    salary: '$85–105K',
    type: 'Full-time',
    loc: 'Detroit Foundry District',
    accent: '#d8c49a',
  },
  {
    code: 'ROLE / 03',
    title: 'MATERIALS WHISPERER',
    plain: '(FF&E Specialist)',
    desc: 'Blackened steel, end-grain oak, leather that improves with neglect. You source the things rooms remember.',
    salary: '$78–95K',
    type: 'Full-time',
    loc: 'Hybrid / 3 days on-site',
    accent: '#9aa7ad',
  },
  {
    code: 'ROLE / 04',
    title: 'APPRENTICE OF THE UNSEEN',
    plain: '(Junior Designer)',
    desc: 'Zero ego, dangerous curiosity. You will sweep floors, build models, and watch buildings change their minds.',
    salary: '$58–68K',
    type: 'Full-time',
    loc: 'Detroit Foundry District',
    accent: '#e8632c',
  },
  {
    code: 'ROLE / 05',
    title: 'KEEPER OF THE LEDGER',
    plain: '(Studio Operations)',
    desc: 'Magic has invoices. You keep the chaos billable, the timelines honest, and the conjurers fed.',
    salary: '$72–88K',
    type: 'Full-time',
    loc: 'On-site',
    accent: '#d8c49a',
  },
];

const ritual = [
  {
    n: '01',
    icon: Hammer,
    title: 'EXCAVATE',
    body: 'Strip it back. Plaster off, drywall down, decades of bad decisions hauled to the dumpster. We find what the building was hiding.',
    img: 'https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&h=560&fit=crop',
  },
  {
    n: '02',
    icon: Flame,
    title: 'TRANSMUTE',
    body: 'Steel is welded at midnight. Concrete is ground until it shines like wet stone. The ordinary becomes the inevitable.',
    img: 'https://images.unsplash.com/photo-1565992441121-4367c2967103?w=800&h=560&fit=crop',
  },
  {
    n: '03',
    icon: Eye,
    title: 'REVEAL',
    body: 'The client walks in. There is always a silence first — about four seconds. That silence is the entire job.',
    img: 'https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=800&h=560&fit=crop',
  },
];

/* ------------------------------ SUB-COMPONENTS ----------------------------- */

const fadeUp = {
  hidden: { opacity: 0, y: 48 },
  show: { opacity: 1, y: 0, transition: { duration: 0.85, ease: [0.22, 1, 0.36, 1] } },
};

function SectionHeader({ kicker, title, sub }) {
  return (
    <div className="px-6 md:px-14 mb-10 flex flex-col md:flex-row md:items-end md:justify-between gap-6">
      <div>
        <div className="font-mono text-[11px] tracking-[0.35em] text-[#e8632c] mb-4 flex items-center gap-3">
          <span className="block w-10 h-px bg-[#e8632c]" />
          {kicker}
        </div>
        <h2 className="anton text-5xl md:text-7xl leading-[0.92] text-[#e7e2d8]">{title}</h2>
      </div>
      {sub && (
        <p className="font-mono text-xs text-[#8a8378] max-w-xs leading-relaxed border-l-2 border-[#3a352e] pl-4">
          {sub}
        </p>
      )}
    </div>
  );
}

function HScroll({ children, scrollerRef }) {
  return (
    <div className="relative">
      <div
        ref={scrollerRef}
        className="hscroll flex gap-5 overflow-x-auto px-6 md:px-14 pb-8 snap-x snap-mandatory"
      >
        {children}
        <div className="shrink-0 w-2" />
      </div>
      <div className="px-6 md:px-14 flex items-center gap-3 text-[#6b655b] font-mono text-[10px] tracking-[0.3em]">
        <MoveHorizontal size={14} className="text-[#e8632c]" />
        DRAG SIDEWAYS — THE GOOD STUFF KEEPS GOING
      </div>
    </div>
  );
}

/* ---------------------------------- APP ----------------------------------- */

export default function App() {
  const [hovered, setHovered] = useState(null);
  const memeRef = useRef(null);
  const roleRef = useRef(null);

  const nudge = (ref, dir) => {
    if (ref.current) ref.current.scrollBy({ left: dir * 420, behavior: 'smooth' });
  };

  return (
    <div className="bg-[#141210] text-[#e7e2d8] min-h-screen overflow-x-hidden antialiased relative">
      <link
        href="https://fonts.googleapis.com/css2?family=Anton&family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap"
        rel="stylesheet"
      />
      <style
        dangerouslySetInnerHTML={{
          __html: `
        body { background:#141210; }
        .anton { font-family:'Anton', sans-serif; letter-spacing: 0.01em; }
        .grotesk { font-family:'Space Grotesk', sans-serif; }
        .font-mono { font-family:'JetBrains Mono', monospace; }
        .hscroll { scrollbar-width: thin; scrollbar-color: #e8632c #26221d; }
        .hscroll::-webkit-scrollbar { height: 6px; }
        .hscroll::-webkit-scrollbar-track { background: #26221d; }
        .hscroll::-webkit-scrollbar-thumb { background: #e8632c; }
        .noise::after {
          content:''; position:fixed; inset:0; pointer-events:none; z-index:50; opacity:0.07;
          background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        }
        .concrete {
          background-color:#1c1916;
          background-image:
            radial-gradient(ellipse at 20% 10%, rgba(255,255,255,0.025), transparent 50%),
            radial-gradient(ellipse at 80% 90%, rgba(232,99,44,0.04), transparent 55%);
        }
        .rivet { width:7px; height:7px; border-radius:50%; background:#3a352e; box-shadow: inset 0 1px 1px rgba(255,255,255,0.18), 0 1px 2px rgba(0,0,0,0.6); }
        .marquee-track { display:flex; width:max-content; animation: marquee 26s linear infinite; }
        @keyframes marquee { from { transform:translateX(0); } to { transform:translateX(-50%); } }
        .stamp { transform: rotate(-4deg); }
        .hatch {
          background-image: repeating-linear-gradient(45deg, #e8632c 0, #e8632c 10px, #141210 10px, #141210 20px);
        }
        ::selection { background:#e8632c; color:#141210; }
      `,
        }}
      />
      <div className="noise grotesk">

        {/* ============================ STICKY TOP BAR ============================ */}
        <div className="sticky top-0 z-40 border-b border-[#2c2823] bg-[#141210]/92 backdrop-blur-sm">
          <div className="flex items-center justify-between px-6 md:px-14 h-14">
            <div className="flex items-center gap-3">
              <Sparkles size={16} className="text-[#e8632c]" />
              <span className="anton text-lg tracking-wide">RAW&nbsp;&amp;&nbsp;RITUAL</span>
              <span className="font-mono text-[10px] text-[#6b655b] tracking-[0.25em] hidden md:inline">
                INTERIOR STUDIO — EST. 2014 — DETROIT
              </span>
            </div>
            <button className="group flex items-center gap-2 bg-[#e8632c] text-[#141210] font-mono text-[11px] font-bold tracking-[0.2em] px-4 py-2 hover:bg-[#e7e2d8] transition-colors">
              APPLY <ArrowUpRight size={14} className="group-hover:rotate-45 transition-transform" />
            </button>
          </div>
        </div>

        {/* ================================ HERO ================================ */}
        <motion.section
          variants={fadeUp}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.25 }}
          className="concrete relative border-b border-[#2c2823]"
        >
          <div className="px-6 md:px-14 pt-16 pb-10 md:pt-24 md:pb-16 relative">
            {/* rivets */}
            <div className="absolute top-6 left-6 rivet" />
            <div className="absolute top-6 right-6 rivet" />

            <div className="font-mono text-[11px] tracking-[0.35em] text-[#9aa7ad] mb-8 flex flex-wrap items-center gap-x-6 gap-y-2">
              <span>FILE: HIRING_RITUAL_2025.PDF</span>
              <span className="text-[#e8632c]">● NOW CASTING</span>
              <span>SHARE THIS WITH THE MOST OBSESSIVE PERSON YOU KNOW</span>
            </div>

            <h1 className="anton uppercase leading-[0.86] text-[#e7e2d8] text-[17vw] md:text-[9.5rem]">
              We make<br />
              concrete<br />
              <span className="text-[#e8632c]">disappear.</span>
            </h1>

            <div className="mt-10 flex flex-col md:flex-row md:items-end gap-8">
              <p className="font-mono text-sm leading-relaxed text-[#b3aca0] max-w-md">
                Not literally. Legally we must say that. But when we're done with a
                warehouse, nobody remembers it was ever just a warehouse —{' '}
                <span className="text-[#e7e2d8]">and we need 5 more hands for the trick.</span>
              </p>
              <div className="stamp inline-flex items-center gap-2 border-2 border-[#e8632c] text-[#e8632c] font-mono text-xs font-bold tracking-[0.25em] px-5 py-3 self-start">
                5 OPEN ROLES — NO ORDINARY APPLICANTS
              </div>
            </div>
          </div>

          {/* marquee */}
          <div className="border-t border-[#2c2823] py-3 overflow-hidden bg-[#171411]">
            <div className="marquee-track font-mono text-[11px] tracking-[0.3em] text-[#6b655b]">
              {[0, 1].map((i) => (
                <span key={i} className="flex gap-10 pr-10 whitespace-nowrap">
                  <span>EXPOSED BRICK IS A LOVE LANGUAGE</span>
                  <span className="text-[#e8632c]">✦</span>
                  <span>WE'RE HIRING CONJURERS</span>
                  <span className="text-[#e8632c]">✦</span>
                  <span>STEEL, OAK, AND FOUR SECONDS OF SILENCE</span>
                  <span className="text-[#e8632c]">✦</span>
                  <span>TAG SOMEONE WHO MEASURES ROOMS BY EYE</span>
                  <span className="text-[#e8632c]">✦</span>
                </span>
              ))}
            </div>
          </div>
        </motion.section>

        {/* ============================ MEME STRIP ============================== */}
        <motion.section
          variants={fadeUp}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          className="py-20 border-b border-[#2c2823]"
        >
          <SectionHeader
            kicker="EXHIBIT A — THE MEMES"
            title={<>STEAL THESE.<br />POST THESE.</>}
            sub="Official transformation templates. Caption them, screenshot them, tag @rawandritual. The best repost gets a studio tour."
          />
          <HScroll scrollerRef={memeRef}>
            {memes.map((m, i) => (
              <article
                key={i}
                className="snap-start shrink-0 w-[320px] md:w-[400px] bg-[#1f1b17] border border-[#332e27] hover:border-[#e8632c] transition-colors duration-300 group"
              >
                <div className="px-5 py-3 border-b border-[#332e27] flex justify-between items-center">
                  <span className="font-mono text-[10px] tracking-[0.25em] text-[#6b655b]">{m.tag}</span>
                  <span className="rivet" />
                </div>
                <div className="p-5">
                  <p className="anton text-2xl leading-tight text-[#e7e2d8]">{m.top}</p>
                  <p className="font-mono text-xs text-[#8a8378] mt-1 mb-4">{m.topSub}</p>
                  <div className="overflow-hidden border border-[#332e27]">
                    <img
                      src={m.img}
                      alt=""
                      className="w-full h-52 object-cover grayscale-[40%] contrast-110 group-hover:grayscale-0 group-hover:scale-[1.03] transition-all duration-700"
                    />
                  </div>
                  <p className="anton text-2xl leading-tight text-[#e8632c] mt-4">{m.bottom}</p>
                  <p className="font-mono text-xs text-[#b3aca0] mt-1">{m.bottomSub}</p>
                </div>
                <div className="px-5 py-3 border-t border-[#332e27] font-mono text-[10px] tracking-[0.2em] text-[#6b655b] flex justify-between">
                  <span>@RAWANDRITUAL</span>
                  <span>HIRING.RAWRITUAL.STUDIO</span>
                </div>
              </article>
            ))}
            {/* CTA card at end of strip */}
            <article className="snap-start shrink-0 w-[320px] md:w-[400px] hatch p-1">
              <div className="bg-[#141210] h-full flex flex-col justify-between p-8">
                <p className="anton text-4xl leading-[0.95]">
                  IF YOU LAUGHED,<br />YOU'RE QUALIFIED.
                </p>
                <div>
                  <p className="font-mono text-xs text-[#8a8378] leading-relaxed mb-6">
                    Humor about load paths is a hiring signal. Scroll down. The roles are real.
                  </p>
                  <button className="flex items-center gap-2 font-mono text-xs font-bold tracking-[0.2em] text-[#e8632c] hover:gap-4 transition-all">
                    SEE OPEN ROLES <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            </article>
          </HScroll>
          <div className="px-6 md:px-14 mt-4 flex gap-2">
            <button onClick={() => nudge(memeRef, -1)} className="border border-[#3a352e] p-2 hover:bg-[#e8632c] hover:text-[#141210] hover:border-[#e8632c] transition-colors">
              <ArrowLeft size={16} />
            </button>
            <button onClick={() => nudge(memeRef, 1)} className="border border-[#3a352e] p-2 hover:bg-[#e8632c] hover:text-[#141210] hover:border-[#e8632c] transition-colors">
              <ArrowRight size={16} />
            </button>
          </div>
        </motion.section>

        {/* ============================ THE RITUAL ============================== */}
        <motion.section
          variants={fadeUp}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          className="py-20 border-b border-[#2c2823] concrete"
        >
          <SectionHeader
            kicker="EXHIBIT B — HOW THE TRICK WORKS"
            title="THE RITUAL"
            sub="Three acts. Every project. No shortcuts, no reveals before their time."
          />
          <HScroll>
            {ritual.map((r) => {
              const Icon = r.icon;
              return (
                <article
                  key={r.n}
                  className="snap-start shrink-0 w-[300px] md:w-[460px] border border-[#332e27] bg-[#18150f]"
                >
                  <div className="relative">
                    <img src={r.img} alt="" className="w-full h-56 object-cover grayscale-[55%] contrast-110" />
                    <span className="anton text-7xl text-[#e8632c] absolute -bottom-6 right-5 drop-shadow-[0_4px_0_#141210]">
                      {r.n}
                    </span>
                  </div>
                  <div className="p-6 pt-10">
                    <div className="flex items-center gap-3 mb-3">
                      <Icon size={18} className="text-[#d8c49a]" />
                      <h3 className="anton text-3xl">{r.title}</h3>
                    </div>
                    <p className="font-mono text-xs leading-relaxed text-[#9b948a]">{r.body}</p>
                  </div>
                </article>
              );
            })}
          </HScroll>
        </motion.section>

        {/* ============================ OPEN ROLES ============================== */}
        <motion.section
          variants={fadeUp}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.15 }}
          className="py-20 border-b border-[#2c2823]"
        >
          <SectionHeader
            kicker="EXHIBIT C — THE CASTING CALL"
            title={<>FIVE SEATS AT<br />THE STEEL TABLE</>}
            sub="Full benefits, profit share after year one, a workshop with a plasma cutter, and a studio dog named Rivet."
          />
          <HScroll scrollerRef={roleRef}>
            {roles.map((role, i) => (
              <article
                key={i}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                className="snap-start shrink-0 w-[300px] md:w-[380px] border bg-[#1c1916] flex flex-col justify-between transition-all duration-300"
                style={{
                  borderColor: hovered === i ? role.accent : '#332e27',
                  transform: hovered === i ? 'translateY(-6px)' : 'none',
                }}
              >
                <div className="p-7">
                  <div className="flex justify-between items-center mb-8">
                    <span className="font-mono text-[10px] tracking-[0.3em] text-[#6b655b]">{role.code}</span>
                    <span className="block w-3 h-3" style={{ background: role.accent }} />
                  </div>
                  <h3 className="anton text-4xl leading-[0.95]" style={{ color: hovered === i ? role.accent : '#e7e2d8' }}>
                    {role.title}
                  </h3>
                  <p className="font-mono text-[11px] text-[#8a8378] mt-2 mb-6">{role.plain}</p>
                  <p className="font-mono text-xs leading-relaxed text-[#b3aca0]">{role.desc}</p>
                </div>
                <div>
                  <div className="px-7 pb-6 flex flex-wrap gap-x-5 gap-y-2 font-mono text-[10px] tracking-[0.15em] text-[#8a8378]">
                    <span className="flex items-center gap-1.5"><Clock size={12} /> {role.type}</span>
                    <span className="flex items-center gap-1.5"><MapPin size={12} /> {role.loc}</span>
                    <span className="text-[#d8c49a]">{role.salary}</span>
                  </div>
                  <button
                    className="w-full border-t font-mono text-xs font-bold tracking-[0.25em] py-4 flex items-center justify-center gap-2 transition-colors"
                    style={{
                      borderColor: hovered === i ? role.accent : '#332e27',
                      background: hovered === i ? role.accent : 'transparent',
                      color: hovered === i ? '#141210' : '#e7e2d8',
                    }}
                  >
                    SUMMON ME <ArrowUpRight size={14} />
                  </button>
                </div>
              </article>
            ))}
          </HScroll>
          <div className="px-6 md:px-14 mt-4 flex gap-2">
            <button onClick={() => nudge(roleRef, -1)} className="border border-[#3a352e] p-2 hover:bg-[#e8632c] hover:text-[#141210] hover:border-[#e8632c] transition-colors">
              <ArrowLeft size={16} />
            </button>
            <button onClick={() => nudge(roleRef, 1)} className="border border-[#3a352e] p-2 hover:bg-[#e8632c] hover:text-[#141210] hover:border-[#e8632c] transition-colors">
              <ArrowRight size={16} />
            </button>
          </div>
        </motion.section>

        {/* ============================== FINAL CTA ============================= */}
        <motion.section
          variants={fadeUp}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
          className="concrete relative"
        >
          <div className="px-6 md:px-14 py-24 text-center">
            <p className="font-mono text-[11px] tracking-[0.35em] text-[#9aa7ad] mb-6">FINAL FRAME — SHARE BEFORE APPLYING</p>
            <h2 className="anton uppercase leading-[0.88] text-[14vw] md:text-[7.5rem]">
              Apply, or remain
              <br />
              <span className="text-[#e8632c]">ordinary.</span>
            </h2>
            <p className="font-mono text-xs text-[#8a8378] mt-8 max-w-md mx-auto leading-relaxed">
              Send a portfolio, a photo of the strangest room you've ever loved, and one
              sentence about why. No cover letters. We can't read them over the angle grinder.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <button className="group bg-[#e8632c] text-[#141210] anton text-xl tracking-wide px-10 py-4 hover:bg-[#e7e2d8] transition-colors flex items-center gap-3">
                BEGIN THE RITUAL
                <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
              </button>
              <span className="font-mono text-[10px] tracking-[0.25em] text-[#6b655b]">
                HIRING@RAWRITUAL.STUDIO — REPLIES IN 72 HRS
              </span>
            </div>
          </div>
          <footer className="border-t border-[#2c2823] px-6 md:px-14 py-5 flex flex-col md:flex-row gap-3 justify-between font-mono text-[10px] tracking-[0.25em] text-[#6b655b]">
            <span>© 2025 RAW &amp; RITUAL INTERIOR STUDIO</span>
            <span>1400 FOUNDRY ST, DETROIT MI</span>
            <span className="text-[#e8632c]">EQUAL OPPORTUNITY CONJURING</span>
          </footer>
        </motion.section>
      </div>
    </div>
  );
}
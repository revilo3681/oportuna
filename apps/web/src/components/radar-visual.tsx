import { cn, compactNumber } from "@/lib/format";

export function RadarVisual({
  openTotal,
  sources,
  closing,
  className,
}: {
  openTotal: number;
  sources: number;
  closing: number;
  className?: string;
}) {
  const blips = [
    { x: 146, y: 128, r: 3.2, tone: "#df4a1a" },
    { x: 268, y: 96, r: 2.4, tone: "#f3f0e7" },
    { x: 302, y: 196, r: 3.8, tone: "#df4a1a" },
    { x: 232, y: 268, r: 2.6, tone: "#7fb79c" },
    { x: 118, y: 246, r: 2.2, tone: "#f3f0e7" },
    { x: 196, y: 334, r: 2.8, tone: "#df4a1a" },
    { x: 318, y: 288, r: 2.2, tone: "#7fb79c" },
    { x: 164, y: 178, r: 1.8, tone: "#f3f0e7" },
  ];

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[6px] border border-ink/20 bg-ink text-paper-raised",
        className,
      )}
    >
      <div className="absolute inset-0 grain opacity-[0.18]" aria-hidden />
      <svg viewBox="0 0 400 400" className="relative block h-full w-full" role="img" aria-label="Radar esquemático de oportunidades">
        <defs>
          <radialGradient id="radar-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#df4a1a" stopOpacity="0.16" />
            <stop offset="70%" stopColor="#df4a1a" stopOpacity="0.02" />
            <stop offset="100%" stopColor="#df4a1a" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="radar-sweep-fill" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="#df4a1a" stopOpacity="0.34" />
            <stop offset="100%" stopColor="#df4a1a" stopOpacity="0" />
          </linearGradient>
        </defs>

        <rect width="400" height="400" fill="#101310" />
        <circle cx="200" cy="200" r="160" fill="url(#radar-glow)" />

        {[60, 105, 150, 195, 240].map((radius) => (
          <circle
            key={radius}
            cx="200"
            cy="200"
            r={radius}
            fill="none"
            stroke="#f3f0e7"
            strokeOpacity={radius === 240 ? 0.18 : 0.11}
            strokeWidth="1"
          />
        ))}

        <g stroke="#f3f0e7" strokeOpacity="0.1" strokeWidth="1">
          <path d="M200 5v390M5 200h390" />
          <path d="M60 60l280 280M340 60L60 340" strokeOpacity="0.05" />
        </g>

        <g className="radar-sweep">
          <path
            d="M200 200 L200 5 A195 195 0 0 1 382 95 Z"
            fill="url(#radar-sweep-fill)"
          />
          <path d="M200 200 L200 5" stroke="#df4a1a" strokeWidth="1.2" strokeOpacity="0.75" />
        </g>

        <circle cx="200" cy="200" r="3" fill="#df4a1a" />
        <circle cx="200" cy="200" r="8" fill="none" stroke="#df4a1a" strokeOpacity="0.4" />

        {blips.map((blip) => (
          <g key={`${blip.x}-${blip.y}`}>
            <circle cx={blip.x} cy={blip.y} r={blip.r + 5} fill={blip.tone} opacity="0.1" />
            <circle cx={blip.x} cy={blip.y} r={blip.r} fill={blip.tone} />
          </g>
        ))}

        <g fill="#f3f0e7" fillOpacity="0.4" fontSize="9" fontFamily="monospace" letterSpacing="2">
          <text x="196" y="20">N</text>
          <text x="380" y="204">E</text>
          <text x="196" y="390">S</text>
          <text x="12" y="204">O</text>
        </g>

        <g stroke="#f3f0e7" strokeOpacity="0.25" strokeWidth="1">
          <path d="M20 20h12M20 20v12M380 20h-12M380 20v12M20 380h12M20 380v-12M380 380h-12M380 380v-12" />
        </g>
      </svg>

      <div className="absolute left-5 top-5 flex items-center gap-2">
        <span className="size-1.5 animate-pulse rounded-full bg-signal" />
        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-paper-raised/70">
          Señal activa · cobertura global
        </span>
      </div>

      <div className="absolute bottom-0 left-0 right-0 grid grid-cols-3 divide-x divide-paper-raised/10 border-t border-paper-raised/10 bg-ink/70 backdrop-blur">
        <div className="px-4 py-4">
          <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-paper-raised/45">Abiertas</p>
          <p className="mono mt-1 text-2xl text-paper-raised">{compactNumber(openTotal)}</p>
        </div>
        <div className="px-4 py-4">
          <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-paper-raised/45">Fuentes</p>
          <p className="mono mt-1 text-2xl text-paper-raised">{compactNumber(sources)}</p>
        </div>
        <div className="px-4 py-4">
          <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-paper-raised/45">Cierran 7 d</p>
          <p className="mono mt-1 text-2xl text-signal">{compactNumber(closing)}</p>
        </div>
      </div>

      <p className="absolute bottom-[86px] right-4 font-mono text-[8px] uppercase tracking-[0.14em] text-paper-raised/30">
        Radar esquemático
      </p>
    </div>
  );
}

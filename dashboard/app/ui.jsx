// Shared small components used across pages
// Exposes: BankBadge, CategoryChip, Sparkline, StatBlock, Ring, Icon, ChartArea
const { useState, useEffect, useMemo, useRef } = React;

function Icon({ name, size = 16, stroke = 1.5, className = "" }) {
  const s = size;
  const common = {
    width: s, height: s, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: stroke, strokeLinecap: "round", strokeLinejoin: "round",
    className,
  };
  const paths = {
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    close: <><path d="M6 6l12 12M18 6L6 18"/></>,
    chevronR: <><path d="m9 6 6 6-6 6"/></>,
    chevronD: <><path d="m6 9 6 6 6-6"/></>,
    upload: <><path d="M12 3v12"/><path d="m6 9 6-6 6 6"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></>,
    download: <><path d="M12 3v12"/><path d="m6 9 6 6 6-6"/><path d="M4 21h16"/></>,
    filter: <><path d="M4 5h16l-6 8v7l-4-2v-5Z"/></>,
    sliders: <><path d="M4 7h10"/><path d="M18 7h2"/><circle cx="16" cy="7" r="2"/><path d="M4 17h4"/><path d="M12 17h8"/><circle cx="10" cy="17" r="2"/></>,
    eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></>,
    eyeOff: <><path d="m3 3 18 18"/><path d="M10.5 5.2A10 10 0 0 1 22 12s-1.2 2.4-3.8 4.4"/><path d="M6.5 6.5C3.7 8.4 2 12 2 12s3.5 7 10 7a10 10 0 0 0 4-.8"/><circle cx="12" cy="12" r="3"/></>,
    bell: <><path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8Z"/><path d="M10 20a2 2 0 0 0 4 0"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4 4M20 20l-1.6-1.6M5.6 18.4 4 20M20 4l-1.6 1.6"/></>,
    home: <><path d="M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/></>,
    list: <><path d="M4 6h16M4 12h16M4 18h16"/></>,
    pie: <><path d="M21 12A9 9 0 1 1 12 3v9Z"/><path d="M21 12a9 9 0 0 0-9-9"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    file: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6"/></>,
    check: <><path d="m5 12 5 5 9-11"/></>,
    sparkle: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></>,
    arrowUp: <><path d="M12 19V5M5 12l7-7 7 7"/></>,
    arrowDown: <><path d="M12 5v14M5 12l7 7 7-7"/></>,
    arrowRight: <><path d="M5 12h14M13 5l7 7-7 7"/></>,
  };
  return <svg {...common}>{paths[name] || null}</svg>;
}

function BankBadge({ bankId, size = 14 }) {
  const b = BANKS.find((x) => x.id === bankId) || BANKS[0];
  return (
    <span className="bank-chip">
      <span className="sq" style={{ background: b.color, width: size, height: size }}>
        {b.short.slice(0, 1)}
      </span>
      <span>{b.short}</span>
    </span>
  );
}

function CategoryChip({ catId, active, onClick }) {
  const c = getCatInfo(catId);
  if (!c) return null;
  return (
    <span className={"chip" + (active ? " active" : "")} onClick={onClick}>
      <span style={{ fontSize: 12, lineHeight: 1 }}>{c.glyph}</span>
      <span>{c.name}</span>
    </span>
  );
}

function StatBlock({ label, value, sub, accent = false, mono = true }) {
  return (
    <div className={"stat" + (accent ? " accent" : "")}>
      <div className="lab">{label}</div>
      <div className={"val" + (mono ? " tnum" : "")}>{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

/* ==========  Sparkline / Area chart ========== */
function Sparkline({ data, height = 140, privacy = false }) {
  // data: [{date, income, spend}]
  const wrapRef = useRef(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((ents) => {
      for (const e of ents) setW(e.contentRect.width);
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  const padX = 8, padY = 16;
  const maxVal = Math.max(1, ...data.map((d) => Math.max(d.income, d.spend)));
  const xAt = (i) => padX + (i * (w - padX * 2)) / Math.max(1, data.length - 1);
  const yAt = (v) => padY + (1 - v / maxVal) * (height - padY * 2);

  const linePath = (key) =>
    data.map((d, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(d[key])}`).join(" ");

  const areaPath = (key) => {
    const p = data.map((d, i) => `${i === 0 ? "M" : "L"} ${xAt(i)} ${yAt(d[key])}`).join(" ");
    return `${p} L ${xAt(data.length - 1)} ${height - padY} L ${xAt(0)} ${height - padY} Z`;
  };

  return (
    <div ref={wrapRef} className="sparkwrap" style={{ height, filter: privacy ? "blur(8px)" : "none" }}>
      <svg width={w} height={height} style={{ overflow: "visible" }}>
        <defs>
          <linearGradient id="spark-in" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="oklch(0.55 0.09 145)" stopOpacity="0.25"/>
            <stop offset="100%" stopColor="oklch(0.55 0.09 145)" stopOpacity="0"/>
          </linearGradient>
          <linearGradient id="spark-out" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="oklch(0.48 0.11 35)" stopOpacity="0.18"/>
            <stop offset="100%" stopColor="oklch(0.48 0.11 35)" stopOpacity="0"/>
          </linearGradient>
        </defs>
        {/* grid */}
        {[0.25, 0.5, 0.75].map((t, i) => (
          <line key={i} x1={padX} x2={w - padX} y1={padY + t * (height - padY * 2)} y2={padY + t * (height - padY * 2)}
            stroke="oklch(0.88 0.008 80)" strokeDasharray="2 4" />
        ))}
        <path d={areaPath("income")} fill="url(#spark-in)" />
        <path d={areaPath("spend")} fill="url(#spark-out)" />
        <path d={linePath("income")} fill="none" stroke="oklch(0.48 0.09 150)" strokeWidth="1.5" />
        <path d={linePath("spend")} fill="none" stroke="oklch(0.48 0.11 35)" strokeWidth="1.5" />
        {/* latest dots */}
        {data.length > 0 && (
          <>
            <circle cx={xAt(data.length - 1)} cy={yAt(data[data.length-1].income)} r="3" fill="oklch(0.48 0.09 150)" />
            <circle cx={xAt(data.length - 1)} cy={yAt(data[data.length-1].spend)} r="3" fill="oklch(0.48 0.11 35)" />
          </>
        )}
      </svg>
    </div>
  );
}

/* ========== Ring chart ========== */
function Ring({ segments, size = 180, thickness = 22, center }) {
  const [hovered, setHovered] = useState(null);
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = size / 2 - thickness / 2;
  const c = 2 * Math.PI * r;
  let acc = 0;
  const hovSeg = hovered != null ? segments[hovered] : null;
  const hovPct = hovSeg ? Math.round((hovSeg.value / total) * 100) : null;
  const displayCenter = hovSeg ? (
    <div>
      <div style={{ fontFamily: "Instrument Serif, serif", fontSize: 28, lineHeight: 1, color: hovSeg.color }}>
        {hovPct}%
      </div>
      <div style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-4)", marginTop: 3 }}>
        {hovSeg.cat?.name || hovSeg.id}
      </div>
    </div>
  ) : center;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ overflow: "visible" }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="oklch(0.92 0.01 80)" strokeWidth={thickness} />
      {segments.map((s, i) => {
        const frac = s.value / total;
        const dash = `${c * frac} ${c * (1 - frac)}`;
        const offset = c * (1 - acc);
        acc += frac;
        const isHov = hovered === i;
        return (
          <circle key={s.id} cx={size/2} cy={size/2} r={r} fill="none"
            stroke={s.color} strokeWidth={isHov ? thickness + 4 : thickness}
            strokeDasharray={dash} strokeDashoffset={offset}
            transform={`rotate(-90 ${size/2} ${size/2})`} strokeLinecap="butt"
            style={{ cursor: "pointer", transition: "stroke-width 0.12s" }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          />
        );
      })}
      {displayCenter && (
        <foreignObject x={thickness} y={thickness} width={size - thickness*2} height={size - thickness*2}>
          <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", textAlign: "center" }}>
            {displayCenter}
          </div>
        </foreignObject>
      )}
    </svg>
  );
}

/* ========== Bar chart (monthly) ========== */
function Bars({ data, height = 180, privacy = false }) {
  // data: [{label, income, spend}]
  const wrapRef = useRef(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((ents) => { for (const e of ents) setW(e.contentRect.width); });
    ro.observe(wrapRef.current); return () => ro.disconnect();
  }, []);
  const max = Math.max(1, ...data.flatMap((d) => [d.income, d.spend]));
  const padX = 12, padY = 20;
  const bw = Math.max(8, (w - padX * 2) / data.length / 3);
  const gap = (w - padX * 2) / data.length;
  return (
    <div ref={wrapRef} style={{ height, filter: privacy ? "blur(8px)" : "none" }}>
      <svg width={w} height={height}>
        {[0.25, 0.5, 0.75].map((t, i) => (
          <line key={i} x1={padX} x2={w-padX} y1={padY + t*(height-padY*2)} y2={padY + t*(height-padY*2)}
            stroke="oklch(0.88 0.008 80)" strokeDasharray="2 4" />
        ))}
        {data.map((d, i) => {
          const x = padX + i * gap + gap/2;
          const hi = (d.income / max) * (height - padY * 2);
          const hs = (d.spend / max) * (height - padY * 2);
          return (
            <g key={i}>
              <rect x={x - bw - 1} y={height - padY - hi} width={bw} height={hi}
                fill="oklch(0.48 0.09 150)" />
              <rect x={x + 1} y={height - padY - hs} width={bw} height={hs}
                fill="oklch(0.48 0.11 35)" />
              <text x={x} y={height - 4} textAnchor="middle" fontSize="10"
                fill="oklch(0.52 0.008 70)" fontFamily="JetBrains Mono, monospace">{d.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

Object.assign(window, { Icon, BankBadge, CategoryChip, StatBlock, Sparkline, Ring, Bars });

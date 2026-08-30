import type { DrillProgress } from './api'

/** 1〜6。ドリル全体のレベル・ステージ進捗から算出。 */
export function starTierFromProgress(rows: DrillProgress[]): number {
  if (rows.length === 0) return 1
  const ratios = rows.map((row) => {
    const max = Math.max(row.max_step, 1)
    if (max <= 1) return 0
    const step = Math.min(Math.max(row.step, 1), max)
    return (step - 1) / (max - 1)
  })
  const avg = ratios.reduce((sum, value) => sum + value, 0) / ratios.length
  return Math.min(6, Math.max(1, 1 + Math.floor(avg * 5.999)))
}

type Sparkle = { char: string; className: string }

type StarStage = {
  icon: string
  scale: number
  glow: string
  sparkles: Sparkle[]
}

const STAR_STAGES: StarStage[] = [
  { icon: '⭐', scale: 1, glow: 'none', sparkles: [] },
  {
    icon: '⭐',
    scale: 1.08,
    glow: 'drop-shadow(0 2px 4px rgba(255, 209, 102, 0.55))',
    sparkles: [{ char: '✦', className: 'absolute -right-1 -top-0.5 text-[0.55rem] text-sun' }],
  },
  {
    icon: '🌟',
    scale: 1.14,
    glow: 'drop-shadow(0 0 8px rgba(255, 209, 102, 0.75))',
    sparkles: [
      { char: '✦', className: 'absolute -right-2 top-0 text-xs text-sun' },
      { char: '✦', className: 'absolute -left-1.5 bottom-0 text-[0.6rem] text-sun/80' },
    ],
  },
  {
    icon: '🌟',
    scale: 1.22,
    glow: 'drop-shadow(0 0 10px rgba(255, 122, 69, 0.35)) drop-shadow(0 0 14px rgba(255, 209, 102, 0.8))',
    sparkles: [
      { char: '✨', className: 'absolute -right-3 top-1 text-sm' },
      { char: '✦', className: 'absolute -left-2 top-2 text-xs text-sun' },
      { char: '✦', className: 'absolute right-0 -bottom-2 text-[0.65rem] text-sun' },
    ],
  },
  {
    icon: '💫',
    scale: 1.28,
    glow: 'drop-shadow(0 0 12px rgba(255, 209, 102, 0.9)) drop-shadow(0 0 4px rgba(77, 182, 226, 0.45))',
    sparkles: [
      { char: '✨', className: 'absolute -right-3 -top-1 text-base' },
      { char: '✨', className: 'absolute -left-3 top-0 text-sm' },
      { char: '✦', className: 'absolute left-1/2 -bottom-3 -translate-x-1/2 text-xs text-sun' },
    ],
  },
  {
    icon: '🌠',
    scale: 1.34,
    glow: 'drop-shadow(0 0 14px rgba(255, 209, 102, 1)) drop-shadow(0 0 8px rgba(255, 122, 69, 0.5))',
    sparkles: [
      { char: '✨', className: 'absolute -right-4 top-0 text-lg' },
      { char: '✨', className: 'absolute -left-4 top-1 text-base' },
      { char: '✦', className: 'absolute -top-2 left-1/2 -translate-x-1/2 text-sm text-sun' },
      { char: '✦', className: 'absolute -bottom-3 left-1/2 -translate-x-1/2 text-xs text-coral/80' },
    ],
  },
]

const TIER_LABELS = ['はじめて', 'すこし つよい', 'みんな しってる', 'とても つよい', 'スーパー', 'マスター'] as const

export function GrowthStar({ tier }: { tier: number }) {
  const stage = STAR_STAGES[Math.min(Math.max(tier, 1), STAR_STAGES.length) - 1]
  const label = TIER_LABELS[Math.min(Math.max(tier, 1), TIER_LABELS.length) - 1]

  return (
    <div
      className="relative inline-flex h-12 w-12 items-center justify-center"
      role="img"
      aria-label={`ほしのつよさ ${label}`}
    >
      {stage.sparkles.map((sparkle, index) => (
        <span key={index} className={`pointer-events-none ${sparkle.className}`} aria-hidden>
          {sparkle.char}
        </span>
      ))}
      <span
        className="inline-block text-4xl leading-none transition-transform duration-500"
        style={{
          transform: `scale(${stage.scale})`,
          filter: stage.glow === 'none' ? undefined : stage.glow,
        }}
        aria-hidden
      >
        {stage.icon}
      </span>
    </div>
  )
}

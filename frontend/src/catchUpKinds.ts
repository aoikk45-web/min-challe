import type { DrillKind, DrillProgress } from './api'

export type CatchUpKindStat = {
  kind: DrillKind
  step: number
  expected: number
  lag: number
  stepLabel: string
}

export type CatchUpResult = {
  kinds: CatchUpKindStat[]
  /** behind: めやす未満あり / slowest: すべてめやす以上なので相対的に遅いもの */
  mode: 'behind' | 'slowest'
}

const TOP_N = 3

const HUNDRED_STEP_KINDS = new Set([
  'たしざん',
  'ひきざん',
  'かけざん',
  'わりざん',
  'かんじのよみ',
  'じゅくごのよみ',
])

const RIKA_EIGO_KINDS = new Set([
  'いきもののせいかつ',
  'じしゃくとでんき',
  'たいようとかげ',
  'ひかりとおと',
  'てんきとみず',
  'たんご',
  'あいさつ',
])

/** Curriculum floor step for this school grade (学習要領めやす). */
export function expectedStepForKind(kind: string, schoolGrade: number, maxStep: number): number {
  const grade = Math.min(Math.max(schoolGrade, 1), 6)
  if (maxStep >= 100 || HUNDRED_STEP_KINDS.has(kind)) {
    // 1–17 小1 … 35–51 小3 …（drill_progress.step_label と同じ帯）
    return (grade - 1) * 17 + 1
  }
  if (RIKA_EIGO_KINDS.has(kind)) {
    // stage1–2≒小3、3≒小4、4≒小5、5–6≒小6
    if (grade <= 2) return 1
    if (grade === 3) return 2
    return Math.min(6, grade - 1)
  }
  // 社会・読解: ステージ番号 ≒ 学年の上限
  return Math.min(Math.max(maxStep, 1), grade)
}

function toStat(row: DrillProgress, schoolGrade: number): CatchUpKindStat {
  const step = row.step
  const expected = expectedStepForKind(row.kind, schoolGrade, row.max_step)
  return {
    kind: row.kind as DrillKind,
    step,
    expected,
    lag: expected - step,
    stepLabel: row.step_label,
  }
}

function byMostBehind(a: CatchUpKindStat, b: CatchUpKindStat) {
  return b.lag - a.lag || a.step - b.step || a.kind.localeCompare(b.kind, 'ja')
}

/** Prefer kinds below curriculum floor; if none, the relatively slowest vs めやす. */
export function rankCatchUpKinds(progress: DrillProgress[], schoolGrade: number): CatchUpResult {
  const all = progress.map((row) => toStat(row, schoolGrade))
  const behind = all.filter((row) => row.lag > 0)
  if (behind.length > 0) {
    return { mode: 'behind', kinds: [...behind].sort(byMostBehind).slice(0, TOP_N) }
  }
  if (all.length === 0) {
    return { mode: 'slowest', kinds: [] }
  }
  return { mode: 'slowest', kinds: [...all].sort(byMostBehind).slice(0, TOP_N) }
}

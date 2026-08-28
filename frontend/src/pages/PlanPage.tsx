import type { Role } from '../role'

export default function PlanPage({ role }: { role: Role }) {
  return (
    <Empty
      emoji="📒"
      title="学習計画"
      body={
        role === 'child'
          ? 'まだ予定がないよ。おうちの人につくってもらおう。'
          : '次のループで、今週の計画を置けるようにします。'
      }
    />
  )
}

export function Empty({ emoji, title, body }: { emoji: string; title: string; body: string }) {
  return (
    <section className="rounded-3xl bg-white p-8 text-center shadow-sm">
      <p className="text-5xl">{emoji}</p>
      <h2 className="mt-3 text-xl font-black">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-ink/70">{body}</p>
    </section>
  )
}

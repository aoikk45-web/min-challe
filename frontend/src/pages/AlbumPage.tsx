import { Empty } from './PlanPage'
import type { Role } from '../role'

export default function AlbumPage({ role }: { role: Role }) {
  return (
    <Empty
      emoji="📔"
      title="成長アルバム"
      body={
        role === 'child'
          ? '最初のページは、これからつくられるよ。'
          : 'できた記録と一言メモは、あとのループで残せるようにします。'
      }
    />
  )
}

import { Empty } from './PlanPage'
import type { Role } from '../role'

export default function DrillPage({ role }: { role: Role }) {
  return (
    <Empty
      emoji="✨"
      title="計算ドリル"
      body={
        role === 'child'
          ? 'もうすぐ 10もん できるよ。つぎのループで あそべるよ。'
          : 'たしざん・ひきざん・かけざん・わりざんは次のループで実装します。'
      }
    />
  )
}

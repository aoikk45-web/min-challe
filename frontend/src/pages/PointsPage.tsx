import { Empty } from './PlanPage'
import type { Role } from '../role'

export default function PointsPage({ role }: { role: Role }) {
  return (
    <Empty
      emoji="🏅"
      title="ポイント"
      body={
        role === 'child'
          ? 'がんばりが みえるように するよ。おうちの人が ルールを きめるよ。'
          : '家庭ごとの付与ルールとごほうびは、あとのループで設定できます。'
      }
    />
  )
}

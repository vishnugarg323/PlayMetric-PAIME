import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

interface BugData {
  bug_type: string
  count: number
}

interface BugDistributionChartProps {
  data: BugData[]
}

const COLORS = {
  crash: '#ef4444',
  performance: '#f59e0b',
  visual: '#3b82f6',
  gameplay: '#8b5cf6',
  other: '#6b7280'
}

export default function BugDistributionChart({ data }: BugDistributionChartProps) {
  const chartData = data.map(item => ({
    name: item.bug_type,
    value: item.count
  }))
  
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell 
              key={`cell-${index}`} 
              fill={COLORS[entry.name as keyof typeof COLORS] || COLORS.other} 
            />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  )
}
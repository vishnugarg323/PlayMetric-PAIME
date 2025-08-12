import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface TelemetryData {
  timestamp: string
  fps: number
  cpu_usage: number
  memory_usage: number
}

interface TelemetryChartProps {
  data: TelemetryData[]
}

export default function TelemetryChart({ data }: TelemetryChartProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
      
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="fps" stroke="#3b82f6" />
            <Line type="monotone" dataKey="cpu_usage" stroke="#ef4444" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
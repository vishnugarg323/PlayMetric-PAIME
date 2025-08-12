import { Brain } from 'lucide-react'

interface AIThoughtsProps {
  sessionId: string
}

export default function AIThoughts({ }: AIThoughtsProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center mb-4">
        <Brain className="w-5 h-5 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold">AI Analysis</h3>
      </div>
      
      <div className="space-y-3">
        <div className="p-3 bg-blue-50 rounded">
          <p className="text-sm">Analyzing game mechanics...</p>
        </div>
        <div className="p-3 bg-green-50 rounded">
          <p className="text-sm">Found optimal path through level 1</p>
        </div>
        <div className="p-3 bg-yellow-50 rounded">
          <p className="text-sm">Detected potential UI issue at coordinates (234, 456)</p>
        </div>
      </div>
    </div>
  )
}
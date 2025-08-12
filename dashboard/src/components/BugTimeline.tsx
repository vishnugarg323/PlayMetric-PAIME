import { AlertCircle } from 'lucide-react'

interface Bug {
  bug_id: string
  bug_type: string
  severity: string
  description: string
  timestamp: string
}

interface BugTimelineProps {
  bugs: Bug[]
}

export default function BugTimeline({ bugs }: BugTimelineProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center mb-4">
        <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
        <h3 className="text-lg font-semibold">Detected Issues</h3>
      </div>
      
      <div className="space-y-3">
        {bugs.length === 0 ? (
          <p className="text-gray-500">No bugs detected</p>
        ) : (
          bugs.map((bug) => (
            <div key={bug.bug_id} className="border-l-4 border-red-500 pl-3">
              <p className="font-medium text-sm">{bug.bug_type}</p>
              <p className="text-sm text-gray-600">{bug.description}</p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
import { Activity } from 'lucide-react'
import { useState, useEffect } from 'react'

type ActivityItem = {
  activity_id: string
  type: 'bug_found' | 'session_started' | 'session_completed'
  message: string
  timestamp: string
  game_name?: string
  version?: string
  max_level_reached?: number
  total_bugs_found?: number
}

export default function RecentActivity() {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  
  useEffect(() => {
    const fetchActivities = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/activities')
        const data = await response.json()
        setActivities(data)
      } catch (error) {
        console.error('Failed to fetch activities:', error)
      }
    }
    
    fetchActivities()
    // Refresh activities every 30 seconds
    const interval = setInterval(fetchActivities, 30000)
    return () => clearInterval(interval)
  }, [])
  
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center mb-4">
        <Activity className="w-5 h-5 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold">Recent Activity</h3>
      </div>
      
      <div className="space-y-3">
        {activities.map((activity) => (
          <div key={activity.activity_id} className="flex items-start">
            <div className="w-2 h-2 bg-blue-600 rounded-full mt-1.5 mr-3"></div>
            <div>
              <p className="text-sm">{activity.message}</p>
              <p className="text-xs text-gray-500">{activity.timestamp}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
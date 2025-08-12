import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  icon: LucideIcon
  trend?: string
  trendUp?: boolean
}

export default function StatCard({ title, value, icon: Icon, trend, trendUp }: StatCardProps) {
  return (
    <div className="group bg-white rounded-xl shadow-md hover:shadow-lg transition-all duration-300 p-6 border border-gray-100 hover:border-blue-200 cursor-pointer transform hover:-translate-y-1">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors duration-300">{value}</p>
          {trend && (
            <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              trendUp 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              <span className="mr-1">{trendUp ? '↗' : '↘'}</span>
              {trend}
            </div>
          )}
        </div>
        <div className={`p-4 rounded-full transition-all duration-300 ${
          title.includes('Games') ? 'bg-purple-100 group-hover:bg-purple-200' :
          title.includes('Bugs') ? 'bg-red-100 group-hover:bg-red-200' :
          title.includes('Sessions') ? 'bg-green-100 group-hover:bg-green-200' :
          'bg-blue-100 group-hover:bg-blue-200'
        }`}>
          <Icon className={`w-7 h-7 transition-all duration-300 ${
            title.includes('Games') ? 'text-purple-600 group-hover:text-purple-700' :
            title.includes('Bugs') ? 'text-red-600 group-hover:text-red-700' :
            title.includes('Sessions') ? 'text-green-600 group-hover:text-green-700' :
            'text-blue-600 group-hover:text-blue-700'
          }`} />
        </div>
      </div>
    </div>
  )
}
import React, { useEffect, useState } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";
// Install with: npm install react-chartjs-2 chart.js

type DqnLossType = { timestamp: string; loss: number };
type ActionSuccessType = { action_type: string; outcome: string; count: number };
type AiThoughtType = { timestamp: string; thought: string };
type AnalyticsDashboardProps = { sessionId: string; gameId: string };

const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ sessionId, gameId }) => {
  const [dqnLoss, setDqnLoss] = useState<DqnLossType[]>([]);
  const [actionSuccess, setActionSuccess] = useState<ActionSuccessType[]>([]);
  const [aiThoughts, setAiThoughts] = useState<AiThoughtType[]>([]);

  useEffect(() => {
    axios.get(`/api/analytics/dqn-loss?session_id=${sessionId}&game_id=${gameId}`).then(res => setDqnLoss(res.data));
    axios.get(`/api/analytics/action-success?game_id=${gameId}`).then(res => setActionSuccess(res.data));
    axios.get(`/api/analytics/ai-thoughts?session_id=${sessionId}&game_id=${gameId}`).then(res => setAiThoughts(res.data));
  }, [sessionId, gameId]);

  const dqnLossData = {
    labels: dqnLoss.length ? dqnLoss.map(d => d.timestamp) : ["No Data"],
    datasets: [{ label: "DQN Loss", data: dqnLoss.length ? dqnLoss.map(d => d.loss) : [0], borderColor: "#3b82f6", fill: false }],
  };
  const actionTypes = actionSuccess.length ? Array.from(new Set(actionSuccess.map(a => a.action_type))) : [];
  const outcomes = actionSuccess.length ? Array.from(new Set(actionSuccess.map(a => a.outcome))) : [];
  const thoughts = aiThoughts.length ? aiThoughts.map(t => `${t.timestamp}: ${t.thought}`) : ["No agent thoughts available."];

  return (
    <div className="p-4 grid gap-6">
      <h2 className="text-xl font-bold">Agent Analytics</h2>
      <div>
        <h3 className="font-semibold">DQN Learning Curve</h3>
        <Line data={dqnLossData} />
      </div>
      <div>
        <h3 className="font-semibold">Action Success Table</h3>
        <table className="min-w-full text-xs border">
          <thead>
            <tr>
              <th>Action Type</th>
              {outcomes.map(o => <th key={o}>{o}</th>)}
            </tr>
          </thead>
          <tbody>
            {actionTypes.map(type => (
              <tr key={type}>
                <td>{type}</td>
                {outcomes.map(outcome => {
                  const found = actionSuccess.find(a => a.action_type === type && a.outcome === outcome);
                  return <td key={outcome}>{found ? found.count : 0}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <h3 className="font-semibold">Agent Thoughts Timeline</h3>
        <div className="bg-gray-100 p-2 rounded">
          {thoughts.map((t, i) => <div key={i} className="text-xs mb-1">{t}</div>)}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
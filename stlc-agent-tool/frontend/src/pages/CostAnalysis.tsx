import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { DollarSign, BarChart3, Zap } from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  BarElement
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export function CostAnalysis() {
  const { projectName, token } = useAppContext();
  const [summary, setSummary] = useState({ total_tokens: 0, total_cost_usd: 0, total_calls: 0 });
  const [breakdown, setBreakdown] = useState<any[]>([]);
  const [groupBy, setGroupBy] = useState('agent_name');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectName) return;
    setLoading(true);
    // Fetch Summary
    fetch(`/api/cost/summary?project_name=${projectName}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch summary');
        return res.json();
      })
      .then(data => setSummary(data))
      .catch(console.error);

    // Fetch Breakdown
    fetch(`/api/cost/breakdown?project_name=${projectName}&group_by=${groupBy}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch breakdown');
        return res.json();
      })
      .then(data => setBreakdown(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [groupBy]);

  const chartData = {
    labels: breakdown.map(b => b.group),
    datasets: [
      {
        label: 'Cost (USD)',
        data: breakdown.map(b => b.cost_usd),
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const, labels: { color: '#a1a1aa' } },
    },
    scales: {
      y: { ticks: { color: '#a1a1aa' }, grid: { color: '#3f3f46' } },
      x: { ticks: { color: '#a1a1aa' }, grid: { color: '#3f3f46' } }
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <DollarSign className="h-6 w-6 text-primary" />
          Cost Analysis
        </h1>
        <p className="text-secondary mt-1 text-sm">
          Track LLM token consumption and cost across agents, models, and providers.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4 bg-card border-border flex items-center gap-4">
          <div className="p-3 bg-primary/10 rounded-full text-primary">
            <Zap className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm text-secondary">Total Tokens</p>
            <p className="text-2xl font-bold">{summary.total_tokens.toLocaleString()}</p>
          </div>
        </Card>
        
        <Card className="p-4 bg-card border-border flex items-center gap-4">
          <div className="p-3 bg-success/10 rounded-full text-success">
            <DollarSign className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm text-secondary">Cost (USD)</p>
            <p className="text-2xl font-bold">${summary.total_cost_usd.toFixed(4)}</p>
          </div>
        </Card>

        <Card className="p-4 bg-card border-border flex items-center gap-4">
          <div className="p-3 bg-blue-500/10 rounded-full text-blue-500">
            <BarChart3 className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm text-secondary">LLM Calls</p>
            <p className="text-2xl font-bold">{summary.total_calls.toLocaleString()}</p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-4 bg-card border-border col-span-2">
          <h3 className="font-semibold mb-4">Cost Distribution</h3>
          <Bar data={chartData} options={chartOptions} />
        </Card>
        
        <Card className="p-4 bg-card border-border flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold">Breakdown</h3>
            <select 
              className="bg-main border border-border text-xs rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
            >
              <option value="agent_name">By Agent</option>
              <option value="model">By Model</option>
              <option value="provider">By Provider</option>
            </select>
          </div>
          
          <div className="flex-1 overflow-y-auto pr-2">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-secondary uppercase bg-main/50 sticky top-0">
                <tr>
                  <th className="px-3 py-2 rounded-l">Group</th>
                  <th className="px-3 py-2 text-right">Calls</th>
                  <th className="px-3 py-2 text-right rounded-r">Cost</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.map((row, idx) => (
                  <tr key={idx} className="border-b border-border/50 hover:bg-elevated/50 transition-colors">
                    <td className="px-3 py-2 font-medium text-primary">{row.group}</td>
                    <td className="px-3 py-2 text-right">{row.calls}</td>
                    <td className="px-3 py-2 text-right text-success">${row.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {breakdown.length === 0 && !loading && (
              <div className="text-center text-secondary py-8 text-sm">No usage data found.</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

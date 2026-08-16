import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { RefreshCw, PlaySquare, CheckCircle, XCircle, SkipForward, Clock, TrendingUp } from 'lucide-react';
import { useAppContext } from '../context/AppContext';

interface TestResult {
  test_id: string;
  test_name: string;
  category: string;
  status: string;
  duration_seconds: number;
  error_message: string | null;
  jira_story: string;
  timestamp: string;
}

interface SuiteRun {
  suite_id: string;
  suite_name: string;
  suite_type: string;
  project: string;
  run_id: string;
  triggered_by: string;
  started_at: string;
  completed_at: string;
  summary: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    pass_rate: number;
  };
  results: TestResult[];
}

export function Executions() {
  const { projectName, token } = useAppContext();
  const [deploymentMode, setDeploymentMode] = useState('centralized');
  const [syncing, setSyncing] = useState(false);
  const [runs, setRuns] = useState<SuiteRun[]>([]);
  const [expandedRun, setExpandedRun] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/execution/config', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => setDeploymentMode(data.deployment_mode))
      .catch(console.error);

    // Fetch execution results
    fetch(`/api/execution/results?project_name=${projectName}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed');
        return res.json();
      })
      .then(data => setRuns(data))
      .catch(console.error);
  }, [projectName]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch('/api/execution/sync', { 
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      alert(`Synced ${data.synced_files} results to central platform.`);
    } catch (e) {
      alert("Error syncing results.");
    } finally {
      setSyncing(false);
    }
  };

  const totalTests = runs.reduce((s, r) => s + r.summary.total, 0);
  const totalPassed = runs.reduce((s, r) => s + r.summary.passed, 0);
  const totalFailed = runs.reduce((s, r) => s + r.summary.failed, 0);
  const totalSkipped = runs.reduce((s, r) => s + r.summary.skipped, 0);
  const overallPassRate = totalTests > 0 ? ((totalPassed / totalTests) * 100).toFixed(1) : '0';

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <PlaySquare className="h-6 w-6 text-primary" />
            Test Executions
          </h1>
          <p className="text-secondary mt-1 text-sm">
            View test execution history, drill into individual results, and sync offline runs.
          </p>
        </div>
        <div className="flex gap-2">
          {deploymentMode === 'disconnected' && (
            <Button variant="outline" className="text-warning border-warning" onClick={handleSync}>
              <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing...' : 'Sync Now (Disconnected Mode)'}
            </Button>
          )}
          <Button onClick={() => window.open(`/api/reports/${projectName}`, '_blank')} className="bg-primary text-white hover:bg-primary/90">
            Download HTML Report
          </Button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="p-3 bg-card border border-border text-center">
          <p className="text-xs text-secondary uppercase tracking-wider">Suites</p>
          <p className="text-2xl font-bold text-primary">{runs.length}</p>
        </Card>
        <Card className="p-3 bg-card border border-border text-center">
          <p className="text-xs text-secondary uppercase tracking-wider">Total Tests</p>
          <p className="text-2xl font-bold">{totalTests}</p>
        </Card>
        <Card className="p-3 bg-card border border-border text-center">
          <p className="text-xs text-secondary uppercase tracking-wider">Passed</p>
          <p className="text-2xl font-bold text-green-400">{totalPassed}</p>
        </Card>
        <Card className="p-3 bg-card border border-border text-center">
          <p className="text-xs text-secondary uppercase tracking-wider">Failed</p>
          <p className="text-2xl font-bold text-red-400">{totalFailed}</p>
        </Card>
        <Card className="p-3 bg-card border border-border text-center">
          <p className="text-xs text-secondary uppercase tracking-wider">Pass Rate</p>
          <p className="text-2xl font-bold text-primary">{overallPassRate}%</p>
        </Card>
      </div>

      {/* Suite Runs */}
      <div className="grid grid-cols-1 gap-4">
        {runs.length === 0 && (
          <Card className="p-8 bg-card text-center text-secondary">No execution results found. Run a test suite first.</Card>
        )}
        {runs.map(run => (
          <Card key={run.run_id} className="bg-card border border-border overflow-hidden">
            <div 
              className="p-4 flex justify-between items-center cursor-pointer hover:bg-elevated/50 transition-colors"
              onClick={() => setExpandedRun(expandedRun === run.run_id ? null : run.run_id)}
            >
              <div className="flex gap-4 items-center">
                {run.summary.failed === 0 ? (
                  <CheckCircle className="text-green-400 h-6 w-6" />
                ) : (
                  <XCircle className="text-red-400 h-6 w-6" />
                )}
                <div>
                  <h3 className="font-semibold text-primary">{run.suite_name}</h3>
                  <div className="flex gap-3 text-xs text-secondary mt-1 flex-wrap">
                    <span className="bg-elevated px-2 py-0.5 rounded border border-border">{run.suite_type}</span>
                    <span>Run: {run.run_id}</span>
                    <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {new Date(run.completed_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="flex gap-2 text-xs">
                  <span className="text-green-400 font-semibold">{run.summary.passed}P</span>
                  <span className="text-red-400 font-semibold">{run.summary.failed}F</span>
                  <span className="text-yellow-400 font-semibold">{run.summary.skipped}S</span>
                </div>
                <div className="text-sm font-bold text-primary">{run.summary.pass_rate}%</div>
              </div>
            </div>
            
            {/* Expanded details */}
            {expandedRun === run.run_id && (
              <div className="border-t border-border px-4 py-3 bg-main/30">
                <table className="w-full text-sm">
                  <thead className="text-xs text-secondary uppercase">
                    <tr>
                      <th className="text-left px-2 py-1">Test ID</th>
                      <th className="text-left px-2 py-1">Name</th>
                      <th className="text-left px-2 py-1">Category</th>
                      <th className="text-left px-2 py-1">Status</th>
                      <th className="text-right px-2 py-1">Duration</th>
                      <th className="text-left px-2 py-1">Jira</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run.results.map(r => (
                      <tr key={r.test_id} className="border-b border-border/30 hover:bg-elevated/30 transition-colors">
                        <td className="px-2 py-1.5 font-mono text-xs">{r.test_id}</td>
                        <td className="px-2 py-1.5">{r.test_name}</td>
                        <td className="px-2 py-1.5">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                            r.category === 'positive' ? 'bg-green-500/20 text-green-400' :
                            r.category === 'negative' ? 'bg-red-500/20 text-red-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>{r.category}</span>
                        </td>
                        <td className="px-2 py-1.5">
                          <span className={`flex items-center gap-1 text-xs font-semibold ${
                            r.status === 'passed' ? 'text-green-400' :
                            r.status === 'failed' ? 'text-red-400' :
                            'text-yellow-400'
                          }`}>
                            {r.status === 'passed' && <CheckCircle className="h-3 w-3" />}
                            {r.status === 'failed' && <XCircle className="h-3 w-3" />}
                            {r.status === 'skipped' && <SkipForward className="h-3 w-3" />}
                            {r.status.toUpperCase()}
                          </span>
                          {r.error_message && (
                            <p className="text-[10px] text-red-400/70 mt-0.5 font-mono">{r.error_message}</p>
                          )}
                        </td>
                        <td className="px-2 py-1.5 text-right text-xs">{r.duration_seconds}s</td>
                        <td className="px-2 py-1.5 text-xs text-primary">{r.jira_story}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

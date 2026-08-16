import React, { useState, useEffect } from 'react';
import { Database, Play, CheckCircle, AlertTriangle, Activity } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/Table';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useAppContext } from '../context/AppContext';

// Minimal stub for RAG Eval to satisfy Batch 04 requirements in the UI
export function RAGEval() {
  const { projectName } = useAppContext();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [results, setResults] = useState<any[]>([]);
  const [generateCount, setGenerateCount] = useState(50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchDatasets = async () => {
    try {
      const res = await fetch(`/api/rag-eval/?project_name=${projectName}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('stlc_token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDatasets(data.datasets || []);
        setResults(data.results || []);
      } else {
        const err = await res.json();
        console.error("Failed to fetch datasets:", err);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, [projectName]);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/rag-eval/generate', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('stlc_token')}`
        },
        body: JSON.stringify({ project_name: projectName, count: generateCount })
      });
      if (res.ok) {
        fetchDatasets();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to generate');
      }
    } catch (e) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async (datasetId: number) => {
    try {
      const res = await fetch(`/api/rag-eval/${datasetId}/accept`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('stlc_token')}`
        },
        body: JSON.stringify({ use_as_canary: true }) // hardcoded to true for demo
      });
      if (res.ok) {
        fetchDatasets();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleRun = async (datasetId: number) => {
    try {
      await fetch(`/api/rag-eval/${datasetId}/run`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('stlc_token')}` }
      });
      alert('Evaluation started in background!');
    } catch (e) {
      console.error(e);
    }
  };


  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            RAG Evaluation
          </h1>
          <p className="text-secondary mt-1 text-sm">
            Monitor the health and hallucinations of the RAG test generation pipeline.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Button onClick={() => window.open('/api/reports/default', '_blank')} className="bg-primary text-white hover:bg-primary/90 whitespace-nowrap">
            Download HTML Report
          </Button>
          <select 
            value={generateCount}
            onChange={(e) => setGenerateCount(Number(e.target.value))}
            className="bg-card border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-primary"
          >
            <option value={10}>10 Pairs</option>
            <option value={50}>50 Pairs</option>
            <option value={100}>100 Pairs</option>
          </select>
          <Button onClick={handleGenerate} disabled={loading} className="whitespace-nowrap">
            {loading ? 'Generating...' : 'Generate Dataset'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-fail/10 border border-fail/30 text-fail px-4 py-3 rounded-md flex items-center gap-2 text-sm">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      {/* Canary Alert Stub */}
      {results.some(r => r.run_type === 'canary' && (r.faithfulness < 0.7 || r.context_precision < 0.7)) && (
        <div className="bg-warning/10 border border-warning/30 text-warning px-4 py-3 rounded-md flex items-center gap-2 text-sm">
          <AlertTriangle className="h-4 w-4" />
          <strong>Canary Alert:</strong> RAG Quality metrics dropped below threshold (0.7) on the latest scheduled run. Check the knowledge base ingestion logs.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Generated Datasets
            </CardTitle>
          </CardHeader>
          <CardContent>
            {datasets.length === 0 ? (
              <p className="text-sm text-secondary">No datasets generated yet.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Pairs</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {datasets.map(ds => (
                    <TableRow key={ds.dataset_id}>
                      <TableCell>#{ds.dataset_id}</TableCell>
                      <TableCell>{ds.count}</TableCell>
                      <TableCell>
                        <StatusBadge 
                          status={ds.status === 'accepted' ? 'pass' : 'pending'} 
                          className="mr-2"
                        />
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                        {ds.status === 'pending_review' && (
                          <Button variant="secondary" size="sm" onClick={() => handleAccept(ds.dataset_id)}>
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Accept
                          </Button>
                        )}
                        {ds.status === 'accepted' && (
                          <Button size="sm" onClick={() => handleRun(ds.dataset_id)}>
                            <Play className="h-4 w-4 mr-1" />
                            Run Eval
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Evaluation Results</CardTitle>
          </CardHeader>
          <CardContent>
            {results.length === 0 ? (
              <p className="text-sm text-secondary">No evaluation results yet.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Dataset</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Faithfulness</TableHead>
                    <TableHead>Answer Rel.</TableHead>
                    <TableHead>Ctx Prec.</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map(r => (
                    <TableRow key={r.result_id}>
                      <TableCell>#{r.dataset_id}</TableCell>
                      <TableCell className="capitalize">{r.run_type}</TableCell>
                      <TableCell className={r.faithfulness < 0.7 ? 'text-warning' : 'text-success'}>
                        {r.faithfulness.toFixed(2)}
                      </TableCell>
                      <TableCell>{r.answer_relevancy.toFixed(2)}</TableCell>
                      <TableCell className={r.context_precision < 0.7 ? 'text-warning' : 'text-success'}>
                        {r.context_precision.toFixed(2)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

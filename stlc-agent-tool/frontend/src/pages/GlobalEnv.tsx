import React, { useState } from 'react';
import { Settings, Save, Server, Cpu, Database } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

const PROVIDER_MODELS = {
  vllm: [
    'meta-llama/Meta-Llama-3.1-8B-Instruct', 
    'meta-llama/Meta-Llama-3-8B-Instruct',
    'mistralai/Mistral-Nemo-Instruct-2407',
    'mistralai/Mixtral-8x7B-Instruct-v0.1',
    'Qwen/Qwen2-72B-Instruct',
    'Qwen/Qwen2-7B-Instruct',
    'google/gemma-2-9b-it'
  ],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-5-sonnet-20240620', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
  gemini: ['gemini-1.5-pro', 'gemini-1.5-flash'],
  mistral: ['mistral-large-latest', 'mistral-small-latest', 'open-mixtral-8x22b'],
  ollama: ['llama3.1', 'llama3', 'mistral', 'mixtral', 'gemma2', 'qwen2', 'phi3']
};

const EMBEDDING_MODELS = {
  vllm: ['BAAI/bge-large-en-v1.5', 'BAAI/bge-m3'],
  openai: ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002'],
  anthropic: ['voyage-large-2', 'voyage-lite-2-instruct'],
  gemini: ['text-embedding-004'],
  mistral: ['mistral-embed'],
  ollama: ['nomic-embed-text', 'mxbai-embed-large']
};

export function GlobalEnv() {
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState({
    llmProvider: 'vllm',
    modelName: 'meta-llama/Meta-Llama-3-8B-Instruct',
    qdrantUrl: 'http://localhost:6333',
    celeryWorkers: 4,
    celeryConcurrency: 8,
    llmApiKey: '',
    embeddingModel: 'text-embedding-3-small',
    maxRetryCount: 3,
    maxBatches: 10,
    fallbackSeconds: 10,
    jiraUrl: '',
    jiraEmail: '',
    jiraApiKey: '',
  });

  React.useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/admin/global-env', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('stlc_token')}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setConfig(prev => ({
            ...prev,
            ...data,
            // Keep the password fields blank if the backend doesn't return them
            llmApiKey: prev.llmApiKey,
            jiraApiKey: prev.jiraApiKey
          }));
        }
      } catch (err) {
        console.error("Failed to fetch global env", err);
      }
    };
    fetchConfig();
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/admin/global-env', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('stlc_token')}`
        },
        body: JSON.stringify(config)
      });
      if (res.ok) {
        alert('Global Environment settings saved and applied to running services.');
      } else {
        const err = await res.json();
        alert(`Failed to save: ${err.detail}`);
      }
    } catch (err) {
      alert('Network error while saving Global Env.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Settings className="h-6 w-6 text-primary" />
            Global Environment Settings
          </h1>
          <p className="text-secondary mt-1 text-sm">
            Configure system-wide parameters. These settings affect all projects and agents.
          </p>
        </div>
        <Button onClick={handleSave} disabled={loading} className="bg-primary text-white">
          <Save className="h-4 w-4 mr-2" />
          {loading ? 'Saving...' : 'Save Configuration'}
        </Button>
      </div>

      <div className="grid gap-6">
        {/* LLM Routing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              LLM Provider & Routing
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Primary Provider</label>
                <select 
                  value={config.llmProvider}
                  onChange={e => {
                    const newProvider = e.target.value as keyof typeof PROVIDER_MODELS;
                    setConfig({
                      ...config, 
                      llmProvider: newProvider,
                      modelName: PROVIDER_MODELS[newProvider]?.[0] || '',
                      embeddingModel: EMBEDDING_MODELS[newProvider]?.[0] || ''
                    });
                  }}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                >
                  <option value="vllm">vLLM (Self-Hosted GPU)</option>
                  <option value="openai">OpenAI (Cloud)</option>
                  <option value="anthropic">Anthropic (Cloud)</option>
                  <option value="gemini">Google Gemini (Cloud)</option>
                  <option value="mistral">Mistral (Cloud)</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Model Name</label>
                <input 
                  type="text"
                  list="model-options"
                  value={config.modelName}
                  onChange={e => setConfig({...config, modelName: e.target.value})}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                  placeholder="e.g., meta-llama/Meta-Llama-3-8B-Instruct"
                />
                <datalist id="model-options">
                  {PROVIDER_MODELS[config.llmProvider as keyof typeof PROVIDER_MODELS]?.map(model => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">API Key (Leave blank to keep existing)</label>
                <input 
                  type="password" 
                  value={config.llmApiKey}
                  onChange={e => setConfig({...config, llmApiKey: e.target.value})}
                  placeholder="sk-..."
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Embedding Model Name</label>
                <input 
                  type="text"
                  list="embedding-options"
                  value={config.embeddingModel}
                  onChange={e => setConfig({...config, embeddingModel: e.target.value})}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                  placeholder="e.g., text-embedding-3-small"
                />
                <datalist id="embedding-options">
                  {EMBEDDING_MODELS[config.llmProvider as keyof typeof EMBEDDING_MODELS]?.map(model => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Vector DB */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Vector Database (Knowledge Hub)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary mb-1">Qdrant Connection URL</label>
              <input 
                type="text" 
                value={config.qdrantUrl}
                onChange={e => setConfig({...config, qdrantUrl: e.target.value})}
                className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
              />
            </div>
          </CardContent>
        </Card>

        {/* Jira MCP Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Jira Integration (MCP)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Jira URL</label>
                <input 
                  type="text" 
                  value={config.jiraUrl}
                  onChange={e => setConfig({...config, jiraUrl: e.target.value})}
                  placeholder="https://your-domain.atlassian.net"
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Jira Email</label>
                <input 
                  type="email" 
                  value={config.jiraEmail}
                  onChange={e => setConfig({...config, jiraEmail: e.target.value})}
                  placeholder="user@example.com"
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-secondary mb-1">Jira API Token (Leave blank to keep existing)</label>
                <input 
                  type="password" 
                  value={config.jiraApiKey}
                  onChange={e => setConfig({...config, jiraApiKey: e.target.value})}
                  placeholder="Jira API Token"
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Distributed Execution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Distributed Execution (Celery)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Worker Count</label>
                <input 
                  type="number" 
                  value={config.celeryWorkers}
                  onChange={e => setConfig({...config, celeryWorkers: parseInt(e.target.value) || 0})}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Concurrency per Worker</label>
                <input 
                  type="number" 
                  value={config.celeryConcurrency}
                  onChange={e => setConfig({...config, celeryConcurrency: parseInt(e.target.value) || 0})}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Max Retry Count</label>
                <input 
                  type="number" 
                  value={config.maxRetryCount}
                  onChange={e => setConfig({...config, maxRetryCount: parseInt(e.target.value) || 0})}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Max Batches</label>
                <input 
                  type="number" 
                  value={config.maxBatches}
                  onChange={e => setConfig({...config, maxBatches: parseInt(e.target.value) || 0})}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Fallback Seconds (Wait on 429 Error)</label>
                <input 
                  type="number" 
                  value={config.fallbackSeconds}
                  onChange={e => setConfig({...config, fallbackSeconds: parseInt(e.target.value) || 0})}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

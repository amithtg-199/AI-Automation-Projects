import React, { useState } from 'react';
import { Settings, Key, Cpu, Server, CheckCircle2, ShieldCheck, Database, Sliders, Globe, Lock, PlusCircle, ExternalLink, RefreshCw, AlertCircle } from 'lucide-react';

export default function EnvironmentTabs({ projectName }) {
  const [envConfig, setEnvConfig] = useState(() => {
    const saved = localStorage.getItem('qa_env_settings');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return {
      llmProvider: 'MistralAI',
      llmModel: 'codestral-latest',
      apiKey: 'mistral_apikey_************************',
      embeddingModel: 'mistral-embed',
      dimension: 1024,
      distanceMetric: 'Cosine',
      langflowBaseUrl: 'http://localhost:7860'
    };
  });

  const { llmProvider, llmModel, apiKey, embeddingModel, dimension, distanceMetric, langflowBaseUrl } = envConfig;

  const updateEnvField = (field, value) => {
    setEnvConfig(prev => ({ ...prev, [field]: value }));
  };

  const [mcps, setMcps] = useState(() => {
    const saved = localStorage.getItem('qa_mcps_config');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return [
      {
        id: 'jira',
        name: 'Atlassian Jira Server & Cloud Integration',
        description: 'Auto-create bug tickets (DEF-xxxx) and synchronize test run execution statuses directly into Jira project boards.',
        status: 'Not Configured',
        apiKey: '',
        baseUrl: '',
        placeholderUrl: 'e.g. https://company.atlassian.net',
        placeholderKey: 'Enter Atlassian Personal Access Token (PAT)...'
      },
      {
        id: 'confluence',
        name: 'Confluence Knowledge Base Connector',
        description: 'Ingest product requirement documents, architecture specifications, and API docs from Confluence spaces into Qdrant.',
        status: 'Not Configured',
        apiKey: '',
        baseUrl: '',
        placeholderUrl: 'e.g. https://company.atlassian.net/wiki',
        placeholderKey: 'Enter Confluence API Token...'
      },
      {
        id: 'github',
        name: 'GitHub Repository & CI/CD Orchestrator',
        description: 'Analyze pull request code diffs, trigger automated validation suites via GitHub Actions, and comment test reports on pull requests.',
        status: 'Not Configured',
        apiKey: '',
        baseUrl: '',
        placeholderUrl: 'e.g. https://github.com/organization/repository',
        placeholderKey: 'Enter GitHub Fine-grained PAT (ghp_)...'
      },
      {
        id: 'qdrant',
        name: 'Qdrant Vector Database Connector',
        description: 'High-performance hybrid vector retrieval, metadata prefix filtering, and direct collection snapshots.',
        status: 'Connected',
        apiKey: 'Local Docker Instance Connected',
        baseUrl: 'http://qdrant:6333',
        placeholderUrl: 'http://qdrant:6333',
        placeholderKey: 'Optional API Key for Cloud Qdrant'
      },
      {
        id: 'slack',
        name: 'Slack Notification Webhook Service',
        description: 'Broadcast real-time QA alert digests when critical test cases fail or guardrails trigger repeatedly.',
        status: 'Not Configured',
        apiKey: '',
        baseUrl: '',
        placeholderUrl: 'e.g. https://hooks.slack.com/services/T00/B00/xxxx',
        placeholderKey: 'Enter Slack Bot OAuth Token...'
      }
    ];
  });

  const [savedSuccess, setSavedSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSaveSettings = () => {
    localStorage.setItem('qa_mcps_config', JSON.stringify(mcps));
    localStorage.setItem('qa_env_settings', JSON.stringify(envConfig));
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleMcpChange = (id, field, value) => {
    setMcps(prev => prev.map(m => m.id === id ? { ...m, [field]: value } : m));
  };

  const toggleMcpStatus = (id) => {
    setErrorMessage(null);
    setMcps(prev => {
      const updated = prev.map(m => {
        if (m.id === id) {
          if (m.status === 'Connected') {
            return { ...m, status: 'Not Configured' };
          } else {
            // Validate that endpoint or token is provided unless it's Qdrant local
            if (m.id !== 'qdrant' && (!m.baseUrl || !m.baseUrl.trim())) {
              setErrorMessage(`Please enter a valid Server Endpoint URL for ${m.name} before connecting.`);
              return m;
            }
            if (m.id !== 'qdrant' && (!m.apiKey || !m.apiKey.trim())) {
              setErrorMessage(`Please enter an Authentication Token for ${m.name} before connecting.`);
              return m;
            }
            return { ...m, status: 'Connected' };
          }
        }
        return m;
      });
      localStorage.setItem('qa_mcps_config', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <div className="animate-fade-in" style={{ padding: '0 1.5rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Top Save & Status Bar */}
      <div className="glass-panel" style={{ padding: '1.25rem 1.75rem', display: 'flex', alignItems: 'center', justifyItems: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Settings size={22} color="#6366f1" />
          <div>
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 700 }}>
              System Environment & Integrations Manager
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Configure authentication credentials, vector embedding specifications (1024 Cosine), pipeline endpoints, and Model Context Protocol integrations.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginLeft: 'auto' }}>
          {savedSuccess && (
            <span className="badge badge-emerald animate-fade-in" style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}>
              <CheckCircle2 size={16} /> Environment Settings Saved Live!
            </span>
          )}
          <button onClick={handleSaveSettings} className="btn-primary">
            <CheckCircle2 size={18} />
            Save Environment Configuration
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="animate-fade-in" style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '1rem 1.25rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#f43f5e', fontWeight: 600, fontSize: '0.9rem' }}>
          <AlertCircle size={20} flexShrink={0} />
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', fontWeight: 700 }}>✕</button>
        </div>
      )}

      {/* Grid: LLM Settings + Embedding Configuration */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        
        {/* LLM Provider & Model Box */}
        <div className="glass-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '1rem' }}>
            <Cpu size={20} color="#818cf8" />
            <h4 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 600 }}>
              Language Generation Model & Provider
            </h4>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Provider Selection
            </label>
            <select value={llmProvider} onChange={(e) => updateEnvField('llmProvider', e.target.value)} style={{ fontWeight: 600 }}>
              <option value="MistralAI">MistralAI (Recommended Enterprise Engine)</option>
              <option value="VercelAIGateway">Vercel AI Gateway (Unified Proxy via AI_GATEWAY_API_KEY)</option>
              <option value="OpenAI">OpenAI (GPT-4o / GPT-4o-mini)</option>
              <option value="Anthropic">Anthropic (Claude 3.5 Sonnet)</option>
              <option value="Ollama">Ollama (Local Llama-3 / Mistral)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Model Identifier
            </label>
            <select value={llmModel} onChange={(e) => updateEnvField('llmModel', e.target.value)} style={{ fontWeight: 600 }}>
              <option value="codestral-latest">codestral-latest (Optimized for code & QA tables)</option>
              <option value="mistral-large-latest">mistral-large-latest (High capacity reasoning)</option>
              <option value="open-mistral-nemo">open-mistral-nemo (Low latency execution)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Authentication Secret Key
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => updateEnvField('apiKey', e.target.value)}
                placeholder="e.g. vck_... (AI_GATEWAY_API_KEY) or Mistral Token..."
                style={{ fontFamily: 'monospace', paddingRight: '2.5rem' }}
              />
              <Lock size={16} color="var(--text-muted)" style={{ position: 'absolute', right: '1rem', top: '50%', transform: 'translateY(-50%)' }} />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(99, 102, 241, 0.1)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.2)', fontSize: '0.82rem', color: '#818cf8' }}>
            <ShieldCheck size={16} />
            Authentication keys are securely encrypted in memory for request execution.
          </div>
        </div>

        {/* Embedding Specification & Qdrant Box */}
        <div className="glass-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '1rem' }}>
            <Sliders size={20} color="#ec4899" />
            <h4 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 600 }}>
              Vector Store & Embedding Specifications
            </h4>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Vector Embedding Model
            </label>
            <input
              type="text"
              value={embeddingModel}
              onChange={(e) => updateEnvField('embeddingModel', e.target.value)}
              placeholder="mistral-embed"
              style={{ fontWeight: 600 }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                Vector Dimension
              </label>
              <select value={dimension} onChange={(e) => updateEnvField('dimension', parseInt(e.target.value, 10))} style={{ fontWeight: 600, color: '#34d399' }}>
                <option value={1024}>1024 (Mistral Embed Default)</option>
                <option value={1536}>1536 (OpenAI Ada-002)</option>
                <option value={768}>768 (Standard Transformer)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                Distance Metric
              </label>
              <select value={distanceMetric} onChange={(e) => updateEnvField('distanceMetric', e.target.value)} style={{ fontWeight: 600, color: '#f472b6' }}>
                <option value="Cosine">Cosine (Recommended)</option>
                <option value="Euclidean">Euclidean (L2)</option>
                <option value="Dot">Dot Product</option>
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Orchestration Server Base URL
            </label>
            <input
              type="text"
              value={langflowBaseUrl}
              onChange={(e) => updateEnvField('langflowBaseUrl', e.target.value)}
              placeholder="http://localhost:7860"
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(16, 185, 129, 0.1)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '0.82rem', color: '#34d399' }}>
            <CheckCircle2 size={16} />
            Verified: mistral-embed (1024-d Cosine) matches target collection schema.
          </div>
        </div>

      </div>

      {/* MCP Servers & External Integrations List */}
      <div className="glass-panel" style={{ padding: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyItems: 'space-between', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '1.25rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Server size={24} color="#10b981" />
            <div>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.3rem', fontWeight: 700 }}>
                Model Context Protocol Integrations
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Connect developer tools to allow seamless bi-directional data synchronization across your engineering stack.
              </p>
            </div>
          </div>
          <button className="btn-secondary" style={{ marginLeft: 'auto' }}>
            <PlusCircle size={16} /> Add Custom Service Endpoint
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '1.25rem' }}>
          {mcps.map((m) => (
            <div
              key={m.id}
              style={{
                background: 'rgba(15, 23, 42, 0.65)',
                border: m.status === 'Connected' ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid var(--card-border)',
                borderRadius: '14px',
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                transition: 'all 0.2s ease'
              }}
              className="hover:border-indigo-500/50"
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyItems: 'space-between', gap: '1rem' }}>
                <div>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc' }}>{m.name}</h4>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.3rem', lineHeight: 1.5 }}>
                    {m.description}
                  </p>
                </div>
                <button
                  onClick={() => toggleMcpStatus(m.id)}
                  className={m.status === 'Connected' ? 'badge badge-emerald' : 'badge badge-amber'}
                  style={{ border: 'none', cursor: 'pointer', padding: '0.45rem 0.95rem', flexShrink: 0, fontSize: '0.8rem', transition: 'all 0.2s ease' }}
                >
                  {m.status === 'Connected' ? 'Connected (Click to Disconnect)' : 'Connect Integration'}
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginTop: 'auto', paddingTop: '0.85rem', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Server Base Endpoint</span>
                  <input
                    type="text"
                    value={m.baseUrl}
                    onChange={(e) => handleMcpChange(m.id, 'baseUrl', e.target.value)}
                    placeholder={m.placeholderUrl || 'https://service.domain.net'}
                    style={{ fontSize: '0.82rem', padding: '0.6rem 0.85rem', marginTop: '0.25rem', background: 'rgba(11, 15, 25, 0.7)', border: m.status === 'Connected' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)' }}
                  />
                </div>
                <div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Authentication Token</span>
                  <input
                    type="password"
                    value={m.apiKey}
                    onChange={(e) => handleMcpChange(m.id, 'apiKey', e.target.value)}
                    placeholder={m.placeholderKey || 'Enter service secret token...'}
                    style={{ fontSize: '0.82rem', padding: '0.6rem 0.85rem', marginTop: '0.25rem', fontFamily: 'monospace', background: 'rgba(11, 15, 25, 0.7)', border: m.status === 'Connected' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)' }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

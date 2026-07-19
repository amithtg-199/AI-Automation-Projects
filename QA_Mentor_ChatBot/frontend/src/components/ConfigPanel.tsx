import React, { useState } from 'react';

const knowledgeBaseItems = [
  { id: 'selenium', name: 'Selenium repo', count: 5, color: 'bg-yellow-500' },
  { id: 'playwright', name: 'Playwright repo', count: 5, color: 'bg-green-500' },
  { id: 'tests', name: 'Test Cases', count: 4, color: 'bg-blue-500' },
  { id: 'jira', name: 'JIRA tickets', count: 3, color: 'bg-blue-600' },
  { id: 'docs', name: 'Company Docs', count: 2, color: 'bg-purple-500' },
  { id: 'notes', name: 'Meeting Notes', count: 1, color: 'bg-orange-600' },
  { id: 'prd', name: 'PRD / BRD / SRS', count: 1, color: 'bg-pink-500' },
  { id: 'jenkins', name: 'Jenkins Logs', count: 2, color: 'bg-red-600' },
  { id: 'glossary', name: 'Glossary', count: 2, color: 'bg-blue-400' },
];

const ConfigPanel: React.FC = () => {
    const [selected, setSelected] = useState<string[]>(knowledgeBaseItems.map(i => i.id));
    const [status, setStatus] = useState('');
    const [envStatus, setEnvStatus] = useState('');
    const [projectName, setProjectName] = useState('project_1');
    const [backendUrl, setBackendUrl] = useState(() => localStorage.getItem('backendUrl') || 'http://localhost:8000');

    React.useEffect(() => {
        localStorage.setItem('backendUrl', backendUrl);
    }, [backendUrl]);

    const [progress, setProgress] = useState<{
        status: string;
        total_files: number;
        extracted_files: number;
        total_chunks: number;
        embedded_chunks: number;
        category_chunks?: Record<string, number>;
    }>({
        status: 'idle',
        total_files: 0,
        extracted_files: 0,
        total_chunks: 0,
        embedded_chunks: 0
    });
    
    React.useEffect(() => {
        const interval = setInterval(async () => {
            if (!projectName) return;
            try {
                const res = await fetch(`${backendUrl}/progress/${projectName}`);
                const data = await res.json();
                setProgress(data);
            } catch (e) {
                // Ignore network errors on polling
            }
        }, 2000);
        return () => clearInterval(interval);
    }, [projectName]);
    
    // Env State
    const [qdrantUrl, setQdrantUrl] = useState('http://localhost:6333');
    const [mistralKey, setMistralKey] = useState('');
    const [jiraUrl, setJiraUrl] = useState('');

    const handleSaveEnv = async () => {
        setEnvStatus('saving...');
        try {
            const res = await fetch(`${backendUrl}/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    qdrant_url: qdrantUrl,
                    mistral_api_key: mistralKey,
                    jira_url: jiraUrl
                })
            });
            const data = await res.json();
            setEnvStatus(data.message || 'saved');
            setTimeout(() => setEnvStatus(''), 3000);
        } catch(e) {
            setEnvStatus('error saving');
        }
    };

    const handleIngest = async () => {
        setStatus('Processing files...');
        try {
            const res = await fetch(`${backendUrl}/ingest`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_name: projectName })
            });
            const data = await res.json();
            setStatus(data.message || 'Ingestion triggered.');
            setTimeout(() => setStatus(''), 4000);
        } catch(e) {
            setStatus('Failed to connect to backend.');
        }
    };

    const toggleAll = () => setSelected(knowledgeBaseItems.map(i => i.id));
    const toggleNone = () => setSelected([]);
    
    const toggleItem = (id: string) => {
        setSelected(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    return (
        <div className="flex flex-col h-full w-full py-8 px-6 overflow-y-auto text-gray-800 bg-[#FFFDF7]">
            {/* Header */}
            <div className="mb-10 flex items-center justify-between">
                <div className="text-[10px] font-mono tracking-[0.2em] text-gray-400 uppercase">
                    Configuration
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-[10px] font-mono text-gray-400">Connected</span>
                </div>
            </div>

            {/* Knowledge Base Section */}
            <div className="flex-1">
                <h2 className="text-xs font-mono tracking-[0.15em] text-gray-500 uppercase mb-4">
                    Knowledge Base
                </h2>
                
                <div className="space-y-3 mb-6">
                    {knowledgeBaseItems.map((item) => {
                        // Fetch actual chunks from backend state mapped by ID
                        const actualCount = progress.category_chunks ? (progress.category_chunks[item.id] || 0) : 0;
                        return (
                        <div key={item.id} className="flex items-center justify-between group cursor-pointer" onClick={() => toggleItem(item.id)}>
                            <div className="flex items-center gap-3">
                                <input 
                                    type="checkbox" 
                                    checked={selected.includes(item.id)}
                                    readOnly
                                    className="w-[14px] h-[14px] text-orange-500 rounded-[4px] border-gray-300 focus:ring-0 cursor-pointer accent-orange-500"
                                />
                                <div className={`w-2 h-2 rounded-full ${item.color}`}></div>
                                <span className="text-[15px] font-medium text-gray-700">{item.name}</span>
                            </div>
                            <span className="text-[13px] font-mono text-gray-500">{actualCount}</span>
                        </div>
                        );
                    })}
                </div>

                <div className="flex items-center gap-2 mb-4">
                    <span className="text-[11px] font-mono uppercase tracking-[0.1em] text-gray-500">total chunks</span>
                    <span className="text-[11px] font-mono text-orange-500 font-medium">{progress.total_chunks}</span>
                </div>
                <div className="flex gap-2 mb-10">
                    <button onClick={toggleAll} className="px-4 py-1 text-[13px] font-mono border border-gray-300 rounded-full text-gray-600 hover:bg-white transition-colors">all</button>
                    <button onClick={toggleNone} className="px-4 py-1 text-[13px] font-mono border border-gray-300 rounded-full text-gray-600 hover:bg-white transition-colors">none</button>
                </div>

                {/* Mode Select */}
                <h2 className="text-xs font-mono tracking-[0.15em] text-gray-500 uppercase mb-4">
                    Mode
                </h2>
                <div className="mb-10 border-b border-[#F0EBE1] pb-8">
                    <select className="w-full bg-white border border-[#F0EBE1] rounded-lg p-2 text-xs font-mono text-gray-600 focus:outline-none focus:ring-2 focus:ring-orange-500/20 appearance-none shadow-sm">
                        <option>auto-detect</option>
                        <option>force-graph</option>
                        <option>force-vector</option>
                    </select>
                </div>

                {/* Ingest Action */}
                <div className="flex flex-col mb-8 border-b border-[#F0EBE1] pb-8">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-[10px] font-mono tracking-[0.2em] text-gray-500 uppercase">
                            Ingest
                        </h2>
                        <button onClick={handleIngest} className="px-4 py-1.5 text-[11px] font-mono border border-gray-200 bg-white rounded-full text-gray-600 hover:border-orange-300 hover:text-orange-600 transition-colors shadow-sm">
                            open
                        </button>
                    </div>

                    {/* Progress UI */}
                    {(progress.status !== 'idle' || progress.total_files > 0 || progress.total_chunks > 0) && (
                        <div className="bg-[#FFFEFC] border border-[#F0EBE1] rounded-lg p-3 shadow-sm">
                            <div className="text-[11px] font-mono text-gray-600 uppercase mb-2 flex items-center justify-between">
                                <span>Status</span>
                                <span className="text-orange-500">{progress.status}</span>
                            </div>
                            
                            <div className="space-y-2">
                                <div>
                                    <div className="flex justify-between text-[10px] font-mono text-gray-400 mb-1">
                                        <span>Files Extracted</span>
                                        <span>{progress.extracted_files} / {progress.total_files}</span>
                                    </div>
                                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                                        <div className="bg-orange-400 h-1.5 rounded-full transition-all duration-300" style={{ width: `${progress.total_files > 0 ? (progress.extracted_files / progress.total_files) * 100 : 0}%` }}></div>
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-[10px] font-mono text-gray-400 mb-1">
                                        <span>Chunks Embedded</span>
                                        <span>{progress.embedded_chunks} / {progress.total_chunks}</span>
                                    </div>
                                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                                        <div className="bg-orange-500 h-1.5 rounded-full transition-all duration-300" style={{ width: `${progress.total_chunks > 0 ? (progress.embedded_chunks / progress.total_chunks) * 100 : 0}%` }}></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                    
                    {status && <div className="text-xs font-mono text-orange-500 mt-3">{status}</div>}
                </div>

                {/* Environment Variables Table */}
                <h2 className="text-xs font-mono tracking-[0.15em] text-gray-500 uppercase mt-10 mb-4">
                    Environment Variables
                </h2>
                <div className="border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm mb-3">
                    <table className="w-full text-left text-[13px]">
                        <tbody className="divide-y divide-gray-100">
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 border-r border-gray-100">Project Name</td>
                                <td className="p-0 relative">
                                    <input type="text" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-orange-500/20 transition-all bg-transparent" value={projectName} onChange={e => setProjectName(e.target.value)} />
                                </td>
                            </tr>
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 w-[40%] border-r border-gray-100">Backend URL</td>
                                <td className="p-0 relative">
                                    <input type="text" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-orange-500/20 transition-all bg-transparent" value={backendUrl} onChange={e => setBackendUrl(e.target.value)} />
                                </td>
                            </tr>
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 border-r border-gray-100">Qdrant URL</td>
                                <td className="p-0 relative">
                                    <input type="text" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-orange-500/20 transition-all bg-transparent" value={qdrantUrl} onChange={e => setQdrantUrl(e.target.value)} />
                                </td>
                            </tr>
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 border-r border-gray-100">Mistral API</td>
                                <td className="p-0 relative">
                                    <input type="password" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-orange-500/20 transition-all bg-transparent" placeholder="Loaded from .env" value={mistralKey} onChange={e => setMistralKey(e.target.value)} />
                                </td>
                            </tr>
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 border-r border-gray-100">Jira MCP</td>
                                <td className="p-0 relative">
                                    <input type="text" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-orange-500/20 transition-all bg-transparent placeholder-gray-300" placeholder="https://domain.atlassian.net" value={jiraUrl} onChange={e => setJiraUrl(e.target.value)} />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div className="flex items-center justify-between mb-8">
                    {envStatus ? (
                        <div className="text-[11px] font-mono text-orange-500">{envStatus}</div>
                    ) : (
                        <div></div>
                    )}
                    <button onClick={handleSaveEnv} className="px-4 py-1 text-[13px] font-mono border border-orange-500 text-orange-500 rounded-full hover:bg-orange-500 hover:text-white transition-colors">
                        save config
                    </button>
                </div>
            </div>

            {/* Footer Metadata */}
            <div className="mt-auto pt-6 text-[10px] font-mono text-gray-400 leading-relaxed space-y-1">
                <div>llm <span className="text-gray-600">Mistral AI</span></div>
                <div>search <span className="text-gray-600">Qdrant DB BM25 Hybrid</span></div>
            </div>
        </div>
    );
};

export default ConfigPanel;

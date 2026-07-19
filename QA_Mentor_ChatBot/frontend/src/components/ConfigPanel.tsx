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
                const res = await fetch(`http://localhost:8000/progress/${projectName}`);
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
            const res = await fetch('http://localhost:8000/config', {
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
            const res = await fetch('http://localhost:8000/ingest', { 
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
        <div className="flex flex-col h-full w-full py-8 px-6 overflow-y-auto text-gray-800">
            {/* Header */}
            <div className="mb-10">
                <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-green-500 mt-1"></div>
                    <h1 className="text-[28px] leading-none font-bold text-[#1F2937]">QA Buddy</h1>
                </div>
                <div className="text-[10px] font-mono tracking-[0.2em] text-gray-400 mt-2 ml-6 uppercase">
                    QA Knowledge System
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
                                    className="w-[14px] h-[14px] text-orange-600 rounded-[3px] border-gray-300 focus:ring-0 cursor-pointer accent-[#D95F4D]"
                                />
                                <div className={`w-2 h-2 rounded-full ${item.color}`}></div>
                                <span className="text-[15px] font-medium text-gray-700">{item.name}</span>
                            </div>
                            <span className="text-[13px] font-mono text-gray-500">{actualCount}</span>
                        </div>
                        );
                    })}
                </div>

                {/* Stats & Actions */}
                <div className="flex items-center gap-2 mb-4">
                    <span className="text-[11px] font-mono uppercase tracking-[0.1em] text-gray-500">total chunks</span>
                    <span className="text-[11px] font-mono text-[#D95F4D] font-medium">{progress.total_chunks}</span>
                </div>
                <div className="flex gap-2 mb-10">
                    <button onClick={toggleAll} className="px-4 py-1 text-[13px] font-mono border border-gray-300 rounded-full text-gray-600 hover:bg-white transition-colors">all</button>
                    <button onClick={toggleNone} className="px-4 py-1 text-[13px] font-mono border border-gray-300 rounded-full text-gray-600 hover:bg-white transition-colors">none</button>
                </div>

                {/* Mode Select */}
                <h2 className="text-xs font-mono tracking-[0.15em] text-gray-500 uppercase mb-4">
                    Mode
                </h2>
                <div className="mb-10 border-b border-[#E5E0D8] pb-8">
                    <select className="w-full bg-[#F8F6F0] border border-gray-300 rounded-lg p-2 text-xs font-mono text-gray-600 focus:outline-none focus:ring-2 focus:ring-[#D95F4D]/20 appearance-none">
                        <option>auto-detect</option>
                        <option>force-graph</option>
                        <option>force-vector</option>
                    </select>
                </div>

                {/* Ingest Action */}
                <div className="flex items-center justify-between mb-8 border-b border-[#E5E0D8] pb-8">
                    <h2 className="text-[10px] font-mono tracking-[0.2em] text-gray-500 uppercase">
                        Ingest
                    </h2>
                    <button onClick={handleIngest} className="px-4 py-1.5 text-[11px] font-mono border border-gray-300 rounded-full text-gray-600 hover:bg-white transition-colors">
                        open
                    </button>
                </div>
                {status && <div className="text-xs font-mono text-[#D95F4D] mb-4">{status}</div>}

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
                                    <input type="text" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#D95F4D]/20 transition-all bg-transparent" value={projectName} onChange={e => setProjectName(e.target.value)} />
                                </td>
                            </tr>
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 w-[40%] border-r border-gray-100">Qdrant URL</td>
                                <td className="p-0 relative">
                                    <input type="text" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#D95F4D]/20 transition-all bg-transparent" value={qdrantUrl} onChange={e => setQdrantUrl(e.target.value)} />
                                </td>
                            </tr>
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 border-r border-gray-100">Mistral API</td>
                                <td className="p-0 relative">
                                    <input type="password" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#D95F4D]/20 transition-all bg-transparent" placeholder="Loaded from .env" value={mistralKey} onChange={e => setMistralKey(e.target.value)} />
                                </td>
                            </tr>
                            <tr className="group">
                                <td className="p-3 font-mono text-gray-500 bg-gray-50/50 border-r border-gray-100">Jira MCP</td>
                                <td className="p-0 relative">
                                    <input type="text" className="w-full h-full p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#D95F4D]/20 transition-all bg-transparent placeholder-gray-300" placeholder="https://domain.atlassian.net" value={jiraUrl} onChange={e => setJiraUrl(e.target.value)} />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div className="flex items-center justify-between mb-8">
                    {envStatus ? (
                        <div className="text-[11px] font-mono text-[#D95F4D]">{envStatus}</div>
                    ) : (
                        <div></div>
                    )}
                    <button onClick={handleSaveEnv} className="px-4 py-1 text-[13px] font-mono border border-[#D95F4D] text-[#D95F4D] rounded-full hover:bg-[#D95F4D] hover:text-white transition-colors">
                        save config
                    </button>
                </div>
            </div>

            {/* Footer Metadata */}
            <div className="mt-auto pt-6 text-[10px] font-mono text-gray-400 leading-relaxed space-y-1">
                <div>llm <span className="text-gray-600">Mistral AI</span></div>
                <div>search <span className="text-gray-600">Qdrant DB BM25 Hybrid</span></div>
                <div className="text-[#D95F4D] mt-2 cursor-pointer hover:underline">architecture docs</div>
            </div>
        </div>
    );
};

export default ConfigPanel;

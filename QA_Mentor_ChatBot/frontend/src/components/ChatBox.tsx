import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const ChatBox: React.FC = () => {
    const [messages, setMessages] = useState<{role: string, content: string}[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSend = async (text: string = input) => {
        if (!text.trim()) return;
        
        const userMsg = text;
        setMessages(prev => [...prev, {role: 'user', content: userMsg}]);
        setInput('');
        setIsLoading(true);
        
        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userMsg, project_name: 'project_1' })
            });
            const data = await response.json();
            setMessages(prev => [...prev, {role: 'assistant', content: data.response}]);
        } catch (error) {
            setMessages(prev => [...prev, {role: 'assistant', content: 'Error connecting to backend.'}]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full w-full bg-[#FCFBF9]">
            {/* Top Navigation Breadcrumb */}
            <div className="h-14 border-b border-[#E5E0D8] flex items-center justify-between px-8 text-[11px] font-mono text-gray-400 tracking-[0.1em]">
                <div>ask <span className="mx-2">&rsaquo;</span> hybrid search <span className="mx-2">&rsaquo;</span> rerank <span className="mx-2">&rsaquo;</span> cited answer</div>
                <div className="flex items-center gap-2">
                    online <div className="w-1.5 h-1.5 rounded-full bg-green-500 opacity-80"></div>
                </div>
            </div>

            {/* Main Scrollable Area */}
            <div className="flex-1 overflow-y-auto p-8 relative flex flex-col items-center">
                
                {messages.length === 0 ? (
                    <div className="w-full max-w-3xl mt-16 flex flex-col items-start px-4">
                        {/* Empty State Hero */}
                        <div className="text-[#D95F4D] text-3xl font-light mb-4">*</div>
                        <h1 className="text-5xl text-gray-900 mb-6 font-medium tracking-tight">QA Buddy</h1>
                        <p className="text-gray-500 text-[17px] leading-relaxed max-w-2xl font-light mb-12">
                            One question, one <span className="text-[#D95F4D] font-medium">cited</span> answer, grounded in your team's real QA knowledge: the Selenium & Playwright frameworks, ~5,000 test cases, JIRA history, PRDs, meeting notes, and Jenkins logs.
                        </p>

                        {/* How it works card - Apple Style Glassmorphism */}
                        <div className="w-full bg-white/70 backdrop-blur-xl border border-gray-200/60 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-3xl p-8 mb-12 transition-all duration-500 hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)]">
                            <h2 className="text-[10px] font-mono tracking-[0.2em] text-gray-400 uppercase mb-8">
                                How your answer is fetched
                            </h2>
                            <div className="grid grid-cols-2 gap-x-12 gap-y-8">
                                {/* Step 1 */}
                                <div className="flex gap-4">
                                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-[#D95F4D]/30 flex items-center justify-center text-[#D95F4D] text-xs font-mono">1</div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-900 mb-1">Understand</h3>
                                        <p className="text-[13px] text-gray-500 leading-relaxed">your question is condensed and rewritten into search variants using GraphRAG relationships.</p>
                                    </div>
                                </div>
                                {/* Step 2 */}
                                <div className="flex gap-4">
                                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-[#D95F4D]/30 flex items-center justify-center text-[#D95F4D] text-xs font-mono">2</div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-900 mb-1">Hybrid search</h3>
                                        <p className="text-[13px] text-gray-500 leading-relaxed">meaning (dense Qdrant vectors) + exact keywords (BM25) across selected QA sources.</p>
                                    </div>
                                </div>
                                {/* Step 3 */}
                                <div className="flex gap-4">
                                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-[#D95F4D]/30 flex items-center justify-center text-[#D95F4D] text-xs font-mono">3</div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-900 mb-1">Fuse & rerank</h3>
                                        <p className="text-[13px] text-gray-500 leading-relaxed">both result lists merge (RRF), a cross-encoder keeps the top most relevant chunks.</p>
                                    </div>
                                </div>
                                {/* Step 4 */}
                                <div className="flex gap-4">
                                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-[#D95F4D]/30 flex items-center justify-center text-[#D95F4D] text-xs font-mono">4</div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-900 mb-1">Cited answer</h3>
                                        <p className="text-[13px] text-gray-500 leading-relaxed">Mistral AI answers only from those chunks, citing [n] &rarr; file:line, ticket, or build.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        {/* Suggestion Chips */}
                        <div className="flex flex-wrap gap-3 w-full">
                            <button onClick={() => handleSend("What are the test cases for user checkout?")} className="px-5 py-2.5 rounded-full border border-gray-200 bg-white/50 text-[13px] text-gray-600 hover:border-[#D95F4D]/40 hover:text-[#D95F4D] transition-all shadow-sm">What are the test cases for user checkout?</button>
                            <button onClick={() => handleSend("Why did Jenkins build #4504 fail?")} className="px-5 py-2.5 rounded-full border border-gray-200 bg-white/50 text-[13px] text-gray-600 hover:border-[#D95F4D]/40 hover:text-[#D95F4D] transition-all shadow-sm">Why did Jenkins build #4504 fail?</button>
                            <button onClick={() => handleSend("Summarize the login flow PRD")} className="px-5 py-2.5 rounded-full border border-gray-200 bg-white/50 text-[13px] text-gray-600 hover:border-[#D95F4D]/40 hover:text-[#D95F4D] transition-all shadow-sm">Summarize the login flow PRD</button>
                        </div>
                    </div>
                ) : (
                    <div className="w-full max-w-3xl flex flex-col space-y-10 pb-24">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} w-full`}>
                                <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'bg-[#F2F0E9] border border-[#E5E0D8] rounded-3xl rounded-tr-sm px-6 py-4 shadow-sm' : 'px-2'}`}>
                                    {msg.role === 'assistant' && (
                                        <div className="w-6 h-6 rounded-full bg-[#D95F4D] flex-shrink-0 mt-1 mr-5 shadow-sm opacity-90 flex items-center justify-center text-white text-[10px]">*</div>
                                    )}
                                    <div className={`text-[15px] leading-relaxed ${msg.role === 'user' ? 'text-gray-800' : 'text-gray-800 prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-white prose-pre:border prose-pre:border-gray-200 prose-pre:text-gray-800 prose-pre:shadow-sm prose-a:text-[#D95F4D] prose-a:no-underline hover:prose-a:underline prose-strong:font-semibold'}`}>
                                        {msg.role === 'user' ? (
                                            msg.content
                                        ) : (
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        
                        {isLoading && (
                            <div className="flex justify-start w-full px-2">
                                <div className="w-6 h-6 rounded-full bg-[#D95F4D] flex-shrink-0 mt-1 mr-5 shadow-sm opacity-40 animate-pulse"></div>
                                <div className="text-[14px] text-gray-400 animate-pulse mt-1.5 font-light">
                                    Synthesizing response from knowledge base...
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Input Area Floating */}
            <div className="p-6 pt-0 flex flex-col items-center w-full z-10 bg-gradient-to-t from-[#FCFBF9] via-[#FCFBF9] to-transparent">
                <div className="w-full max-w-3xl relative">
                    <div className="relative group rounded-3xl transition-all duration-300">
                        <input 
                            type="text" 
                            className="w-full bg-white/90 backdrop-blur-md border border-[#D95F4D] rounded-3xl py-4 pl-6 pr-16 text-[15px] text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-[#D95F4D]/10 shadow-[0_4px_20px_rgb(217,95,77,0.08)] transition-all"
                            placeholder="ask about tests, tickets, failures, the framework..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isLoading}
                        />
                        <button 
                            onClick={() => handleSend(input)}
                            disabled={isLoading || !input.trim()}
                            className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-[#E8E6DF] text-gray-500 rounded-2xl hover:bg-[#D95F4D] hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M14.707 9.293a1 1 0 00-1.414-1.414L11 10.586V3a1 1 0 10-2 0v7.586L6.707 7.879a1 1 0 10-1.414 1.414l4 4a1 1 0 001.414 0l4-4z" clipRule="evenodd" transform="rotate(180 10 10)" />
                            </svg>
                        </button>
                    </div>
                    <div className="flex justify-between items-center mt-3 px-4 w-full text-[10px] font-mono text-gray-400">
                        <div>enter to send &middot; shift+enter for newline</div>
                        <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-gray-300"></span> answers always cite their sources</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatBox;

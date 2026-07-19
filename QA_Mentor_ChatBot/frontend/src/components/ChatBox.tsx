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
        <div className="flex flex-col h-full w-full bg-[#FFFEFC]">
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
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-yellow-100 to-orange-100 flex items-center justify-center mb-6 shadow-sm border border-orange-200/50">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                            </svg>
                        </div>
                        <h1 className="text-4xl md:text-5xl text-gray-900 mb-6 font-semibold tracking-tight">QA Mentor Chatbot</h1>
                        <p className="text-gray-500 text-[16px] md:text-[18px] leading-relaxed max-w-2xl font-light mb-12">
                            One question, one <span className="text-orange-500 font-medium">cited</span> answer. I am grounded in your team's real QA knowledge, ready to assist you with frameworks, test cases, and history.
                        </p>
                        
                        {/* Suggestion Chips */}
                        <div className="flex flex-wrap gap-3 w-full">
                            <button onClick={() => handleSend("What are the test cases for user checkout?")} className="px-5 py-2.5 rounded-full border border-gray-200 bg-white/50 text-[13px] text-gray-600 hover:border-orange-300 hover:text-orange-600 transition-all shadow-sm">What are the test cases for user checkout?</button>
                            <button onClick={() => handleSend("Why did Jenkins build #4504 fail?")} className="px-5 py-2.5 rounded-full border border-gray-200 bg-white/50 text-[13px] text-gray-600 hover:border-orange-300 hover:text-orange-600 transition-all shadow-sm">Why did Jenkins build #4504 fail?</button>
                            <button onClick={() => handleSend("Summarize the login flow PRD")} className="px-5 py-2.5 rounded-full border border-gray-200 bg-white/50 text-[13px] text-gray-600 hover:border-orange-300 hover:text-orange-600 transition-all shadow-sm">Summarize the login flow PRD</button>
                        </div>
                    </div>
                ) : (
                    <div className="w-full max-w-3xl flex flex-col space-y-10 pb-24">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} w-full`}>
                                <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'bg-[#FFFDF7] border border-[#F0EBE1] rounded-3xl rounded-tr-sm px-6 py-4 shadow-sm' : 'px-2'}`}>
                                    {msg.role === 'assistant' && (
                                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-yellow-400 to-orange-400 flex-shrink-0 mt-1 mr-5 shadow-sm opacity-90 flex items-center justify-center text-white text-[12px] font-bold">QA</div>
                                    )}
                                    <div className={`text-[15px] leading-relaxed ${msg.role === 'user' ? 'text-gray-800' : 'text-gray-800 prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-white prose-pre:border prose-pre:border-gray-200 prose-pre:text-gray-800 prose-pre:shadow-sm prose-a:text-orange-600 prose-a:no-underline hover:prose-a:underline prose-strong:font-semibold'}`}>
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
            <div className="p-6 pt-0 flex flex-col items-center w-full z-10 bg-gradient-to-t from-[#FFFEFC] via-[#FFFEFC] to-transparent">
                <div className="w-full max-w-3xl relative">
                    <div className="relative group rounded-3xl transition-all duration-300">
                        <input 
                            type="text" 
                            className="w-full bg-white backdrop-blur-md border border-gray-200 hover:border-gray-300 rounded-3xl py-4 pl-6 pr-16 text-[15px] text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-orange-500/10 focus:border-orange-300 shadow-[0_2px_15px_rgb(0,0,0,0.03)] transition-all"
                            placeholder="ask about tests, tickets, failures, the framework..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isLoading}
                        />
                            <button 
                            onClick={() => handleSend(input)}
                            disabled={isLoading || !input.trim()}
                            className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-[#F4F4F5] text-gray-500 rounded-2xl hover:bg-orange-500 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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

import React, { useState } from 'react';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const ChatBox: React.FC = () => {
    const [messages, setMessages] = useState<{role: string, content: string}[]>([
        {role: 'assistant', content: 'Hello! I am your QA Buddy. How can I assist you with the knowledge base today?'}
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSend = async () => {
        if (!input.trim()) return;
        
        const userMsg = input;
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
        <div className="flex flex-col h-full w-full">
            {/* Top Breadcrumb / Navigation */}
            <div className="h-14 border-b border-gray-100 flex items-center px-8 text-[13px] font-mono text-gray-400">
                <span>ask <span className="mx-2">&rarr;</span> hybrid search <span className="mx-2">&rarr;</span> rerank</span>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} w-full`}>
                        <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'bg-gray-50 border border-gray-100 rounded-2xl rounded-tr-sm px-6 py-4' : 'px-2'}`}>
                            {msg.role === 'assistant' && (
                                <div className="w-6 h-6 rounded-full bg-green-500 flex-shrink-0 mt-1 mr-4 shadow-sm opacity-80"></div>
                            )}
                            <div className={`text-[15px] leading-relaxed ${msg.role === 'user' ? 'text-gray-700 font-medium' : 'text-gray-800 prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-gray-100 prose-pre:text-gray-800 prose-a:text-blue-600 prose-strong:font-semibold'}`}>
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
                        <div className="w-6 h-6 rounded-full bg-green-500 flex-shrink-0 mt-1 mr-4 shadow-sm opacity-40 animate-pulse"></div>
                        <div className="text-[15px] text-gray-400 animate-pulse mt-1 font-mono text-sm">
                            searching knowledge base...
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-8 pt-2">
                <div className="relative group">
                    <input 
                        type="text" 
                        className="w-full bg-white border border-gray-200 rounded-2xl py-4 pl-6 pr-20 text-[15px] text-gray-800 placeholder-gray-400 focus:outline-none focus:border-gray-300 focus:ring-4 focus:ring-gray-50 shadow-sm transition-all"
                        placeholder="Ask QA Buddy a question..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        disabled={isLoading}
                    />
                    <button 
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-[#D95F4D] text-white rounded-xl hover:bg-[#c25141] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 ml-0.5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                    </button>
                </div>
                <div className="text-center mt-3 text-[11px] font-mono text-gray-400">
                    QA Buddy can make mistakes. Consider verifying important information.
                </div>
            </div>
        </div>
    );
};

export default ChatBox;

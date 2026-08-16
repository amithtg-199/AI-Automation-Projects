import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Paperclip } from 'lucide-react';
import { Button } from './Button';
import { useAppContext } from '../../context/AppContext';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
}

export function ChatRail({ onClose }: { onClose: () => void }) {
  const { projectName } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'agent', content: 'Hello! I am the STLC Orchestrator. Select a tool below or ask me a question.' }
  ]);
  const [input, setInput] = useState('');
  const [selectedTool, setSelectedTool] = useState('Smart Routing');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() && !loading) return;
    
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    let tool = undefined;
    if (selectedTool === 'UI Automation Agent') tool = 'ui_automation';
    if (selectedTool === 'API Automation Agent') tool = 'api_automation';

    try {
      const res = await fetch('/api/orchestrator/message', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('stlc_token')}`
        },
        body: JSON.stringify({
          thread_id: 'default-thread',
          project_name: projectName || 'default',
          message: userMsg.content,
          selected_tool: tool
        })
      });
      
      const data = await res.json();
      
      // If interrupt is returned, it will be handled here
      if (data.response?.startsWith("PENDING_REVIEW:")) {
        // We will trigger a ReviewModal event or global state, for now just show text
        setMessages(prev => [...prev, { 
          id: Date.now().toString(), 
          role: 'agent', 
          content: 'Please review the detected API configuration before I proceed with generation (Review Modal opens in a full implementation).'
        }]);
        
        // Dispatch an event so AppShell can open the ReviewModal
        window.dispatchEvent(new CustomEvent('open-review-modal', { 
            detail: JSON.parse(data.response.replace("PENDING_REVIEW:", "").replace(/'/g, '"') || "[]") 
        }));
      } else {
        setMessages(prev => [...prev, { id: Date.now().toString(), role: 'agent', content: data.response || "No response" }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'agent', content: "Error connecting to orchestrator." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <aside className="w-[450px] border-l border-border bg-elevated flex flex-col shrink-0 transition-all duration-300">
      <div className="flex h-14 items-center justify-between border-b border-border px-4 shrink-0">
        <h3 className="font-semibold flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Orchestrator
        </h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-5 w-5 text-secondary" />
        </Button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(msg => (
          <div key={msg.id} className={`flex flex-col items-${msg.role === 'user' ? 'end' : 'start'} gap-1`}>
            <span className="text-xs text-secondary mx-2">{msg.role === 'user' ? 'You' : 'Agent'}</span>
            <div className={`p-3 rounded-lg text-sm shadow-sm max-w-[90%] whitespace-pre-wrap ${
              msg.role === 'user' 
                ? 'bg-primary text-white rounded-tr-none' 
                : 'bg-card border border-border rounded-tl-none'
            }`}>
              {(msg.content.includes("FLAKY_ALERT: Proposal") || msg.content.includes("DEBUG_ALERT: Proposal")) ? (
                <div className="space-y-3">
                  <div className="font-semibold text-warning">
                    {msg.content.includes("FLAKY_ALERT") ? "⚠️ Flaky Test Proposal Detected" : "🐞 Debugging Proposal Detected"}
                  </div>
                  <div className="text-xs font-mono bg-elevated p-2 rounded max-h-40 overflow-y-auto">
                    {msg.content.includes("FLAKY_ALERT") 
                      ? msg.content.split("FLAKY_ALERT: Proposal")[1].trim() 
                      : msg.content.split("DEBUG_ALERT: Proposal")[1].trim()}
                  </div>
                  <div className="flex gap-2 pt-2 border-t border-border">
                    <Button size="sm" onClick={() => {setInput("Approve"); handleSend();}} className="bg-success text-white">Approve</Button>
                    <Button size="sm" variant="secondary" onClick={() => {setInput("Decline"); handleSend();}}>Decline</Button>
                    <Button size="sm" variant="outline" onClick={() => {setInput("Implement: "); }}>Implement Custom</Button>
                  </div>
                </div>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex flex-col items-start gap-1">
            <span className="text-xs text-secondary mx-2">Agent</span>
            <div className="bg-card border border-border p-3 rounded-lg rounded-tl-none text-sm shadow-sm">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="p-4 border-t border-border bg-card shrink-0">
        <div className="flex gap-2 mb-3">
          <select 
            value={selectedTool}
            onChange={(e) => setSelectedTool(e.target.value)}
            className="bg-main border border-border text-xs rounded px-2 py-1 flex-1 focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option>Smart Routing</option>
            <option>UI Automation Agent</option>
            <option>API Automation Agent</option>
          </select>
        </div>
        <div className="relative">
          <textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={selectedTool === 'API Automation Agent' ? "Paste curl, Swagger URL, or requirements..." : "Ask orchestrator..."}
            className="w-full bg-main border border-border rounded-md pl-3 pr-20 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none min-h-[60px] max-h-48"
            rows={3}
          />
          <div className="absolute right-2 bottom-2 flex gap-1">
            {selectedTool === 'API Automation Agent' && (
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" title="Upload Collection.json">
                <Paperclip className="h-4 w-4" />
              </Button>
            )}
            <Button size="sm" className="h-7 w-7 p-0" onClick={handleSend} disabled={loading || !input.trim()}>
              <Send className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>
    </aside>
  );
}

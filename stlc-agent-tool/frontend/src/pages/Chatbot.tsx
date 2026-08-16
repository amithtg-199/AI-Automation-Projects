import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, MessageSquare } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useAppContext } from '../context/AppContext';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export function Chatbot() {
  const { projectName } = useAppContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !projectName) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/orchestrator/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('stlc_token')}`
        },
        body: JSON.stringify({
          thread_id: 'chatbot-session-1', // Simplified for demo
          project_name: projectName,
          message: userMessage.content,
          selected_tool: 'chat'
        })
      });

      if (res.ok) {
        const data = await res.json();
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.response || "No response received."
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const err = await res.json();
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Error: ${err.detail || 'Failed to communicate with agent.'}`
        }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Error: Could not connect to the orchestrator.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-4xl mx-auto space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <MessageSquare className="h-6 w-6 text-primary" />
          Agent Chatbot ({projectName})
        </h1>
        <p className="text-secondary mt-1 text-sm">
          Chat with the STLC orchestration agent to generate tests, execute suites, or query knowledge.
        </p>
      </div>

      <Card className="flex-1 flex flex-col bg-card border-border overflow-hidden shadow-sm">
        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-secondary space-y-4">
              <Bot className="h-12 w-12 opacity-50" />
              <p>How can I help you test your application today?</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                  msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-main border border-border text-primary'
                }`}>
                  {msg.role === 'user' ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                </div>
                <div className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  msg.role === 'user' 
                    ? 'bg-primary text-primary-foreground rounded-tr-none' 
                    : 'bg-main border border-border text-secondary rounded-tl-none whitespace-pre-wrap'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-4">
              <div className="shrink-0 h-8 w-8 rounded-full bg-main border border-border text-primary flex items-center justify-center">
                <Bot className="h-5 w-5" />
              </div>
              <div className="bg-main border border-border rounded-lg rounded-tl-none px-4 py-3 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span className="text-sm text-secondary">Agent is thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-border bg-main">
          <div className="relative flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask the agent to generate UI tests for login, or execute API test cases..."
              className="w-full min-h-[60px] max-h-32 bg-card border border-border rounded-lg pl-4 pr-12 py-3 text-sm text-primary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-none"
              disabled={loading}
              rows={1}
            />
            <Button 
              onClick={handleSend} 
              disabled={!input.trim() || loading}
              className="absolute right-2 bottom-2 h-8 w-8 p-0 rounded-md shrink-0 flex items-center justify-center"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <div className="mt-2 text-xs text-secondary text-center">
            Shift+Enter for new line
          </div>
        </div>
      </Card>
    </div>
  );
}

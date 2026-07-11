import React from 'react';
import { Database, MessageSquareCode, Settings, Sparkles, ShieldCheck, Cpu } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, projectName, totalChunks }) {
  const tabs = [
    { id: 'workspace', label: 'Ingestion & Metadata', icon: Database },
    { id: 'chat', label: 'Retrieval & Chat Output Studio', icon: MessageSquareCode },
    { id: 'env', label: 'Environment & MCPs', icon: Settings },
  ];

  return (
    <header className="glass-panel" style={{ margin: '1.5rem', padding: '1.25rem 2rem', marginBottom: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.5rem' }}>
        
        {/* Brand & Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            background: 'var(--gradient-glow)',
            width: '48px',
            height: '48px',
            borderRadius: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-glow)'
          }}>
            <Sparkles size={26} color="white" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.03em', background: 'var(--gradient-glow)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                QA-Assistant-Chatbot
              </h1>
              <span className="badge badge-emerald animate-pulse-glow">
                <ShieldCheck size={13} /> Active & Grounded
              </span>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Enterprise Adaptive Qdrant RAG & Multi-Module Test Case Engine
            </p>
          </div>
        </div>

        {/* Project & Connection Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(15, 23, 42, 0.6)', padding: '0.5rem 1rem', borderRadius: '12px', border: '1px solid var(--card-border)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'right' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Active Collection</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--accent-primary)' }}>{projectName || 'ecommerce_test_cases'}</span>
          </div>
          <div style={{ height: '28px', width: '1px', background: 'var(--card-border)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Cpu size={18} color={totalChunks > 0 ? "#10b981" : "#f43f5e"} />
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: totalChunks > 0 ? '#34d399' : '#f43f5e' }}>
              {totalChunks > 0 ? `${totalChunks} Chunks Indexed` : '0 Chunks Indexed (Empty / Deleted)'}
            </span>
          </div>
        </div>

      </div>

      {/* Navigation Tabs */}
      <nav style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '1.25rem' }}>
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                padding: '0.65rem 1.25rem',
                borderRadius: '10px',
                border: isActive ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid transparent',
                background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                color: isActive ? '#f8fafc' : 'var(--text-secondary)',
                fontFamily: 'var(--font-heading)',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.95rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: isActive ? '0 0 15px rgba(99, 102, 241, 0.2)' : 'none'
              }}
            >
              <Icon size={18} color={isActive ? '#818cf8' : 'var(--text-muted)'} />
              {t.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}

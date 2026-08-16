import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './layout/AppShell';
import { EmptyState } from './components/ui/EmptyState';
import { LayoutDashboard, FileText, PlaySquare, BarChart2, BookOpen, Settings } from 'lucide-react';
import { Button } from './components/ui/Button';
import { RAGEval } from './pages/RAGEval';
import { TestSuites } from './pages/TestSuites';
import { Executions } from './pages/Executions';
import { KnowledgeHub } from './pages/KnowledgeHub';
import { CostAnalysis } from './pages/CostAnalysis';
import { Chatbot } from './pages/Chatbot';

import { Login } from './pages/Login';
import { AppProvider, useAppContext } from './context/AppContext';
import { Navigate } from 'react-router-dom';

import { GlobalEnv } from './pages/GlobalEnv';
import { UserManagement } from './pages/UserManagement';

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user } = useAppContext();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function StubPage({ headline, description, icon: Icon }: { headline: string, description: string, icon: any }) {
  return (
    <EmptyState
      icon={<Icon className="w-12 h-12" />}
      headline={headline}
      description={description}
      action={<Button>Generate new item</Button>}
    />
  );
}

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <AuthGuard>
              <AppShell />
            </AuthGuard>
          }>
            <Route index element={
              <StubPage 
                icon={LayoutDashboard} 
                headline="Dashboard" 
                description="Welcome to STLC Agent. The dashboard will show key metrics once you run your first test suite." 
              />
            } />
            <Route path="chat" element={<Chatbot />} />
            <Route path="eval" element={<RAGEval />} />
            <Route path="suites" element={<TestSuites />} />
            <Route path="executions" element={<Executions />} />
            <Route path="analytics" element={<CostAnalysis />} />
            <Route path="knowledge" element={<KnowledgeHub />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="settings" element={<GlobalEnv />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;

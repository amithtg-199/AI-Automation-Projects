import React, { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import {
  Bell,
  ChevronDown,
  LayoutDashboard,
  FileText,
  PlaySquare,
  BarChart2,
  BookOpen,
  Settings,
  MessageSquare,
  Send,
  X,
  Menu,
  Database,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { ChatRail } from '../components/ui/ChatRail';
import { ReviewModal } from '../components/ReviewModal';
import { useAppContext } from '../context/AppContext';

export function AppShell() {
  const { user, role, projectName, setProjectName, logout, assignedProjects, token } = useAppContext();
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [reviewData, setReviewData] = useState<any>(null);

  const [unreadCount, setUnreadCount] = useState(0);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  React.useEffect(() => {
    const handleOpenReview = (e: any) => {
      setReviewData(e.detail);
      setReviewModalOpen(true);
    };
    window.addEventListener('open-review-modal', handleOpenReview);
    return () => window.removeEventListener('open-review-modal', handleOpenReview);
  }, []);

  React.useEffect(() => {
    const checkApprovals = async () => {
      try {
        const res = await fetch('/api/approvals/pending', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUnreadCount(data.length);
        } else if (res.status === 401) {
          logout();
        }
      } catch (e) {
        // ignore
      }
    };
    checkApprovals();
    const interval = setInterval(checkApprovals, 10000);
    return () => clearInterval(interval);
  }, []);

  const userRole = role || 'Viewer';

  const navItems = [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard, roles: ['Viewer', 'Tester', 'Admin'] },
    { label: 'Chatbot', path: '/chat', icon: MessageSquare, roles: ['Viewer', 'Tester', 'Admin'] },
    { label: 'RAG Eval', path: '/eval', icon: Database, roles: ['Viewer', 'Tester', 'Admin'] },
    { label: 'Test Suites', path: '/suites', icon: FileText, roles: ['Viewer', 'Tester', 'Admin'] },
    { label: 'Executions', path: '/executions', icon: PlaySquare, roles: ['Viewer', 'Tester', 'Admin'] },
    { label: 'Cost Analysis', path: '/analytics', icon: BarChart2, roles: ['Viewer', 'Tester', 'Admin'] },
    { label: 'Knowledge Hub', path: '/knowledge', icon: BookOpen, roles: ['Viewer', 'Tester', 'Admin'] },
    { label: 'User & Project Management', path: '/users', icon: Settings, roles: ['Admin'] },
    { label: 'Global Env Settings', path: '/settings', icon: Settings, roles: ['Admin'] },
  ];

  return (
    <div className="flex h-screen w-full bg-main text-primary overflow-hidden">
      
      {/* Left Nav */}
      <nav
        className={`flex flex-col border-r border-border bg-card transition-all duration-300 ${
          navCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          {!navCollapsed && <span className="font-bold tracking-wide">STLC Agent</span>}
          <Button variant="ghost" size="sm" onClick={() => setNavCollapsed(!navCollapsed)}>
            <Menu className="h-5 w-5" />
          </Button>
        </div>
        
        <div className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-2">
            {navItems
              .filter((item) => item.roles.includes(userRole))
              .map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-primary/10 text-primary'
                          : 'text-secondary hover:bg-elevated hover:text-primary'
                      }`
                    }
                    title={navCollapsed ? item.label : undefined}
                  >
                    <item.icon className="h-5 w-5 shrink-0" />
                    {!navCollapsed && <span>{item.label}</span>}
                  </NavLink>
                </li>
              ))}
          </ul>
        </div>
      </nav>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden relative">
        
        {/* Top Bar */}
        <header className="flex h-14 items-center justify-between border-b border-border bg-card px-6 shrink-0">
          <div className="flex items-center gap-4">
            <select 
              value={projectName || ''}
              onChange={(e) => setProjectName(e.target.value)}
              className="bg-elevated border border-border text-primary px-3 py-1.5 rounded text-sm font-medium focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
            >
              {assignedProjects && assignedProjects.length > 0 ? (
                assignedProjects.map(proj => (
                  <option key={proj} value={proj}>{proj}</option>
                ))
              ) : (
                <option value="" disabled>No Projects Assigned</option>
              )}
            </select>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="h-5 w-5 text-secondary hover:text-primary" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-2 h-4 w-4 rounded-full bg-warning flex items-center justify-center text-[10px] text-black font-bold">
                  {unreadCount}
                </span>
              )}
            </Button>
            <div className="relative">
              <div 
                className="h-8 w-8 rounded-full bg-elevated flex items-center justify-center border border-border cursor-pointer group"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                title="Account Menu"
              >
                <span className="text-sm font-medium">{user ? user.substring(0,2).toUpperCase() : 'U'}</span>
              </div>
              
              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-md shadow-lg z-50 overflow-hidden">
                  <div className="px-4 py-3 border-b border-border">
                    <p className="text-sm text-primary truncate font-medium">{user}</p>
                    <p className="text-xs text-secondary truncate">{role}</p>
                  </div>
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        // Future implementation for changing password
                        alert('Change Password feature coming soon!');
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-secondary hover:bg-elevated hover:text-primary transition-colors"
                    >
                      Change Password
                    </button>
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        logout();
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                    >
                      Logout
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Routed Content */}
        <main className="flex-1 overflow-auto p-6 relative">
          <Outlet />
        </main>
      </div>

      {/* Docked Chat Rail */}
      {chatOpen && <ChatRail onClose={() => setChatOpen(false)} />}
      {!chatOpen && (
        <div className="absolute right-0 top-1/2 -translate-y-1/2 group z-50">
          <Button 
            onClick={() => setChatOpen(true)}
            className="rounded-r-none h-14 pl-4 pr-3 py-0 shadow-2xl border-l border-y border-border bg-primary text-white hover:bg-primary/90 flex items-center gap-2 group-hover:-translate-x-1 transition-transform"
          >
            <MessageSquare className="h-5 w-5 animate-pulse" />
            <span className="font-semibold text-sm">Agent Chat</span>
          </Button>
        </div>
      )}
      {/* Review Modal for API Generator Pause */}
      <ReviewModal 
        isOpen={reviewModalOpen} 
        onClose={() => setReviewModalOpen(false)} 
        data={reviewData} 
      />
    </div>
  );
}

import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';

interface AppContextType {
  user: string | null;
  role: 'Admin' | 'Tester' | 'Viewer' | null;
  projectName: string | null;
  assignedProjects: string[];
  login: (token: string, username: string, role: 'Admin' | 'Tester' | 'Viewer', projects: string[]) => void;
  logout: () => void;
  setProjectName: (name: string) => void;
  token: string | null;
  refreshUser: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<string | null>(localStorage.getItem('stlc_user') || null);
  const [role, setRole] = useState<'Admin' | 'Tester' | 'Viewer' | null>((localStorage.getItem('stlc_role') as any) || null);
  const [projectName, setProjectNameState] = useState<string | null>(localStorage.getItem('stlc_project') || null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('stlc_token') || null);
  const [assignedProjects, setAssignedProjects] = useState<string[]>([]);
  const [isInitializing, setIsInitializing] = useState(true);

  const login = (newToken: string, username: string, newRole: 'Admin' | 'Tester' | 'Viewer', projects: string[]) => {
    setUser(username);
    setRole(newRole);
    setToken(newToken);
    setAssignedProjects(projects);
    localStorage.setItem('stlc_user', username);
    localStorage.setItem('stlc_role', newRole);
    localStorage.setItem('stlc_token', newToken);
    
    if (projects.length > 0) {
      if (!projectName || !projects.includes(projectName)) {
        setProjectName(projects[0]);
      }
    } else {
      setProjectNameState(null);
      localStorage.removeItem('stlc_project');
    }
  };

  const logout = () => {
    setUser(null);
    setRole(null);
    setToken(null);
    setAssignedProjects([]);
    setProjectNameState(null);
    localStorage.removeItem('stlc_user');
    localStorage.removeItem('stlc_role');
    localStorage.removeItem('stlc_token');
    localStorage.removeItem('stlc_project');
  };

  const setProjectName = (name: string) => {
    setProjectNameState(name);
    localStorage.setItem('stlc_project', name);
  };

  const refreshUser = async () => {
    if (!token) return;
    
    // Demo mode — skip backend call entirely
    const isDemoMode = localStorage.getItem('stlc_demo_mode') === 'true';
    if (isDemoMode) {
      setAssignedProjects(['Test']);
      setRole('Admin');
      setUser('admin');
      if (!projectName) {
        setProjectName('Test');
      }
      return;
    }
    
    try {
      const res = await fetch('/api/users/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAssignedProjects(data.assigned_projects);
        setRole(data.role_name);
        setUser(data.username);
        
        // Auto-select first project if current is invalid
        if (data.assigned_projects.length > 0) {
          if (!projectName || !data.assigned_projects.includes(projectName)) {
            setProjectName(data.assigned_projects[0]);
          }
        }
      } else {
        logout();
      }
    } catch (e) {
      // Backend unreachable but user has a stored session — keep them logged in
      if (token && user) {
        console.warn("Backend unreachable, keeping existing session.");
        if (!assignedProjects.length) {
          setAssignedProjects(['Test']);
        }
      } else {
        console.error("Failed to refresh user", e);
      }
    }
  };

  useEffect(() => {
    if (token) {
      refreshUser().finally(() => setIsInitializing(false));
    } else {
      setIsInitializing(false);
    }
  }, [token]);

  if (isInitializing) {
    return <div className="flex h-screen w-screen items-center justify-center bg-background text-primary">Loading...</div>;
  }

  return (
    <AppContext.Provider value={{ user, role, projectName, assignedProjects, login, logout, setProjectName, token, refreshUser }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}

import React, { useState, useEffect } from 'react';
import { Users, FolderPlus, UserPlus, Link as LinkIcon, Copy, Check } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useAppContext } from '../context/AppContext';

interface User {
  username: string;
  role_name: string;
  assigned_projects: string[];
}

interface Project {
  name: string;
}

export function UserManagement() {
  const { token, role } = useAppContext();
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  // Form states
  const [newProjectName, setNewProjectName] = useState('');
  const [newUser, setNewUser] = useState({ username: '', role_name: 'Tester' });
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Assignment states
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);

  const fetchUsersAndProjects = async () => {
    if (role !== 'Admin' || !token) return;
    try {
      const [uRes, pRes] = await Promise.all([
        fetch('/api/admin/users', { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch('/api/admin/projects', { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      if (uRes.ok) setUsers((await uRes.json()).users);
      if (pRes.ok) setProjects((await pRes.json()).projects);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchUsersAndProjects();
  }, [token, role]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/admin/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ name: newProjectName })
      });
      if (res.ok) {
        setNewProjectName('');
        fetchUsersAndProjects();
        alert('Project created successfully');
      } else {
        const d = await res.json();
        alert(d.detail || 'Failed to create project');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(newUser)
      });
      const data = await res.json();
      if (res.ok) {
        setGeneratedPassword(data.temporary_password);
        setNewUser({ username: '', role_name: 'Tester' });
        fetchUsersAndProjects();
      } else {
        alert(data.detail || 'Failed to create user');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAssignProjects = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    try {
      const res = await fetch(`/api/admin/users/${selectedUser}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ projects: selectedProjects })
      });
      if (res.ok) {
        alert('Projects assigned successfully');
        fetchUsersAndProjects();
      } else {
        const d = await res.json();
        alert(d.detail || 'Failed to assign projects');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCopyPassword = () => {
    if (generatedPassword) {
      navigator.clipboard.writeText(generatedPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (role !== 'Admin') {
    return <div className="p-8 text-center text-secondary">You do not have permission to view this page.</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" />
            User & Project Management
          </h1>
          <p className="text-secondary mt-1 text-sm">
            Create projects, manage testers, and configure access controls.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Create Project */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderPlus className="h-5 w-5" />
              Create Project
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary mb-1">Project Name</label>
                <input 
                  type="text" 
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                  required
                />
              </div>
              <Button type="submit">Create Project</Button>
            </form>
          </CardContent>
        </Card>

        {/* Create User */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Create User
            </CardTitle>
          </CardHeader>
          <CardContent>
            {generatedPassword ? (
              <div className="space-y-4">
                <div className="bg-success/10 border border-success text-success p-4 rounded-md">
                  <p className="font-semibold mb-2">User Created Successfully!</p>
                  <p className="text-sm mb-4">Please copy and securely distribute this temporary password. It will not be shown again.</p>
                  <div className="flex items-center gap-2 bg-main p-2 rounded border border-border">
                    <code className="flex-1 text-primary">{generatedPassword}</code>
                    <Button variant="ghost" size="sm" onClick={handleCopyPassword}>
                      {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <Button onClick={() => setGeneratedPassword(null)} variant="outline" className="w-full">
                  Create Another User
                </Button>
              </div>
            ) : (
              <form onSubmit={handleCreateUser} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-secondary mb-1">Username</label>
                  <input 
                    type="text" 
                    value={newUser.username}
                    onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                    className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary mb-1">Role</label>
                  <select 
                    value={newUser.role_name}
                    onChange={(e) => setNewUser({...newUser, role_name: e.target.value})}
                    className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary appearance-none cursor-pointer"
                  >
                    <option value="Admin">Admin</option>
                    <option value="Tester">Tester</option>
                    <option value="Viewer">Viewer</option>
                  </select>
                </div>
                <Button type="submit">Generate User</Button>
              </form>
            )}
          </CardContent>
        </Card>

        {/* Assign Projects to User */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LinkIcon className="h-5 w-5" />
              Assign Projects to User
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAssignProjects} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-secondary mb-2">Select User</label>
                  <select 
                    value={selectedUser}
                    onChange={(e) => {
                      setSelectedUser(e.target.value);
                      const user = users.find(u => u.username === e.target.value);
                      setSelectedProjects(user ? user.assigned_projects : []);
                    }}
                    className="w-full bg-main border border-border rounded-md px-3 py-2 text-primary focus:outline-none focus:border-primary cursor-pointer"
                  >
                    <option value="">-- Choose User --</option>
                    {users.map(u => (
                      <option key={u.username} value={u.username}>{u.username} ({u.role_name})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary mb-2">Projects</label>
                  <div className="bg-main border border-border rounded-md p-4 space-y-2 max-h-48 overflow-y-auto">
                    {projects.length === 0 && <span className="text-secondary text-sm">No projects exist yet.</span>}
                    {projects.map(p => (
                      <label key={p.name} className="flex items-center gap-3 cursor-pointer">
                        <input 
                          type="checkbox" 
                          checked={selectedProjects.includes(p.name)}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedProjects([...selectedProjects, p.name]);
                            else setSelectedProjects(selectedProjects.filter(sp => sp !== p.name));
                          }}
                          className="h-4 w-4 rounded border-border text-primary focus:ring-primary bg-card"
                        />
                        <span className="text-sm font-medium">{p.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <Button type="submit" disabled={!selectedUser}>Save Assignments</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

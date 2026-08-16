import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { BookOpen, Share2, UploadCloud, File, Play } from 'lucide-react';
import { useAppContext } from '../context/AppContext';

interface Skill {
  id: string;
  project: string;
  module: string;
  use_case: string;
  card: string;
  shared_across: string[];
}

export function KnowledgeHub() {
  const { projectName, token } = useAppContext();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [ingesting, setIngesting] = useState(false);

  // MOCK DATA for rendering until backend is fully hooked up
  useEffect(() => {
    fetch('/api/knowledge-hub/skills', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Unauthorized');
        return res.json();
      })
      .then(data => {
        setSkills(data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [projectName]);

  const handleShare = async (skillId: string) => {
    // Mock sharing with another project
    const target = prompt("Enter target project name to share with (e.g., project-b):");
    if (!target) return;
    
    try {
      const res = await fetch(`/api/knowledge-hub/${skillId}/share`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ target_projects: [target] })
      });
      if (res.ok) {
        alert(`Successfully shared skill with ${target}`);
      } else {
        alert("Failed to share skill. Ensure you are an Admin.");
      }
    } catch (e) {
      alert("Error sharing skill.");
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploading(true);
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_name', projectName || '');
      
      try {
        const res = await fetch('/api/knowledge-hub/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });
        const data = await res.json();
        if (res.ok) {
          alert(data.message || `${file.name} uploaded successfully to ${projectName}.`);
        } else {
          alert(`Upload failed: ${data.detail}`);
        }
      } catch (err) {
        alert("Upload error.");
      } finally {
        setUploading(false);
      }
    }
  };

  const handleIngest = async () => {
    setIngesting(true);
    const formData = new URLSearchParams();
    formData.append('project_name', projectName || '');
    
    try {
      const res = await fetch('/api/knowledge-hub/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${token}`
        },
        body: formData.toString()
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message || `Ingestion cycle started for ${projectName}!`);
      } else {
        alert(`Ingestion failed: ${data.detail}`);
      }
    } catch (err) {
      alert("Ingestion trigger error.");
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-primary" />
            Central Knowledge Hub ({projectName})
          </h1>
          <p className="text-secondary mt-1 text-sm">
            Browse automation skills learned from approved scripts. 
            Upload API Swagger specs or PRDs to train the agents.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Upload & Ingest Panel */}
        <div className="md:col-span-1 space-y-4">
          <Card className="p-4 bg-card border border-border">
            <h3 className="font-semibold text-primary mb-3 flex items-center gap-2">
              <UploadCloud className="h-4 w-4" /> Add Context
            </h3>
            <p className="text-xs text-secondary mb-4">
              Upload Swagger JSON, OpenAPI specs, or Markdown PRDs to provide context to the agentic RAG pipeline.
            </p>
            
            <label className="flex justify-center w-full h-24 px-4 transition bg-main border-2 border-border border-dashed rounded-md appearance-none cursor-pointer hover:border-primary focus:outline-none">
                <span className="flex items-center space-x-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <span className="font-medium text-secondary">
                        {uploading ? 'Uploading...' : 'Drop files or click to browse'}
                    </span>
                </span>
                <input type="file" name="file_upload" className="hidden" onChange={handleUpload} accept=".json,.yaml,.yml,.md" />
            </label>

            <Button 
              className="w-full mt-4 bg-success text-white hover:bg-success/90" 
              onClick={handleIngest} 
              disabled={ingesting || uploading}
            >
              <Play className="h-4 w-4 mr-2" />
              {ingesting ? 'Running Ingestion...' : 'Run Ingestion Cycle'}
            </Button>
          </Card>
        </div>

        {/* Skills Grid */}
        <div className="md:col-span-2">
          <h3 className="font-semibold text-primary mb-3">Discovered Skills</h3>
          <div className="grid grid-cols-1 gap-4">
            {skills.map((skill) => (
              <Card key={skill.id} className="p-4 flex flex-col justify-between bg-card hover:bg-elevated transition-colors border border-border">
                <div>
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-primary">{skill.module} / {skill.use_case}</h3>
                      <div className="flex gap-2 mt-1">
                        <span className="text-[10px] font-mono bg-primary/20 text-primary px-1.5 py-0.5 rounded">Origin: {skill.project}</span>
                        {skill.shared_across.map(target => (
                          <span key={target} className="text-[10px] font-mono bg-success/20 text-success px-1.5 py-0.5 rounded">Shared: {target}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <p className="text-sm text-secondary whitespace-pre-wrap">{skill.card}</p>
                </div>
                
                <div className="mt-4 pt-3 border-t border-border flex justify-end">
                  <Button size="sm" variant="outline" className="flex items-center gap-1" onClick={() => handleShare(skill.id)}>
                    <Share2 className="h-3 w-3" />
                    Share to Project
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

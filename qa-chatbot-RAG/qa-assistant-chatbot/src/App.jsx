import React, { useState, useEffect } from 'react';
import './index.css';
import Header from './components/Header';
import IngestionWorkspace from './components/IngestionWorkspace';
import ChatStudio from './components/ChatStudio';
import EnvironmentTabs from './components/EnvironmentTabs';

export default function App() {
  const [activeTab, setActiveTab] = useState('workspace');
  const [projectName, setProjectName] = useState('ecommerce_test_cases');
  
  // Initialize totalChunks from localStorage or default to 0 if deleted
  const [totalChunks, setTotalChunks] = useState(() => {
    const saved = localStorage.getItem('qa_total_chunks');
    return saved !== null ? Number(saved) : 0;
  });

  const [ingestionStatus, setIngestionStatus] = useState(() => {
    const saved = localStorage.getItem('qa_total_chunks');
    return (saved !== null && Number(saved) === 0) ? 'Collection Deleted / Empty (0 Chunks)' : 'Ready / Checked Live';
  });

  // Check live Qdrant status on mount and when projectName changes
  const syncLiveQdrantStatus = async (customName = null) => {
    const target = customName || projectName;
    try {
      const res = await fetch(`http://localhost:6333/collections/${target}`);
      if (!res.ok || res.status === 404) {
        // Collection does not exist or was deleted in Qdrant
        setTotalChunks(0);
        setIngestionStatus('Collection Deleted / Not Found in Qdrant');
        localStorage.setItem('qa_total_chunks', '0');
      } else {
        const data = await res.json();
        if (data && data.result && typeof data.result.points_count === 'number') {
          const count = data.result.points_count;
          setTotalChunks(count);
          setIngestionStatus(count > 0 ? 'Indexed & Active' : 'Collection Empty (0 Chunks)');
          localStorage.setItem('qa_total_chunks', String(count));
        }
      }
    } catch (err) {
      // If direct browser fetch blocked by CORS or Qdrant offline, sync with localStorage
      const saved = localStorage.getItem('qa_total_chunks');
      const val = saved !== null ? Number(saved) : 0;
      setTotalChunks(val);
      setIngestionStatus(val > 0 ? 'Indexed & Active' : 'Collection Deleted / Empty (0 Chunks)');
    }
  };

  useEffect(() => {
    syncLiveQdrantStatus();
  }, [projectName]);

  return (
    <div className="min-h-screen pb-16">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        projectName={projectName}
        totalChunks={totalChunks}
        syncLiveQdrantStatus={syncLiveQdrantStatus}
      />

      <main style={{ maxWidth: '1440px', margin: '0 auto' }}>
        {activeTab === 'workspace' && (
          <IngestionWorkspace
            projectName={projectName}
            setProjectName={setProjectName}
            totalChunks={totalChunks}
            setTotalChunks={setTotalChunks}
            ingestionStatus={ingestionStatus}
            setIngestionStatus={setIngestionStatus}
            syncLiveQdrantStatus={syncLiveQdrantStatus}
          />
        )}

        {activeTab === 'chat' && (
          <ChatStudio
            projectName={projectName}
            totalChunks={totalChunks}
          />
        )}

        {activeTab === 'env' && (
          <EnvironmentTabs projectName={projectName} />
        )}
      </main>
    </div>
  );
}

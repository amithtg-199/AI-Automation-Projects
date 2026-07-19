// import React from 'react';
import ChatBox from './components/ChatBox';
import ConfigPanel from './components/ConfigPanel';

function App() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#F8F6F0]">
      {/* Left Sidebar - Fixed Width */}
      <div className="w-[340px] flex-shrink-0 h-full border-r border-[#E5E0D8]">
        <ConfigPanel />
      </div>

      {/* Main Chat Area - Takes remaining space */}
      <main className="flex-1 h-full bg-white flex flex-col relative">
        <ChatBox />
      </main>
    </div>
  );
}

export default App;

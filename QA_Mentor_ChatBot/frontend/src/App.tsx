// import React from 'react';
import ChatBox from './components/ChatBox';
import ConfigPanel from './components/ConfigPanel';
import InfoPanel from './components/InfoPanel';

function App() {
  return (
    <div className="h-screen w-full bg-[#FFFEFC] text-gray-800 font-sans overflow-hidden">
      {/* 
        3-Column Layout on Desktop:
        Left: Config Panel (300px)
        Center: Chat Interface (Fluid)
        Right: Info Panel (320px)
      */}
      <div className="grid lg:grid-cols-[300px_1fr_320px] w-full h-full">
        {/* Left Sidebar - Hidden on mobile/tablet by default */}
        <div className="hidden lg:block h-full border-r border-[#F0EBE1] bg-[#FFFDF7] overflow-y-auto custom-scrollbar">
          <ConfigPanel />
        </div>

        {/* Center Main Chat */}
        <div className="h-full bg-[#FFFEFC] relative shadow-[0_0_40px_rgba(0,0,0,0.03)] z-10 flex flex-col overflow-hidden">
          <ChatBox />
        </div>

        {/* Right Info Sidebar - Hidden on mobile/tablet */}
        <div className="hidden lg:block h-full overflow-y-auto custom-scrollbar">
          <InfoPanel />
        </div>
      </div>
    </div>
  );
}

export default App;

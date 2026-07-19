import React from 'react';

const InfoPanel: React.FC = () => {
    return (
        <div className="flex flex-col h-full w-full py-8 px-6 overflow-y-auto bg-[#FFFDF7] border-l border-[#F0EBE1]">
            <h2 className="text-[10px] font-mono tracking-[0.2em] text-gray-400 uppercase mb-8">
                How your answer is fetched
            </h2>
            
            <div className="flex flex-col gap-8 mb-12">
                {/* Step 1 */}
                <div className="flex gap-4">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-yellow-400/50 flex items-center justify-center text-yellow-600 text-[11px] font-mono shadow-sm bg-white">1</div>
                    <div>
                        <h3 className="text-[13px] font-semibold text-gray-800 mb-1">Understand</h3>
                        <p className="text-[12px] text-gray-500 leading-relaxed">question is condensed and rewritten using GraphRAG relationships.</p>
                    </div>
                </div>
                {/* Step 2 */}
                <div className="flex gap-4">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-yellow-400/50 flex items-center justify-center text-yellow-600 text-[11px] font-mono shadow-sm bg-white">2</div>
                    <div>
                        <h3 className="text-[13px] font-semibold text-gray-800 mb-1">Hybrid search</h3>
                        <p className="text-[12px] text-gray-500 leading-relaxed">meaning (dense) + exact keywords (BM25) across sources.</p>
                    </div>
                </div>
                {/* Step 3 */}
                <div className="flex gap-4">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-yellow-400/50 flex items-center justify-center text-yellow-600 text-[11px] font-mono shadow-sm bg-white">3</div>
                    <div>
                        <h3 className="text-[13px] font-semibold text-gray-800 mb-1">Fuse & rerank</h3>
                        <p className="text-[12px] text-gray-500 leading-relaxed">result lists merge, cross-encoder keeps the top chunks.</p>
                    </div>
                </div>
                {/* Step 4 */}
                <div className="flex gap-4">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full border border-yellow-400/50 flex items-center justify-center text-yellow-600 text-[11px] font-mono shadow-sm bg-white">4</div>
                    <div>
                        <h3 className="text-[13px] font-semibold text-gray-800 mb-1">Cited answer</h3>
                        <p className="text-[12px] text-gray-500 leading-relaxed">Mistral AI answers citing exact file:line or ticket.</p>
                    </div>
                </div>
            </div>

            <h2 className="text-[10px] font-mono tracking-[0.2em] text-gray-400 uppercase mb-6 pt-6 border-t border-[#F0EBE1]">
                Knowledge Map
            </h2>
            
            {/* Visual Knowledge Map using Tailwind */}
            <div className="flex flex-col items-center w-full bg-white rounded-2xl p-4 border border-[#F0EBE1] shadow-sm relative">
                {/* User */}
                <div className="px-3 py-1.5 bg-gray-50 rounded-lg text-[11px] font-medium text-gray-600 z-10 border border-gray-200">
                    User Query
                </div>
                
                {/* Arrow */}
                <div className="w-px h-6 bg-gradient-to-b from-gray-200 to-yellow-300 -my-1 z-0"></div>
                
                {/* FastAPI */}
                <div className="w-full px-3 py-2 bg-[#FFFDF7] rounded-xl text-[11px] font-medium text-gray-700 text-center z-10 border border-yellow-200 shadow-sm">
                    FastAPI Orchestrator
                </div>
                
                {/* Split Arrows */}
                <div className="flex w-full justify-between px-6 -my-1 z-0">
                    <div className="w-px h-6 bg-gradient-to-b from-yellow-300 to-blue-300 transform -rotate-[25deg] origin-top"></div>
                    <div className="w-px h-6 bg-gradient-to-b from-yellow-300 to-green-300 transform rotate-[25deg] origin-top"></div>
                </div>
                
                {/* Databases */}
                <div className="flex w-full justify-between gap-2 z-10 mt-2">
                    <div className="flex-1 px-2 py-2 bg-blue-50/50 rounded-xl text-[10px] font-medium text-blue-700 text-center border border-blue-100">
                        Neo4j (Graph)
                    </div>
                    <div className="flex-1 px-2 py-2 bg-green-50/50 rounded-xl text-[10px] font-medium text-green-700 text-center border border-green-100">
                        Qdrant (Vector)
                    </div>
                </div>

                {/* Arrow Down */}
                <div className="flex w-full justify-center -my-1 z-0 mt-1">
                    <div className="w-px h-6 bg-gradient-to-b from-gray-200 to-purple-300"></div>
                </div>
                
                {/* LLM */}
                <div className="px-4 py-2 bg-purple-50 rounded-xl text-[11px] font-medium text-purple-700 text-center z-10 border border-purple-200 shadow-sm mt-1">
                    Mistral AI
                </div>
            </div>
        </div>
    );
};

export default InfoPanel;

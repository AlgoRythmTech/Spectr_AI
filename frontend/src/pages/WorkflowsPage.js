import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Workflow, Play, Loader2, CheckCircle2, ChevronRight, FileText } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

export default function WorkflowsPage() {
  const { getToken } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [initialInput, setInitialInput] = useState('');
  
  const [activeChain, setActiveChain] = useState(null);
  const [chainLoading, setChainLoading] = useState(false);
  const [editedOutput, setEditedOutput] = useState('');

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${API}/workflows/chain/templates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTemplates(data.templates || []);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleStartChain = async () => {
    if (!selectedTemplate || !initialInput.trim()) return;
    setChainLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API}/workflows/chain/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ chain_type: selectedTemplate.id, initial_input: initialInput })
      });
      if (res.ok) {
        const data = await res.json();
        setActiveChain(data);
        setEditedOutput(data.step_output);
      }
    } catch (err) {
      console.error(err);
    }
    setChainLoading(false);
  };

  const handleNextStep = async () => {
    if (!activeChain) return;
    setChainLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API}/workflows/chain/next`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ chain_id: activeChain.chain_id, edited_output: editedOutput })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'completed') {
           setActiveChain(data);
        } else {
           setActiveChain(data);
           setEditedOutput(data.step_output);
        }
      }
    } catch (err) {
      console.error(err);
    }
    setChainLoading(false);
  };

  const resetWorkflow = () => {
    setSelectedTemplate(null);
    setInitialInput('');
    setActiveChain(null);
    setEditedOutput('');
  };

  return (
    <div className="flex flex-col h-full bg-[#FAFAFA] font-sans">
      <div className="h-16 border-b border-[#E5E7EB] px-8 flex items-center shrink-0 bg-[#FFFFFF] justify-between">
        <div className="flex items-center">
            <Workflow className="w-5 h-5 text-[#000] mr-3" />
            <h1 className="text-[15px] font-semibold text-[#000] tracking-tight">Agentic Workflows</h1>
        </div>
        {activeChain && (
            <button onClick={resetWorkflow} className="text-[13px] font-semibold text-[#4B5563] hover:text-[#000] transition-colors">
                New Workflow
            </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-[1000px] mx-auto">
          
          {loading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-[#000]" /></div>
          ) : !activeChain ? (
            <div>
              <div className="mb-10 text-center">
                <h2 className="text-[32px] font-bold text-[#111827] mb-4 tracking-[-0.02em]">Select a Workflow</h2>
                <p className="text-[15px] text-[#4B5563] max-w-[600px] mx-auto">
                  Multi-step execution chains where the output of each AI reasoning step feeds into the next, mimicking a human associate's workflow.
                </p>
              </div>

              {!selectedTemplate ? (
                  <div className="grid grid-cols-2 gap-6">
                    {templates.map(t => (
                        <div 
                           key={t.id} 
                           onClick={() => setSelectedTemplate(t)}
                           className="bg-[#FFFFFF] border border-[#E5E7EB] p-6 rounded-[12px] cursor-pointer hover:border-[#000] hover:shadow-md transition-all group"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-[#F3F4F6] rounded-[8px] group-hover:bg-[#000] group-hover:text-white transition-colors">
                                    <FileText className="w-5 h-5" />
                                </div>
                                <span className="text-[12px] font-bold text-[#6B7280] uppercase tracking-wider bg-[#F9FAFB] px-2 py-1 rounded">
                                    {t.steps} Steps
                                </span>
                            </div>
                            <h3 className="text-[18px] font-bold text-[#111827] mb-2">{t.name}</h3>
                            <p className="text-[13px] text-[#4B5563] leading-relaxed">{t.description}</p>
                        </div>
                    ))}
                  </div>
              ) : (
                  <div className="bg-[#FFFFFF] border border-[#E5E7EB] p-8 rounded-[16px] shadow-sm">
                      <button onClick={() => setSelectedTemplate(null)} className="text-[12px] font-bold text-[#4B5563] uppercase tracking-wider hover:text-[#000] mb-6 flex items-center gap-1">
                          ← Back to templates
                      </button>
                      <h3 className="text-[24px] font-bold text-[#111827] mb-2">{selectedTemplate.name}</h3>
                      <p className="text-[14px] text-[#4B5563] mb-8">{selectedTemplate.description}</p>
                      
                      <label className="block text-[13px] font-bold text-[#111827] mb-2 uppercase tracking-wide">Initial Input / Context</label>
                      <textarea
                        value={initialInput}
                        onChange={e => setInitialInput(e.target.value)}
                        placeholder="Paste the initial facts, contract text, or notice here..."
                        className="w-full h-48 p-4 text-[14.5px] border border-[#D1D5DB] rounded-[8px] mb-4 focus:outline-none focus:border-[#000] focus:ring-1 focus:ring-[#000] resize-none font-mono"
                      />
                      <button
                        onClick={handleStartChain}
                        disabled={!initialInput.trim() || chainLoading}
                        className="w-full bg-[#000] text-white py-4 rounded-[8px] font-semibold flex items-center justify-center gap-2 hover:bg-[#1f2937] transition-all disabled:opacity-50"
                      >
                         {chainLoading ? (
                             <><Loader2 className="w-5 h-5 animate-spin" /> Initializing Chain...</>
                         ) : (
                             <><Play className="w-5 h-5 fill-current" /> Next: Execute Step 1</>
                         )}
                      </button>
                  </div>
              )}
            </div>
          ) : activeChain.status === 'completed' ? (
             <div className="bg-[#FFFFFF] border border-[#10B981] p-8 rounded-[16px] shadow-sm text-center">
                 <CheckCircle2 className="w-16 h-16 text-[#10B981] mx-auto mb-4" />
                 <h2 className="text-[24px] font-bold text-[#111827] mb-2">Workflow Completed</h2>
                 <p className="text-[15px] text-[#4B5563] mb-8">All steps in the chain have been successfully executed.</p>
                 
                 <div className="text-left bg-[#FAFAFA] border border-[#E5E7EB] rounded-[12px] p-6 mb-8 overflow-auto max-h-[600px]">
                     {Object.entries(activeChain.all_outputs).map(([stepId, output], idx) => (
                         <div key={stepId} className="mb-8 last:mb-0">
                             <h4 className="text-[12px] font-bold text-[#6B7280] uppercase tracking-wider mb-3">Step {idx + 1}: {stepId}</h4>
                             <div className="text-[14.5px] text-[#111827] leading-relaxed whitespace-pre-wrap font-serif" dangerouslySetInnerHTML={{ __html: output }} />
                             {idx < Object.entries(activeChain.all_outputs).length - 1 && <hr className="my-6 border-[#E5E7EB]" />}
                         </div>
                     ))}
                 </div>
                 
                 <button onClick={resetWorkflow} className="bg-[#000] text-white px-8 py-3 rounded-[8px] font-semibold">Start New Workflow</button>
             </div>
          ) : (
             <div className="flex gap-8">
                 {/* Sidebar progress */}
                 <div className="w-64 shrink-0">
                     <div className="bg-[#FFFFFF] border border-[#E5E7EB] rounded-[12px] p-5 sticky top-8">
                         <h3 className="text-[14px] font-bold text-[#111827] mb-4">Chain Progress</h3>
                         <div className="space-y-4">
                             {Array.from({length: activeChain.total_steps}).map((_, i) => (
                                 <div key={i} className={`flex items-center gap-3 ${i === activeChain.current_step ? 'opacity-100' : 'opacity-40'}`}>
                                     <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold ${
                                         i < activeChain.current_step ? 'bg-[#10B981] text-white' :
                                         i === activeChain.current_step ? 'bg-[#000] text-white' : 'bg-[#E5E7EB] text-[#6B7280]'
                                     }`}>
                                         {i < activeChain.current_step ? '✓' : i + 1}
                                     </div>
                                     <span className="text-[13px] font-bold">
                                         {i === activeChain.current_step ? activeChain.step_title : `Step ${i + 1}`}
                                     </span>
                                 </div>
                             ))}
                         </div>
                     </div>
                 </div>

                 {/* Main content */}
                 <div className="flex-1 bg-[#FFFFFF] border border-[#E5E7EB] p-8 rounded-[16px] shadow-sm">
                     <div className="flex justify-between items-center mb-6">
                         <h3 className="text-[20px] font-bold text-[#111827]">Step {activeChain.current_step + 1}: {activeChain.step_title}</h3>
                         <span className="text-[11px] font-bold text-[#1D4ED8] bg-[#DBEAFE] px-2 py-1 rounded tracking-widest uppercase">Awaiting human review</span>
                     </div>
                     
                     <p className="text-[14px] text-[#4B5563] mb-4">Review the AI's output for this step. You can edit the text directly before it is passed as context to the next step.</p>
                     
                     <textarea
                        value={editedOutput}
                        onChange={e => setEditedOutput(e.target.value)}
                        className="w-full h-[400px] p-5 text-[14.5px] border border-[#D1D5DB] rounded-[8px] mb-6 focus:outline-none focus:border-[#000] focus:ring-1 focus:ring-[#000] leading-relaxed resize-y font-serif bg-[#FAFAFA]"
                     />
                     
                     <button
                        onClick={handleNextStep}
                        disabled={chainLoading || !editedOutput.trim()}
                        className="w-full bg-[#000] text-white py-4 rounded-[8px] font-semibold flex items-center justify-center gap-2 hover:bg-[#1f2937] transition-all disabled:opacity-50"
                     >
                        {chainLoading ? (
                             <><Loader2 className="w-5 h-5 animate-spin" /> Processing Next Step...</>
                        ) : activeChain.next_step ? (
                             <>Approve & Run Next: {activeChain.next_step} <ChevronRight className="w-5 h-5" /></>
                        ) : (
                             <><CheckCircle2 className="w-5 h-5" /> Finalize Workflow</>
                        )}
                     </button>
                 </div>
             </div>
          )}

        </div>
      </div>
    </div>
  );
}

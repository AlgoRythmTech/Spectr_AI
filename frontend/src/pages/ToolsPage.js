import React from 'react';
import { useSearchParams } from 'react-router-dom';
import TDSClassifierPage from './TDSClassifierPage';
import PenaltyCalculatorPage from './PenaltyCalculatorPage';
import ReconcilerPage from './ReconcilerPage';
import NoticeReplyPage from './NoticeReplyPage';
import NoticeCheckPage from './NoticeCheckPage';
import SectionMapperPage from './SectionMapperPage';
import TallyImportPage from './TallyImportPage';

const TOOLS = [
  { id: 'tds', label: 'TDS', component: TDSClassifierPage },
  { id: 'penalty', label: 'Penalties', component: PenaltyCalculatorPage },
  { id: 'reconciler', label: 'Reconciler', component: ReconcilerPage },
  { id: 'notice-reply', label: 'Notice Reply', component: NoticeReplyPage },
  { id: 'notice-check', label: 'Notice Check', component: NoticeCheckPage },
  { id: 'mapper', label: 'Section Mapper', component: SectionMapperPage },
  { id: 'tally', label: 'Tally Import', component: TallyImportPage },
];

export default function ToolsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeId = searchParams.get('tab') || 'tds';
  const activeTool = TOOLS.find(t => t.id === activeId) || TOOLS[0];
  const ActiveComponent = activeTool.component;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        display: 'flex', gap: 0, borderBottom: '1px solid #E5E5E5',
        padding: '0 32px', flexShrink: 0,
      }}>
        {TOOLS.map(tool => {
          const active = tool.id === activeTool.id;
          return (
            <button
              key={tool.id}
              onClick={() => setSearchParams({ tab: tool.id })}
              style={{
                padding: '14px 18px', fontSize: 13, fontWeight: active ? 600 : 400,
                color: active ? '#000' : '#999',
                background: 'none', border: 'none', cursor: 'pointer',
                borderBottom: active ? '2px solid #000' : '2px solid transparent',
                transition: 'color 0.15s', marginBottom: -1,
                fontFamily: "'Inter', sans-serif",
              }}
            >
              {tool.label}
            </button>
          );
        })}
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ActiveComponent />
      </div>
    </div>
  );
}

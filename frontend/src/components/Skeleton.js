import React from 'react';

/**
 * Skeleton — shimmer loading block. Used to replace "Loading..." text with
 * visual placeholders that hint at the shape of the content coming next.
 *
 *   <Skeleton w="70%" h={14} />            → single bar
 *   <Skeleton.List rows={5} />             → pre-composed list of rows
 *   <Skeleton.ChatRow />                   → matches PreviousChatsSidebar row
 */

function Base({ w = '100%', h = 12, r = 6, style = {} }) {
  return (
    <div style={{
      width: w, height: h, borderRadius: r,
      background: 'linear-gradient(90deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.085) 50%, rgba(0,0,0,0.05) 75%)',
      backgroundSize: '200% 100%',
      animation: 'spectr-skel-shimmer 1.4s linear infinite',
      ...style,
    }} />
  );
}

function SkeletonList({ rows = 4, gap = 10, ...props }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Base key={i} {...props} />
      ))}
    </div>
  );
}

function SkeletonChatRow() {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9, padding: '8px 10px' }}>
      <Base w={13} h={13} r="50%" style={{ marginTop: 3, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 5 }}>
        <Base w="88%" h={10} />
        <Base w="60%" h={8} />
      </div>
    </div>
  );
}

const Skeleton = Object.assign(Base, {
  List: SkeletonList,
  ChatRow: SkeletonChatRow,
});

export default Skeleton;

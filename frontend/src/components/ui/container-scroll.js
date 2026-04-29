import React, { useRef, useState, useEffect } from 'react';
import { useScroll, useTransform, motion } from 'framer-motion';

export function ContainerScroll({ titleComponent, children }) {
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: containerRef });
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const scaleDimensions = isMobile ? [0.7, 0.9] : [1.05, 1];
  const rotate = useTransform(scrollYProgress, [0, 1], [20, 0]);
  const scale = useTransform(scrollYProgress, [0, 1], scaleDimensions);
  const translate = useTransform(scrollYProgress, [0, 1], [0, -100]);

  return (
    <div
      ref={containerRef}
      style={{
        height: isMobile ? '60rem' : '80rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        padding: isMobile ? '8px' : '80px',
      }}
    >
      <div
        style={{
          padding: isMobile ? '40px 0' : '160px 0',
          width: '100%',
          position: 'relative',
          perspective: '1000px',
        }}
      >
        <ScrollHeader translate={translate} titleComponent={titleComponent} />
        <ScrollCard rotate={rotate} translate={translate} scale={scale}>
          {children}
        </ScrollCard>
      </div>
    </div>
  );
}

function ScrollHeader({ translate, titleComponent }) {
  return (
    <motion.div
      style={{
        translateY: translate,
        maxWidth: '1024px',
        margin: '0 auto',
        textAlign: 'center',
      }}
    >
      {titleComponent}
    </motion.div>
  );
}

function ScrollCard({ rotate, scale, children }) {
  return (
    <motion.div
      style={{
        rotateX: rotate,
        scale,
        boxShadow:
          '0 0 #0000004d, 0 9px 20px #0000004a, 0 37px 37px #00000042, 0 84px 50px #00000026, 0 149px 60px #0000000a, 0 233px 65px #00000003',
        maxWidth: '1024px',
        marginTop: '-48px',
        marginLeft: 'auto',
        marginRight: 'auto',
        width: '100%',
        border: '4px solid #6C6C6C',
        padding: window.innerWidth <= 768 ? '8px' : '24px',
        background: '#222222',
        borderRadius: '30px',
      }}
    >
      <div
        style={{
          height: '100%',
          width: '100%',
          overflow: 'hidden',
          borderRadius: '16px',
          background: '#111111',
          minHeight: window.innerWidth <= 768 ? '30rem' : '40rem',
        }}
      >
        {children}
      </div>
    </motion.div>
  );
}

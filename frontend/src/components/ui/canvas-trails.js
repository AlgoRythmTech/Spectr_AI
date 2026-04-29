import { useEffect, useRef } from 'react';

/**
 * Rainbow Canvas Trails — mouse/touch-following animated lines.
 * Adapted from TSX/Tailwind to plain JS/inline styles for CRA.
 */
export function CanvasTrails({ style, className }) {
  const canvasRef = useRef(null);
  const runningRef = useRef(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const E = {
      friction: 0.5,
      trails: 80,
      size: 50,
      dampening: 0.025,
      tension: 0.99,
    };

    let pos = { x: 0, y: 0 };
    let lines = [];
    let phase = Math.random() * 2 * Math.PI;
    let offset = 285;
    let amplitude = 85;
    let frequency = 0.0015;
    let hue = 0;
    let animId;

    function Node() {
      this.x = 0;
      this.y = 0;
      this.vx = 0;
      this.vy = 0;
    }

    function createLine(spring) {
      const nodes = [];
      for (let i = 0; i < E.size; i++) {
        const node = new Node();
        node.x = pos.x;
        node.y = pos.y;
        nodes.push(node);
      }
      return {
        spring: spring + 0.1 * Math.random() - 0.05,
        friction: E.friction + 0.01 * Math.random() - 0.005,
        nodes,
      };
    }

    function updateLine(line) {
      let sp = line.spring;
      let t = line.nodes[0];
      t.vx += (pos.x - t.x) * sp;
      t.vy += (pos.y - t.y) * sp;
      for (let i = 0; i < line.nodes.length; i++) {
        t = line.nodes[i];
        if (i > 0) {
          const prev = line.nodes[i - 1];
          t.vx += (prev.x - t.x) * sp;
          t.vy += (prev.y - t.y) * sp;
          t.vx += prev.vx * E.dampening;
          t.vy += prev.vy * E.dampening;
        }
        t.vx *= line.friction;
        t.vy *= line.friction;
        t.x += t.vx;
        t.y += t.vy;
        sp *= E.tension;
      }
    }

    function drawLine(line) {
      let n0x = line.nodes[0].x;
      let n0y = line.nodes[0].y;
      ctx.beginPath();
      ctx.moveTo(n0x, n0y);
      let a;
      for (a = 1; a < line.nodes.length - 2; a++) {
        const e = line.nodes[a];
        const t = line.nodes[a + 1];
        const mx = 0.5 * (e.x + t.x);
        const my = 0.5 * (e.y + t.y);
        ctx.quadraticCurveTo(e.x, e.y, mx, my);
      }
      const e2 = line.nodes[a];
      const t2 = line.nodes[a + 1];
      ctx.quadraticCurveTo(e2.x, e2.y, t2.x, t2.y);
      ctx.stroke();
      ctx.closePath();
    }

    function initLines() {
      lines = [];
      for (let i = 0; i < E.trails; i++) {
        lines.push(createLine(0.45 + (i / E.trails) * 0.025));
      }
    }

    function resizeCanvas() {
      canvas.width = canvas.parentElement ? canvas.parentElement.clientWidth : window.innerWidth;
      canvas.height = canvas.parentElement ? canvas.parentElement.clientHeight : window.innerHeight;
    }

    function render() {
      if (!runningRef.current) return;
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.globalCompositeOperation = 'lighter';

      phase += frequency;
      hue = offset + Math.sin(phase) * amplitude;
      ctx.strokeStyle = `hsla(${Math.round(hue)},100%,50%,0.025)`;
      ctx.lineWidth = 10;

      for (let i = 0; i < lines.length; i++) {
        updateLine(lines[i]);
        drawLine(lines[i]);
      }
      animId = requestAnimationFrame(render);
    }

    let started = false;

    function handleMove(e) {
      if (e.touches) {
        pos.x = e.touches[0].clientX;
        pos.y = e.touches[0].clientY - (canvas.getBoundingClientRect().top);
      } else {
        const rect = canvas.getBoundingClientRect();
        pos.x = e.clientX - rect.left;
        pos.y = e.clientY - rect.top;
      }
      if (!started) {
        started = true;
        initLines();
        render();
      }
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Listen on the parent or window for mouse/touch
    const target = canvas.parentElement || window;
    target.addEventListener('mousemove', handleMove);
    target.addEventListener('touchmove', handleMove);
    target.addEventListener('touchstart', handleMove);

    return () => {
      runningRef.current = false;
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resizeCanvas);
      target.removeEventListener('mousemove', handleMove);
      target.removeEventListener('touchmove', handleMove);
      target.removeEventListener('touchstart', handleMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        display: 'block',
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        ...style,
      }}
    />
  );
}

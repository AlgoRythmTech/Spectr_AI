import { useEffect, useRef } from 'react';

/**
 * Beam Canvas — animated beam/ray lines rising upward.
 * Creates a premium "data flowing" effect for hero backgrounds.
 * Adapted from TSX/Tailwind to plain JS/inline styles for CRA.
 */
export function BeamCanvas({ style, className, beamCount = 24, baseColor = 'rgba(0,255,255,' }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const beamsRef = useRef([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const LAYERS = 3;

    function createBeam(w, h, layer) {
      const angle = -35 + Math.random() * 10;
      const baseSpeed = 0.15 + layer * 0.15;
      const baseOpacity = 0.04 + layer * 0.03;
      const baseWidth = 6 + layer * 4;
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        width: baseWidth,
        length: h * 2.5,
        angle,
        speed: baseSpeed + Math.random() * 0.15,
        opacity: baseOpacity + Math.random() * 0.06,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.01 + Math.random() * 0.015,
        layer,
      };
    }

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio, 2);
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);

      beamsRef.current = [];
      for (let layer = 1; layer <= LAYERS; layer++) {
        for (let i = 0; i < beamCount / LAYERS; i++) {
          beamsRef.current.push(createBeam(canvas.clientWidth, canvas.clientHeight, layer));
        }
      }
    };

    const drawBeam = (beam) => {
      ctx.save();
      ctx.translate(beam.x, beam.y);
      ctx.rotate((beam.angle * Math.PI) / 180);

      const pulsingOpacity = Math.min(1, beam.opacity * (0.8 + Math.sin(beam.pulse) * 0.4));
      const gradient = ctx.createLinearGradient(0, 0, 0, beam.length);
      gradient.addColorStop(0, `${baseColor}0)`);
      gradient.addColorStop(0.2, `${baseColor}${pulsingOpacity * 0.5})`);
      gradient.addColorStop(0.5, `${baseColor}${pulsingOpacity})`);
      gradient.addColorStop(0.8, `${baseColor}${pulsingOpacity * 0.5})`);
      gradient.addColorStop(1, `${baseColor}0)`);

      ctx.fillStyle = gradient;
      ctx.filter = `blur(${1 + beam.layer * 2}px)`;
      ctx.fillRect(-beam.width / 2, 0, beam.width, beam.length);
      ctx.restore();
    };

    const render = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      beamsRef.current.forEach((beam) => {
        beam.y -= beam.speed * (beam.layer / LAYERS + 0.5);
        beam.pulse += beam.pulseSpeed;
        if (beam.y + beam.length < -50) {
          beam.y = h + 50;
          beam.x = Math.random() * w;
        }
        drawBeam(beam);
      });

      animRef.current = requestAnimationFrame(render);
    };

    resize();
    window.addEventListener('resize', resize);
    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animRef.current);
    };
  }, [beamCount, baseColor]);

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

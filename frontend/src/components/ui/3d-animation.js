import React, { useEffect, useRef } from 'react';

/**
 * Spectr 3D Poem Animation — a rotating cube with scrolling text on its faces,
 * layered over an ambient courtyard background with a hue-shift glow and the
 * cube's mirrored reflection below.
 *
 * All classNames are prefixed `s3d-` and the surrounding wrapper is `.s3d-hero`
 * so nothing collides with Tailwind utilities, landing-page CSS, or index.css
 * globals like `.container` / `.content`.
 *
 * Props:
 *   poemHTML          — HTML string rendered on each text face of the cube.
 *   backgroundImageUrl — image drawn behind the cube (with zoom/blur/brightness animation).
 *   boyImageUrl        — foreground silhouette image overlaid on the scene.
 */
export const PoemAnimation = ({ poemHTML, backgroundImageUrl, boyImageUrl }) => {
  const contentRef = useRef(null);

  // Responsive scaling — the inner stage is drawn at a fixed 1000×562 canvas
  // and scaled down below that viewport width so the 3D math keeps looking right.
  useEffect(() => {
    function adjustContentSize() {
      if (contentRef.current) {
        const viewportWidth = window.innerWidth;
        const baseWidth = 1000;
        const scaleFactor = viewportWidth < baseWidth ? (viewportWidth / baseWidth) * 0.9 : 1;
        contentRef.current.style.transform = `scale(${scaleFactor})`;
      }
    }
    adjustContentSize();
    window.addEventListener('resize', adjustContentSize);
    return () => window.removeEventListener('resize', adjustContentSize);
  }, []);

  return (
    <header className="s3d-hero">
      <div className="s3d-container">
        <div
          ref={contentRef}
          className="s3d-content"
          style={{ display: 'block', width: '1000px', height: '562px' }}
        >
          <div className="s3d-full">
            <div className="s3d-hue" />
            {backgroundImageUrl && (
              <img
                className="s3d-bg"
                src={backgroundImageUrl}
                alt=""
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            )}
            {boyImageUrl && (
              <img
                className="s3d-fg"
                src={boyImageUrl}
                alt=""
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            )}

            {/* Primary cube */}
            <div className="s3d-stage">
              <div className="s3d-cube">
                <div className="s3d-face s3d-top" />
                <div className="s3d-face s3d-bottom" />
                <div className="s3d-face s3d-left s3d-text" dangerouslySetInnerHTML={{ __html: poemHTML }} />
                <div className="s3d-face s3d-right s3d-text" dangerouslySetInnerHTML={{ __html: poemHTML }} />
                <div className="s3d-face s3d-front" />
                <div className="s3d-face s3d-back s3d-text" dangerouslySetInnerHTML={{ __html: poemHTML }} />
              </div>
            </div>

            {/* Mirrored reflection cube */}
            <div className="s3d-stage s3d-reflect">
              <div className="s3d-cube">
                <div className="s3d-face s3d-top" />
                <div className="s3d-face s3d-bottom" />
                <div className="s3d-face s3d-left s3d-text" dangerouslySetInnerHTML={{ __html: poemHTML }} />
                <div className="s3d-face s3d-right s3d-text" dangerouslySetInnerHTML={{ __html: poemHTML }} />
                <div className="s3d-face s3d-front" />
                <div className="s3d-face s3d-back s3d-text" dangerouslySetInnerHTML={{ __html: poemHTML }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

/**
 * Spectr-branded poem — Law × Accounting, the two practices Spectr is
 * built for. Highlight spans pick up the amber glow animation.
 */
export const SPECTR_POEM_HTML = `
  <p>Spectr is the operating system for Indian <span>law</span> and <span>accounting</span>. Fifty million judgments indexed, every statute decoded, every precedent cited and verified against IndianKanoon. Every GSTR-2B reconciled in one click, every TDS section classified, every ITR regime compared, every Tally import parsed, every notice answered with grounded reasoning and live citations. From the <span>Supreme Court</span> to <span>CESTAT</span>, from <span>CGST</span> to the <span>Income Tax Act</span>, from <span>NCLT</span> benches to <span>ITAT</span> orders, from <span>MCA</span> gazettes to <span>CBIC</span> circulars — the corpus understood, the compliance automated, the research instant. Six AI tiers cascading to the answer. Deep investigation inside isolated sandboxes. Every section mapped from IPC to BNS, every regime compared, every return reconciled. Where an associate once spent three days, we now spend three minutes. One platform. Two practices. <span>Law &amp; Accounting</span>, unified. Built for <span>India</span>, by <span>India</span>, for the <span>firms</span> that refuse to fall behind. Spectr — <span>research</span>, <span>reason</span>, <span>file</span>, <span>ship</span>.</p>
`;

export default PoemAnimation;

import React from 'react';

/**
 * 3D Isometric Cube Loader — shows while AI is thinking.
 * Adapted from TSX/Tailwind to plain JS/inline styles for CRA.
 * Small version (scale 0.3) for inline use in chat.
 */
export function CubeLoader({ size = 0.3, style = {} }) {
  const id = React.useId?.() || 'cl';

  return (
    <>
      <style>{`
        .cl-loader{position:relative;transform:scale(${size});transform-origin:center center;width:96px;height:96px}
        .cl-box{position:absolute;left:50%;top:50%;margin-left:-12px;margin-top:-12px}
        .cl-box>div{width:24px;height:24px;background:#0A0A0A;position:absolute;
          transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg);
          box-shadow:-1px 1px 0 rgba(0,0,0,0.3);
        }
        .cl-box>div::before,.cl-box>div::after{content:'';position:absolute;width:100%;height:100%}
        .cl-box>div::before{
          left:-40%;top:50%;
          background:rgba(10,10,10,0.75);
          transform:skewY(37deg);
          box-shadow:-1px 0 0 rgba(0,0,0,0.3);
        }
        .cl-box>div::after{
          left:50%;top:-40%;
          background:rgba(10,10,10,0.55);
          transform:skewX(37deg);
          box-shadow:0 -1px 0 rgba(0,0,0,0.3);
        }
        .cl-b0{--x:64px;--y:-40px}.cl-b0>div{animation:cl-s0 3s linear infinite}
        .cl-b0{animation:cl-m0 3s linear infinite}
        .cl-b1{--x:64px;--y:10px}.cl-b1>div{animation:cl-s1 3s linear infinite}
        .cl-b1{animation:cl-m1 3s linear infinite}
        .cl-b2{--x:32px;--y:-15px}.cl-b2>div{animation:cl-s2 3s linear infinite}
        .cl-b2{animation:cl-m2 3s linear infinite}
        .cl-b3{--x:32px;--y:35px}.cl-b3>div{animation:cl-s3 3s linear infinite}
        .cl-b3{animation:cl-m3 3s linear infinite}
        .cl-b4{--x:0px;--y:10px}.cl-b4>div{animation:cl-s4 3s linear infinite}
        .cl-b4{animation:cl-m4 3s linear infinite}
        .cl-b5{--x:0px;--y:60px}.cl-b5>div{animation:cl-s5 3s linear infinite}
        .cl-b5{animation:cl-m5 3s linear infinite}
        .cl-b6{--x:-32px;--y:35px}.cl-b6>div{animation:cl-s6 3s linear infinite}
        .cl-b6{animation:cl-m6 3s linear infinite}
        .cl-b7{--x:-32px;--y:85px}.cl-b7>div{animation:cl-s7 3s linear infinite}
        .cl-b7{animation:cl-m7 3s linear infinite}
        .cl-ground{position:absolute;left:50%;top:50%;margin-left:-36px;margin-top:20px;
          width:72px;height:72px;background:rgba(0,0,0,0.12);border-radius:50%;
          transform:rotateX(90deg) rotateY(0deg) translate(-48px,-120px) translateZ(100px) scale(0);
          animation:cl-ground 3s linear infinite;
        }
        .cl-ground>div{width:100%;height:100%;border-radius:50%;
          background:radial-gradient(circle,rgba(0,0,0,0.15),transparent 70%);
          animation:cl-gshin 3s linear infinite;
        }
        @keyframes cl-m0{12%{transform:translate(var(--x),var(--y))}25%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s0{6%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}14%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-m1{16%{transform:translate(var(--x),var(--y))}29%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s1{10%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}18%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-m2{20%{transform:translate(var(--x),var(--y))}33%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s2{14%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}22%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-m3{24%{transform:translate(var(--x),var(--y))}37%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s3{18%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}26%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-m4{28%{transform:translate(var(--x),var(--y))}41%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s4{22%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}30%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-m5{32%{transform:translate(var(--x),var(--y))}45%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s5{26%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}34%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-m6{36%{transform:translate(var(--x),var(--y))}49%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s6{30%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}38%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-m7{40%{transform:translate(var(--x),var(--y))}53%,52%{transform:translate(0,0)}80%{transform:translate(0,-32px)}90%,100%{transform:translate(0,188px)}}
        @keyframes cl-s7{34%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(0)}42%,100%{transform:rotateY(-47deg) rotateX(-15deg) rotateZ(15deg) scale(1)}}
        @keyframes cl-ground{0%,65%{transform:rotateX(90deg) rotateY(0deg) translate(-48px,-120px) translateZ(100px) scale(0)}75%,90%{transform:rotateX(90deg) rotateY(0deg) translate(-48px,-120px) translateZ(100px) scale(1)}100%{transform:rotateX(90deg) rotateY(0deg) translate(-48px,-120px) translateZ(100px) scale(0)}}
        @keyframes cl-gshin{0%,70%{opacity:0}75%,87%{opacity:0.2}100%{opacity:0}}
      `}</style>
      <div className="cl-loader" style={style}>
        {[0,1,2,3,4,5,6,7].map(i => (
          <div key={i} className={`cl-box cl-b${i}`}><div /></div>
        ))}
        <div className="cl-ground"><div /></div>
      </div>
    </>
  );
}

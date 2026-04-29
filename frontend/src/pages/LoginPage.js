import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Scale, ArrowRight, ShieldCheck } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { loginWithGoogle, user } = useAuth();

  React.useEffect(() => {
    if (user) {
      navigate('/app/assistant');
    }
  }, [user, navigate]);

  const handleLogin = async () => {
    try {
      await loginWithGoogle();
      // Navigation handled by useEffect watching user state
    } catch (err) {
      console.error('Login error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col md:flex-row font-display relative overflow-hidden">
      {/* Background abstract elements */}
      <div className="absolute inset-0 bg-mesh opacity-20 pointer-events-none" />
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[#0A0A0A] opacity-[0.05] blur-[150px] rounded-full pointer-events-none animate-pulse-slow" />
      
      {/* Left side - Branding & Hype */}
      <div className="flex-1 p-12 flex flex-col justify-between relative z-10 hidden md:flex">
        <div>
          <div className="flex items-center mb-16">
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 32, fontWeight: 500, letterSpacing: '-0.05em', color: '#fff', background: 'linear-gradient(to bottom right, #fff 40%, rgba(255,255,255,0.55))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>Spectr</span>
          </div>

          <h1 className="text-5xl lg:text-6xl font-serif text-white leading-[1.1] mb-6 tracking-tight">
            The legal intelligence<br />platform for India.
          </h1>
          <p className="text-[#94A3B8] text-lg max-w-md font-light">
            Log in to access the Tri-Model Map-Reduce document engine, 18+ indexed statutes, and zero-hallucination mathematical outputs.
          </p>
        </div>

        <div className="flex items-center gap-4 text-[#64748B] text-sm">
          <ShieldCheck className="w-5 h-5" />
          <span>Enterprise Grade Security • Powered by Google Auth</span>
        </div>
      </div>

      {/* Right side - Auth panel */}
      <div className="flex-1 bg-white flex items-center justify-center p-8 relative z-20 shadow-[-20px_0_50px_rgba(0,0,0,0.5)]">
        <div className="w-full max-w-sm page-enter">
          <div className="md:hidden flex items-center mb-12">
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 26, fontWeight: 500, letterSpacing: '-0.05em', color: '#0A0A0A', background: 'linear-gradient(to bottom right, #0A0A0A 40%, rgba(10,10,10,0.5))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>Spectr</span>
          </div>
          
          <h2 className="text-3xl font-bold text-[#0A0A0A] tracking-tight mb-2">Welcome Back</h2>
          <p className="text-[#64748B] mb-8 font-light">Continue to your workspace.</p>
          
          <button
            onClick={handleLogin}
            className="w-full group relative flex items-center justify-center gap-3 bg-white border-2 border-[#E2E8F0] p-4 rounded-[14px] text-[#0A0A0A] font-bold hover:bg-[#F8FAFC] hover:border-[#CBD5E1] transition-all duration-300"
          >
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="w-5 h-5 absolute left-5" alt="Google" />
            <span>Continue with Google</span>
            <ArrowRight className="w-4 h-4 absolute right-5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
          </button>
          
          <p className="text-center text-xs text-[#94A3B8] mt-8 leading-relaxed">
            By continuing, you agree to our Terms of Service and Privacy Policy.<br />
            For enterprise SSO setup, contact sales.
          </p>
        </div>
      </div>
    </div>
  );
}

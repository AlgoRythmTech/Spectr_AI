import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Scale, ArrowRight, ShieldCheck } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { loginWithGoogle, devLogin, user } = useAuth();

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

  const handleDevLogin = () => {
    devLogin();
    // Navigation handled by useEffect watching user state
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col md:flex-row font-display relative overflow-hidden">
      {/* Background abstract elements */}
      <div className="absolute inset-0 bg-mesh opacity-20 pointer-events-none" />
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[#0A0A0A] opacity-[0.05] blur-[150px] rounded-full pointer-events-none animate-pulse-slow" />
      
      {/* Left side - Branding & Hype */}
      <div className="flex-1 p-12 flex flex-col justify-between relative z-10 hidden md:flex">
        <div>
          <div className="flex items-center gap-3 mb-16">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center p-2 shadow-[0_0_20px_rgba(255,255,255,0.2)]">
              <Scale className="w-6 h-6 text-[#0A0A0A]" />
            </div>
            <span className="text-2xl font-bold tracking-tight text-white font-display">Associate</span>
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
          <div className="md:hidden flex items-center gap-2 mb-12">
            <div className="w-8 h-8 bg-[#0A0A0A] rounded-lg flex items-center justify-center">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-bold text-[#0A0A0A]">Associate</span>
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
          
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#E2E8F0]" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-3 text-[#94A3B8] font-semibold tracking-wider">Or</span>
            </div>
          </div>

          <button
            onClick={handleDevLogin}
            className="w-full group relative flex items-center justify-center gap-3 bg-[#0A0A0A] text-white p-4 rounded-[100px] font-bold hover:bg-[#1A1A1A] transition-all duration-300 shadow-lg hover:shadow-xl hover:-translate-y-0.5"
          >
            <span>Dev Bypass</span>
            <ArrowRight className="w-4 h-4 absolute right-5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all text-[#0A0A0A]" />
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

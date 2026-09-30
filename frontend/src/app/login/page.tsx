'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';

const ROLE_CONFIG = {
  CITIZEN: {
    label: 'Citizen',
    labelHi: 'नागरिक',
    icon: '🧑‍💼',
    desc: 'File & track your grievances',
    color: '#0e3b64',
  },
  OFFICER: {
    label: 'Officer',
    labelHi: 'अधिकारी',
    icon: '🏛️',
    desc: 'Manage assigned cases',
    color: '#166534',
  },
  ADMIN: {
    label: 'District Admin',
    labelHi: 'जिला प्रशासक',
    icon: '⚙️',
    desc: 'District oversight & triage',
    color: '#7c3aed',
  },
} as const;

type RoleKey = keyof typeof ROLE_CONFIG;

export default function LoginPage() {
  const { login } = useAuth();
  const { language } = useLanguage();
  const router = useRouter();

  const [roleTab, setRoleTab] = useState<RoleKey>('CITIZEN');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);
    try {
      const user = await login(email.trim(), password);
      if (user.role === 'OFFICER') router.push('/officer');
      else if (user.role === 'DISTRICT_ADMIN' || user.role === 'SUPER_ADMIN') router.push('/admin');
      else router.push('/dashboard');
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.detail ||
          (language === 'hi'
            ? 'ईमेल या पासवर्ड अमान्य है।'
            : 'Invalid email or password. Please verify credentials.')
      );
    } finally {
      setLoading(false);
    }
  };

  const setDemo = (role: RoleKey) => {
    setRoleTab(role);
    setErrorMsg(null);
    const demos = {
      CITIZEN: { e: 'citizen.demo@example.com', p: 'CitizenPass123!' },
      OFFICER: { e: 'officer.bhopal.revenue@example.com', p: 'OfficerPass123!' },
      ADMIN: { e: 'admin.bhopal@example.com', p: 'AdminPass123!' },
    };
    setEmail(demos[role].e);
    setPassword(demos[role].p);
  };

  const activeColor = ROLE_CONFIG[roleTab].color;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: '#f0f4f8' }}>

      {/* LEFT PANEL: Branding */}
      <div
        className="login-left-panel"
        style={{
          flex: '0 0 42%',
          background: 'linear-gradient(160deg, #0a1f3a 0%, #0e3b64 50%, #1a5276 100%)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '3rem 2.5rem',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative circles */}
        <div style={{
          position: 'absolute', top: '-80px', right: '-80px',
          width: '320px', height: '320px', borderRadius: '50%',
          background: 'rgba(255,255,255,0.04)', pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', bottom: '-60px', left: '-60px',
          width: '240px', height: '240px', borderRadius: '50%',
          background: 'rgba(255,153,51,0.08)', pointerEvents: 'none',
        }} />

        {/* Top tricolor stripe */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '5px',
          background: 'linear-gradient(90deg, #FF9933 33.3%, #ffffff 33.3%, #ffffff 66.6%, #138808 66.6%)',
        }} />

        {/* Logo & title */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2.5rem' }}>
            <div style={{
              background: 'rgba(255,255,255,0.12)',
              border: '2px solid rgba(255,255,255,0.2)',
              borderRadius: '12px', padding: '8px',
              display: 'flex', backdropFilter: 'blur(4px)',
            }}>
              <Image src="/logo.png" alt="JanSeva AI" width={52} height={52} style={{ objectFit: 'contain' }} priority />
            </div>
            <div>
              <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '1.4rem', lineHeight: 1.2, letterSpacing: '-0.02em' }}>
                JanSeva AI
              </div>
              <div style={{ color: '#FF9933', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                जनसेवा AI पोर्टल
              </div>
            </div>
          </div>

          <h2 style={{ color: '#ffffff', fontSize: '1.7rem', fontWeight: 800, lineHeight: 1.3, marginBottom: '0.75rem' }}>
            Transparent.<br />
            Accountable.<br />
            <span style={{ color: '#FF9933' }}>Time-Bound.</span>
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.9rem', lineHeight: 1.7, maxWidth: '280px' }}>
            Madhya Pradesh Government&apos;s official AI-powered grievance redressal platform under Lok Seva Guarantee Act.
          </p>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {[
            { n: '55', label: 'Districts Connected', icon: '🗺️' },
            { n: '8', label: 'Departments Integrated', icon: '🏛️' },
            { n: '100%', label: 'AI-Assisted Triage', icon: '🤖' },
          ].map(({ n, label, icon }) => (
            <div key={label} style={{
              display: 'flex', alignItems: 'center', gap: '0.85rem',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '10px', padding: '0.75rem 1rem',
            }}>
              <span style={{ fontSize: '1.4rem' }}>{icon}</span>
              <div>
                <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '1.1rem', lineHeight: 1 }}>{n}</div>
                <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.78rem', marginTop: '2px' }}>{label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer note */}
        <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.7rem', lineHeight: 1.6, marginTop: '1.5rem' }}>
          Government of Madhya Pradesh &bull; NIC Hosted &bull; ISO 9001:2015<br />
          Helpline: <strong style={{ color: 'rgba(255,255,255,0.6)' }}>181</strong> (Toll Free)
        </div>
      </div>

      {/* RIGHT PANEL: Form */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2.5rem 1.5rem',
        overflowY: 'auto',
      }}>
        <div style={{ width: '100%', maxWidth: '420px' }}>

          {/* Card */}
          <div style={{
            background: '#ffffff',
            borderRadius: '16px',
            boxShadow: '0 4px 40px rgba(0,0,0,0.10)',
            overflow: 'hidden',
          }}>
            {/* Accent bar */}
            <div style={{
              height: '4px',
              background: `linear-gradient(90deg, ${activeColor}, ${activeColor}99)`,
              transition: 'background 0.3s ease',
            }} />

            <div style={{ padding: '2rem 2.25rem' }}>

              <h1 style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0a1f3a', marginBottom: '4px' }}>
                {language === 'hi' ? 'पोर्टल लॉगिन' : 'Portal Sign In'}
              </h1>
              <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '1.5rem' }}>
                {language === 'hi' ? 'अपनी भूमिका चुनें और लॉगिन करें' : 'Select your role and sign in securely'}
              </p>

              {/* Role Tabs */}
              <div style={{
                display: 'flex', gap: '0.5rem', marginBottom: '1.5rem',
                background: '#f1f5f9', borderRadius: '10px', padding: '4px',
              }}>
                {(Object.keys(ROLE_CONFIG) as RoleKey[]).map((role) => {
                  const cfg = ROLE_CONFIG[role];
                  const isActive = roleTab === role;
                  return (
                    <button
                      key={role}
                      type="button"
                      onClick={() => { setRoleTab(role); setErrorMsg(null); }}
                      style={{
                        flex: 1, padding: '0.5rem 0.25rem',
                        border: 'none', borderRadius: '7px',
                        cursor: 'pointer', textAlign: 'center',
                        background: isActive ? cfg.color : 'transparent',
                        color: isActive ? '#ffffff' : '#475569',
                        fontWeight: isActive ? 700 : 600,
                        fontSize: '0.72rem',
                        transition: 'all 0.2s ease',
                        boxShadow: isActive ? '0 2px 8px rgba(0,0,0,0.18)' : 'none',
                      }}
                    >
                      <div style={{ fontSize: '1rem', marginBottom: '2px' }}>{cfg.icon}</div>
                      {language === 'hi' ? cfg.labelHi : cfg.label}
                    </button>
                  );
                })}
              </div>

              {/* Role description */}
              <div style={{
                background: '#f8faff',
                border: `1px solid ${activeColor}22`,
                borderLeft: `3px solid ${activeColor}`,
                borderRadius: '6px', padding: '0.55rem 0.85rem',
                marginBottom: '1.25rem', fontSize: '0.78rem', color: '#374151',
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                transition: 'border-color 0.3s',
              }}>
                <span style={{ fontSize: '1rem' }}>{ROLE_CONFIG[roleTab].icon}</span>
                {ROLE_CONFIG[roleTab].desc}
                <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: '0.7rem' }}>
                  {roleTab === 'CITIZEN' ? 'Public Access' : 'Official Portal'}
                </span>
              </div>

              {/* Demo Quick-fill */}
              <div style={{
                background: 'linear-gradient(135deg, #eff6ff, #f0fdf4)',
                border: '1px solid #bfdbfe', borderRadius: '8px',
                padding: '0.65rem 1rem', marginBottom: '1.25rem',
                fontSize: '0.75rem', color: '#1e40af',
              }}>
                <span style={{ fontWeight: 700, display: 'block', marginBottom: '6px' }}>
                  🚀 Demo Quick-Fill
                </span>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {(['CITIZEN', 'OFFICER', 'ADMIN'] as RoleKey[]).map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => setDemo(role)}
                      style={{
                        background: roleTab === role ? '#1e40af' : '#dbeafe',
                        color: roleTab === role ? '#ffffff' : '#1e40af',
                        border: 'none', borderRadius: '5px',
                        padding: '3px 10px', fontSize: '0.72rem',
                        fontWeight: 700, cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                    >
                      {role === 'CITIZEN' ? 'Citizen' : role === 'OFFICER' ? 'Officer' : 'Admin'}
                    </button>
                  ))}
                </div>
              </div>

              {errorMsg && (
                <div style={{
                  background: '#fef2f2', border: '1px solid #fecaca',
                  borderLeft: '3px solid #dc2626', borderRadius: '6px',
                  padding: '0.65rem 0.9rem', marginBottom: '1rem',
                  fontSize: '0.8rem', color: '#991b1b',
                  display: 'flex', alignItems: 'flex-start', gap: '0.5rem',
                }}>
                  <span style={{ fontWeight: 700 }}>✕</span>
                  <span>{errorMsg}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{
                    display: 'block', fontSize: '0.78rem', fontWeight: 700,
                    color: '#374151', marginBottom: '5px',
                    textTransform: 'uppercase', letterSpacing: '0.04em',
                  }}>
                    {language === 'hi' ? 'ईमेल / यूज़र आईडी' : 'Email / User ID'}{' '}
                    <span style={{ color: '#dc2626' }}>*</span>
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.gov.in"
                    style={{
                      width: '100%', padding: '0.65rem 0.85rem',
                      border: '1.5px solid #e2e8f0', borderRadius: '8px',
                      fontSize: '0.9rem', color: '#0f172a', outline: 'none',
                      background: '#fafafa', boxSizing: 'border-box',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = activeColor)}
                    onBlur={(e) => (e.target.style.borderColor = '#e2e8f0')}
                  />
                </div>

                <div>
                  <label style={{
                    display: 'block', fontSize: '0.78rem', fontWeight: 700,
                    color: '#374151', marginBottom: '5px',
                    textTransform: 'uppercase', letterSpacing: '0.04em',
                  }}>
                    {language === 'hi' ? 'पासवर्ड' : 'Password'}{' '}
                    <span style={{ color: '#dc2626' }}>*</span>
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      style={{
                        width: '100%', padding: '0.65rem 3rem 0.65rem 0.85rem',
                        border: '1.5px solid #e2e8f0', borderRadius: '8px',
                        fontSize: '0.9rem', color: '#0f172a', outline: 'none',
                        background: '#fafafa', boxSizing: 'border-box',
                      }}
                      onFocus={(e) => (e.target.style.borderColor = activeColor)}
                      onBlur={(e) => (e.target.style.borderColor = '#e2e8f0')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: 'absolute', right: '10px', top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'none', border: 'none', cursor: 'pointer',
                        fontSize: '0.72rem', color: '#64748b', fontWeight: 600,
                      }}
                    >
                      {showPassword ? '🙈 Hide' : '👁 Show'}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    width: '100%', padding: '0.8rem',
                    background: loading ? '#94a3b8' : activeColor,
                    color: '#ffffff', border: 'none', borderRadius: '9px',
                    fontSize: '0.92rem', fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s', letterSpacing: '0.03em',
                    boxShadow: loading ? 'none' : `0 4px 14px ${activeColor}55`,
                    marginTop: '0.25rem',
                  }}
                >
                  {loading
                    ? (language === 'hi' ? '⏳ सत्यापन जारी है...' : '⏳ Verifying...')
                    : (language === 'hi' ? '🔐 सुरक्षित लॉगिन करें' : '🔐 Secure Sign In')}
                </button>
              </form>

              <div style={{
                borderTop: '1px solid #f1f5f9', marginTop: '1.5rem',
                paddingTop: '1.25rem', textAlign: 'center',
                fontSize: '0.8rem', color: '#64748b',
              }}>
                <p>
                  {language === 'hi' ? 'नया नागरिक?' : 'New citizen?'}{' '}
                  <Link href="/register" style={{ color: activeColor, fontWeight: 700, textDecoration: 'none' }}>
                    {language === 'hi' ? 'पंजीकरण करें →' : 'Register Here →'}
                  </Link>
                </p>
                <p style={{ marginTop: '0.5rem' }}>
                  <Link href="/track" style={{ color: '#047857', fontWeight: 600, textDecoration: 'none', fontSize: '0.75rem' }}>
                    🔍 {language === 'hi' ? 'बिना लॉगिन शिकायत ट्रैक करें' : 'Track grievance without login'}
                  </Link>
                </p>
              </div>
            </div>
          </div>

          {/* Statutory notice */}
          <div style={{
            marginTop: '1.25rem', padding: '0.75rem 1rem',
            background: '#fffbeb', border: '1px solid #fde68a',
            borderRadius: '8px', fontSize: '0.7rem', color: '#92400e',
            textAlign: 'center', lineHeight: 1.6,
          }}>
            ⚠️ Official Govt. of MP portal. Unauthorized access is punishable under IT Act 2000.
            &nbsp;Helplines: <strong>181</strong> &bull; <strong>112</strong>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .login-left-panel { display: none !important; }
        }
      `}</style>
    </div>
  );
}

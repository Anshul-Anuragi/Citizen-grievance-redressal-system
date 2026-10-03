'use client';

import React, { useState, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import api from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { formatApiError } from '@/utils/formatError';

const STEPS = ['Personal Info', 'Account Setup', 'Declaration'];

export const PASSWORD_RULES = [
  {
    id: 'length',
    labelEn: 'At least 8 characters',
    labelHi: 'कम से कम 8 वर्ण',
    test: (p: string) => p.length >= 8,
  },
  {
    id: 'upper',
    labelEn: 'One uppercase letter (A-Z)',
    labelHi: 'एक बड़ा अक्षर (A-Z)',
    test: (p: string) => /[A-Z]/.test(p),
  },
  {
    id: 'lower',
    labelEn: 'One lowercase letter (a-z)',
    labelHi: 'एक छोटा अक्षर (a-z)',
    test: (p: string) => /[a-z]/.test(p),
  },
  {
    id: 'number',
    labelEn: 'One number (0-9)',
    labelHi: 'एक अंक (0-9)',
    test: (p: string) => /\d/.test(p),
  },
  {
    id: 'special',
    labelEn: 'One special character',
    labelHi: 'एक विशेष वर्ण (उदा. !@#$%^&*)',
    // Matches backend regex _PASSWORD_POLICY_PATTERN:
    // [!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;\'\/`~]
    test: (p: string) => /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\;'/`~]/.test(p),
  },
];

export const normalizeMobile = (raw: string): string => {
  let val = raw.trim();
  if (val.startsWith('+91')) {
    val = val.slice(3).trim();
  }
  if (val.startsWith('0') && val.length === 11) {
    val = val.slice(1);
  }
  return val.replace(/\s+/g, '');
};

export const isMobileValid = (raw: string): boolean => {
  const trimmed = raw.trim();
  if (!trimmed) return true; // Optional field
  const normalized = normalizeMobile(trimmed);
  return /^[6-9]\d{9}$/.test(normalized);
};

export default function RegisterPage() {
  const { login } = useAuth();
  const { language } = useLanguage();
  const router = useRouter();

  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    mobile: '',
    password: '',
    confirmPassword: '',
    declaration: false,
  });

  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [passwordAttempted, setPasswordAttempted] = useState(false);
  const [mobileAttempted, setMobileAttempted] = useState(false);

  const passwordRef = useRef<HTMLInputElement>(null);
  const mobileRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const allPasswordRulesPassed = PASSWORD_RULES.every((r) => r.test(formData.password));

  const getPasswordStrength = (p: string) => {
    if (!p) return null;
    const passedCount = PASSWORD_RULES.filter((r) => r.test(p)).length;

    if (passedCount === 5) {
      return {
        label: 'Strong',
        text:
          language === 'hi'
            ? 'मजबूत पासवर्ड — सभी आवश्यकताएं पूरी हुईं।'
            : 'Strong password — all requirements satisfied.',
        color: '#16a34a',
        pct: 100,
      };
    }
    if (passedCount >= 3) {
      return {
        label: 'Medium',
        text: language === 'hi' ? 'मध्यम पासवर्ड' : 'Medium password',
        color: '#f59e0b',
        pct: 66,
      };
    }
    return {
      label: 'Weak',
      text: language === 'hi' ? 'कमजोर पासवर्ड' : 'Weak password',
      color: '#dc2626',
      pct: 33,
    };
  };

  const strength = getPasswordStrength(formData.password);

  const validateStep = (): boolean => {
    setErrorMsg(null);
    if (step === 0) {
      if (!formData.fullName.trim()) {
        setErrorMsg(language === 'hi' ? 'पूरा नाम आवश्यक है।' : 'Full name is required.');
        return false;
      }
      if (!formData.email.trim()) {
        setErrorMsg(language === 'hi' ? 'ईमेल पता आवश्यक है।' : 'Email address is required.');
        return false;
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
        setErrorMsg(
          language === 'hi'
            ? 'कृपया एक मान्य ईमेल पता दर्ज करें।'
            : 'Please enter a valid email address.'
        );
        return false;
      }
      if (formData.mobile.trim() && !isMobileValid(formData.mobile)) {
        setMobileAttempted(true);
        setErrorMsg(
          language === 'hi'
            ? 'मोबाइल नंबर में ठीक 10 अंक होने चाहिए और यह 6-9 से शुरू होना चाहिए।'
            : 'Mobile number must contain exactly 10 digits and start with 6–9.'
        );
        mobileRef.current?.focus();
        return false;
      }
    }

    if (step === 1) {
      if (!allPasswordRulesPassed) {
        setPasswordAttempted(true);
        setErrorMsg(
          language === 'hi'
            ? 'आपका पासवर्ड बहुत कमजोर है। कृपया आगे बढ़ने से पहले हाइलाइट की गई आवश्यकताओं को पूरा करें।'
            : 'Your password is too weak. Please complete the highlighted requirements before registering.'
        );
        passwordRef.current?.focus();
        return false;
      }
      if (formData.password !== formData.confirmPassword) {
        setErrorMsg(language === 'hi' ? 'पासवर्ड मेल नहीं खाते।' : 'Passwords do not match.');
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    // Validate step 0
    if (!formData.fullName.trim() || !formData.email.trim()) {
      setStep(0);
      setErrorMsg(language === 'hi' ? 'कृपया सभी आवश्यक फ़ील्ड भरें।' : 'Please fill in all required fields.');
      return;
    }

    if (formData.mobile.trim() && !isMobileValid(formData.mobile)) {
      setStep(0);
      setMobileAttempted(true);
      setErrorMsg(
        language === 'hi'
          ? 'मोबाइल नंबर में ठीक 10 अंक होने चाहिए और यह 6-9 से शुरू होना चाहिए।'
          : 'Mobile number must contain exactly 10 digits and start with 6–9.'
      );
      mobileRef.current?.focus();
      return;
    }

    // Validate step 1
    if (!allPasswordRulesPassed) {
      setStep(1);
      setPasswordAttempted(true);
      setErrorMsg(
        language === 'hi'
          ? 'आपका पासवर्ड बहुत कमजोर है। कृपया आगे बढ़ने से पहले हाइलाइट की गई आवश्यकताओं को पूरा करें।'
          : 'Your password is too weak. Please complete the highlighted requirements before registering.'
      );
      setTimeout(() => passwordRef.current?.focus(), 50);
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setStep(1);
      setErrorMsg(language === 'hi' ? 'पासवर्ड मेल नहीं खाते।' : 'Passwords do not match.');
      return;
    }

    // Validate step 2
    if (!formData.declaration) {
      setErrorMsg(language === 'hi' ? 'कृपया स्व-घोषणा स्वीकार करें।' : 'Please accept the declaration to proceed.');
      return;
    }

    setLoading(true);
    try {
      const cleanMobile = formData.mobile.trim() ? normalizeMobile(formData.mobile) : undefined;

      await api.post('/auth/register', {
        email: formData.email.trim(),
        password: formData.password,
        full_name: formData.fullName.trim(),
        mobile: cleanMobile,
      });

      setSuccessMsg(
        language === 'hi'
          ? 'पंजीकरण सफल! डैशबोर्ड पर ले जाया जा रहा है...'
          : 'Registration successful! Redirecting to your dashboard...'
      );

      try {
        await login(formData.email.trim(), formData.password);
        setTimeout(() => router.push('/dashboard'), 1200);
      } catch {
        setTimeout(() => router.push('/login'), 1500);
      }
    } catch (err: any) {
      const fallback =
        language === 'hi'
          ? 'पंजीकरण विफल। यह ईमेल पहले से पंजीकृत हो सकता है।'
          : 'Registration failed. This email may already be registered.';
      setErrorMsg(formatApiError(err, fallback));
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '0.65rem 0.85rem',
    border: '1.5px solid #e2e8f0', borderRadius: '8px',
    fontSize: '0.875rem', color: '#0f172a', outline: 'none',
    background: '#fafafa', boxSizing: 'border-box',
    fontFamily: 'inherit',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: '0.75rem', fontWeight: 700,
    color: '#374151', marginBottom: '5px',
    textTransform: 'uppercase', letterSpacing: '0.04em',
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: '#f0f4f8' }}>

      {/* LEFT PANEL */}
      <div
        className="reg-left-panel"
        style={{
          flex: '0 0 42%',
          background: 'linear-gradient(160deg, #0a1f3a 0%, #0e3b64 55%, #1b5e20 100%)',
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
          position: 'absolute', top: '-100px', right: '-100px',
          width: '360px', height: '360px', borderRadius: '50%',
          background: 'rgba(255,255,255,0.03)', pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', bottom: '-80px', left: '-80px',
          width: '300px', height: '300px', borderRadius: '50%',
          background: 'rgba(19,136,8,0.1)', pointerEvents: 'none',
        }} />

        {/* Tricolor top */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '5px',
          background: 'linear-gradient(90deg, #FF9933 33.3%, #ffffff 33.3%, #ffffff 66.6%, #138808 66.6%)',
        }} />

        {/* Logo & brand */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2.5rem' }}>
            <div style={{
              background: 'rgba(255,255,255,0.12)',
              border: '2px solid rgba(255,255,255,0.2)',
              borderRadius: '12px', padding: '8px', display: 'flex',
            }}>
              <Image src="/logo.png" alt="JanSeva AI" width={52} height={52} style={{ objectFit: 'contain' }} priority />
            </div>
            <div>
              <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '1.4rem', lineHeight: 1.2 }}>JanSeva AI</div>
              <div style={{ color: '#4ade80', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                नागरिक पंजीकरण पोर्टल
              </div>
            </div>
          </div>

          <h2 style={{ color: '#ffffff', fontSize: '1.65rem', fontWeight: 800, lineHeight: 1.35, marginBottom: '0.85rem' }}>
            Your Voice.<br />
            Your Rights.<br />
            <span style={{ color: '#4ade80' }}>Our Commitment.</span>
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.88rem', lineHeight: 1.7, maxWidth: '270px' }}>
            Join 55 districts of Madhya Pradesh in transparent, accountable, and time-bound grievance resolution.
          </p>
        </div>

        {/* Benefits */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[
            { icon: '📋', title: 'File Grievances Online', desc: 'From any device, anytime' },
            { icon: '📍', title: 'Real-Time Tracking', desc: 'See your case status live' },
            { icon: '🤖', title: 'AI-Assisted Resolution', desc: 'Smart routing to right officer' },
            { icon: '⏱️', title: 'SLA-Bound Process', desc: 'Guaranteed timelines by law' },
          ].map(({ icon, title, desc }) => (
            <div key={title} style={{
              display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '10px', padding: '0.65rem 0.9rem',
            }}>
              <span style={{ fontSize: '1.2rem', marginTop: '1px' }}>{icon}</span>
              <div>
                <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.82rem' }}>{title}</div>
                <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.73rem', marginTop: '1px' }}>{desc}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.7rem', lineHeight: 1.6, marginTop: '1.5rem' }}>
          Government of Madhya Pradesh &bull; Lok Seva Guarantee Act 2010<br />
          Helpline: <strong style={{ color: 'rgba(255,255,255,0.6)' }}>181</strong> (Toll Free)
        </div>
      </div>

      {/* RIGHT PANEL: Form */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1.5rem',
        overflowY: 'auto',
      }}>
        <div style={{ width: '100%', maxWidth: '460px' }}>

          {/* Card */}
          <div style={{
            background: '#ffffff',
            borderRadius: '16px',
            boxShadow: '0 4px 40px rgba(0,0,0,0.10)',
            overflow: 'hidden',
          }}>
            {/* Green accent bar for register */}
            <div style={{ height: '4px', background: 'linear-gradient(90deg, #166534, #16a34a)' }} />

            <div style={{ padding: '2rem 2.25rem' }}>

              <h1 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#0a1f3a', marginBottom: '4px' }}>
                {language === 'hi' ? 'नागरिक पंजीकरण' : 'Citizen Registration'}
              </h1>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '1.5rem' }}>
                {language === 'hi'
                  ? 'एक बार पंजीकरण करें — हमेशा के लिए जुड़ें'
                  : 'Register once to access all grievance services'}
              </p>

              {/* Step indicator */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.75rem' }}>
                {STEPS.map((s, i) => (
                  <React.Fragment key={s}>
                    <div style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
                      flex: 1,
                    }}>
                      <div style={{
                        width: '28px', height: '28px', borderRadius: '50%',
                        background: i < step ? '#166534' : i === step ? '#0e3b64' : '#e2e8f0',
                        color: i <= step ? '#ffffff' : '#94a3b8',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '0.72rem', fontWeight: 800,
                        transition: 'all 0.3s',
                      }}>
                        {i < step ? '✓' : i + 1}
                      </div>
                      <span style={{
                        fontSize: '0.65rem', fontWeight: 600,
                        color: i === step ? '#0e3b64' : '#94a3b8',
                        whiteSpace: 'nowrap',
                      }}>
                        {s}
                      </span>
                    </div>
                    {i < STEPS.length - 1 && (
                      <div style={{
                        flex: 2, height: '2px', marginBottom: '16px',
                        background: i < step ? '#166534' : '#e2e8f0',
                        transition: 'background 0.3s',
                      }} />
                    )}
                  </React.Fragment>
                ))}
              </div>

              {/* Alerts */}
              {errorMsg && (
                <div style={{
                  background: '#fef2f2', border: '1px solid #fecaca',
                  borderLeft: '3px solid #dc2626', borderRadius: '6px',
                  padding: '0.65rem 0.9rem', marginBottom: '1rem',
                  fontSize: '0.8rem', color: '#991b1b',
                  display: 'flex', gap: '0.5rem',
                }}>
                  <span style={{ fontWeight: 700 }}>✕</span><span>{errorMsg}</span>
                </div>
              )}
              {successMsg && (
                <div style={{
                  background: '#f0fdf4', border: '1px solid #bbf7d0',
                  borderLeft: '3px solid #16a34a', borderRadius: '6px',
                  padding: '0.65rem 0.9rem', marginBottom: '1rem',
                  fontSize: '0.8rem', color: '#166534',
                  display: 'flex', gap: '0.5rem',
                }}>
                  <span style={{ fontWeight: 700 }}>✓</span><span>{successMsg}</span>
                </div>
              )}

              <form onSubmit={handleSubmit}>

                {/* STEP 0: Personal Info */}
                {step === 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                      <label style={labelStyle}>
                        {language === 'hi' ? 'पूरा नाम' : 'Full Legal Name'}{' '}
                        <span style={{ color: '#dc2626' }}>*</span>
                      </label>
                      <input
                        name="fullName" type="text" required
                        value={formData.fullName} onChange={handleChange}
                        placeholder={language === 'hi' ? 'उदा. राजेश कुमार शर्मा' : 'e.g. Rajesh Kumar Sharma'}
                        style={inputStyle}
                        onFocus={(e) => (e.target.style.borderColor = '#0e3b64')}
                        onBlur={(e) => (e.target.style.borderColor = '#e2e8f0')}
                      />
                    </div>
                    <div>
                      <label style={labelStyle}>
                        {language === 'hi' ? 'ईमेल पता' : 'Email Address'}{' '}
                        <span style={{ color: '#dc2626' }}>*</span>
                      </label>
                      <input
                        name="email" type="email" required
                        value={formData.email} onChange={handleChange}
                        placeholder="citizen@example.com"
                        style={inputStyle}
                        onFocus={(e) => (e.target.style.borderColor = '#0e3b64')}
                        onBlur={(e) => (e.target.style.borderColor = '#e2e8f0')}
                      />
                    </div>
                    <div>
                      <label style={labelStyle}>
                        {language === 'hi' ? 'मोबाइल नंबर (SMS अपडेट)' : 'Mobile Number (SMS Updates)'}{' '}
                        <span style={{ color: '#94a3b8', fontWeight: 500, fontSize: '0.68rem', textTransform: 'none' }}>(Optional)</span>
                      </label>
                      <div style={{ display: 'flex' }}>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center',
                          padding: '0.65rem 0.75rem',
                          background: '#f1f5f9', border: '1.5px solid #e2e8f0',
                          borderRight: 'none', borderRadius: '8px 0 0 8px',
                          fontSize: '0.85rem', color: '#475569', fontWeight: 700,
                        }}>🇮🇳 +91</span>
                        <input
                          ref={mobileRef}
                          name="mobile" type="tel" maxLength={15}
                          value={formData.mobile} onChange={handleChange}
                          placeholder="9876543210"
                          style={{
                            ...inputStyle,
                            borderRadius: '0 8px 8px 0',
                            borderColor:
                              formData.mobile.trim() && !isMobileValid(formData.mobile)
                                ? '#dc2626'
                                : formData.mobile.trim() && isMobileValid(formData.mobile)
                                ? '#16a34a'
                                : '#e2e8f0',
                          }}
                          onFocus={(e) => (e.target.style.borderColor = '#0e3b64')}
                          onBlur={(e) =>
                            (e.target.style.borderColor =
                              formData.mobile.trim() && !isMobileValid(formData.mobile)
                                ? '#dc2626'
                                : formData.mobile.trim() && isMobileValid(formData.mobile)
                                ? '#16a34a'
                                : '#e2e8f0')
                          }
                        />
                      </div>

                      {/* Live mobile validation feedback */}
                      {formData.mobile.trim() !== '' && (
                        <div
                          style={{
                            marginTop: '5px',
                            fontSize: '0.73rem',
                            fontWeight: 600,
                            color: isMobileValid(formData.mobile) ? '#16a34a' : '#dc2626',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span style={{ fontWeight: 800 }}>{isMobileValid(formData.mobile) ? '✓' : '✗'}</span>
                          <span>
                            {isMobileValid(formData.mobile)
                              ? language === 'hi'
                                ? 'वैध 10-अंकीय मोबाइल नंबर'
                                : 'Valid 10-digit mobile number'
                              : language === 'hi'
                              ? 'मोबाइल नंबर में ठीक 10 अंक होने चाहिए और यह 6-9 से शुरू होना चाहिए।'
                              : 'Mobile number must contain exactly 10 digits and start with 6–9.'}
                          </span>
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => { if (validateStep()) setStep(1); }}
                      style={{
                        width: '100%', padding: '0.8rem',
                        background: '#0e3b64', color: '#ffffff',
                        border: 'none', borderRadius: '9px',
                        fontSize: '0.92rem', fontWeight: 700, cursor: 'pointer',
                        marginTop: '0.5rem', letterSpacing: '0.02em',
                        boxShadow: '0 4px 14px rgba(14,59,100,0.35)',
                      }}
                    >
                      {language === 'hi' ? 'जारी रखें →' : 'Continue →'}
                    </button>
                  </div>
                )}

                {/* STEP 1: Account Setup */}
                {step === 1 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                      <label style={labelStyle}>
                        {language === 'hi' ? 'पासवर्ड' : 'Password'}{' '}
                        <span style={{ color: '#dc2626' }}>*</span>
                      </label>
                      <div style={{ position: 'relative' }}>
                        <input
                          ref={passwordRef}
                          name="password" type={showPass ? 'text' : 'password'} required
                          value={formData.password} onChange={handleChange}
                          placeholder="••••••••••••"
                          style={{
                            ...inputStyle,
                            paddingRight: '3rem',
                            borderColor:
                              passwordAttempted && !allPasswordRulesPassed
                                ? '#dc2626'
                                : allPasswordRulesPassed
                                ? '#16a34a'
                                : '#e2e8f0',
                          }}
                          onFocus={(e) => (e.target.style.borderColor = '#0e3b64')}
                          onBlur={(e) =>
                            (e.target.style.borderColor =
                              passwordAttempted && !allPasswordRulesPassed
                                ? '#dc2626'
                                : allPasswordRulesPassed
                                ? '#16a34a'
                                : '#e2e8f0')
                          }
                        />
                        <button type="button" onClick={() => setShowPass(!showPass)} style={{
                          position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                          background: 'none', border: 'none', cursor: 'pointer',
                          fontSize: '0.72rem', color: '#64748b', fontWeight: 600,
                        }}>
                          {showPass ? '🙈 Hide' : '👁 Show'}
                        </button>
                      </div>

                      {/* Password strength */}
                      {strength && (
                        <div style={{ marginTop: '8px' }}>
                          <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{
                              height: '100%', width: `${strength.pct}%`,
                              background: strength.color, borderRadius: '4px',
                              transition: 'width 0.3s, background 0.3s',
                            }} />
                          </div>
                          <div style={{ marginTop: '4px', fontSize: '0.72rem', color: strength.color, fontWeight: 700 }}>
                            {strength.text}
                          </div>
                        </div>
                      )}

                      {/* Password Requirements Checklist */}
                      <div style={{
                        marginTop: '10px',
                        padding: '0.65rem 0.85rem',
                        background: passwordAttempted && !allPasswordRulesPassed ? '#fef2f2' : '#f8fafc',
                        border: `1.5px solid ${passwordAttempted && !allPasswordRulesPassed ? '#fca5a5' : '#e2e8f0'}`,
                        borderRadius: '8px',
                        transition: 'all 0.2s',
                      }}>
                        <div style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          color: passwordAttempted && !allPasswordRulesPassed ? '#991b1b' : '#374151',
                          marginBottom: '6px',
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                        }}>
                          {language === 'hi' ? 'पासवर्ड की आवश्यकताएं' : 'Password requirements'}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {PASSWORD_RULES.map((rule) => {
                            const satisfied = rule.test(formData.password);
                            const isMissingAfterAttempt = passwordAttempted && !satisfied;
                            return (
                              <div
                                key={rule.id}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '6px',
                                  fontSize: '0.73rem',
                                  fontWeight: satisfied ? 600 : isMissingAfterAttempt ? 700 : 500,
                                  color: satisfied
                                    ? '#16a34a'
                                    : isMissingAfterAttempt
                                    ? '#dc2626'
                                    : '#64748b',
                                  transition: 'color 0.2s',
                                }}
                              >
                                <span style={{
                                  fontSize: '0.8rem',
                                  fontWeight: 800,
                                  width: '14px',
                                  display: 'inline-block',
                                }}>
                                  {satisfied ? '✓' : '✗'}
                                </span>
                                <span>
                                  {language === 'hi' ? rule.labelHi : rule.labelEn}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    <div>
                      <label style={labelStyle}>
                        {language === 'hi' ? 'पासवर्ड की पुष्टि करें' : 'Confirm Password'}{' '}
                        <span style={{ color: '#dc2626' }}>*</span>
                      </label>
                      <div style={{ position: 'relative' }}>
                        <input
                          name="confirmPassword" type={showConfirm ? 'text' : 'password'} required
                          value={formData.confirmPassword} onChange={handleChange}
                          placeholder="••••••••••••"
                          style={{
                            ...inputStyle, paddingRight: '3rem',
                            borderColor: formData.confirmPassword && formData.password !== formData.confirmPassword ? '#dc2626' : '#e2e8f0',
                          }}
                          onFocus={(e) => (e.target.style.borderColor = '#0e3b64')}
                          onBlur={(e) => (e.target.style.borderColor = formData.password !== formData.confirmPassword ? '#dc2626' : '#e2e8f0')}
                        />
                        <button type="button" onClick={() => setShowConfirm(!showConfirm)} style={{
                          position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                          background: 'none', border: 'none', cursor: 'pointer',
                          fontSize: '0.72rem', color: '#64748b', fontWeight: 600,
                        }}>
                          {showConfirm ? '🙈 Hide' : '👁 Show'}
                        </button>
                      </div>
                      {formData.confirmPassword && formData.password === formData.confirmPassword && (
                        <div style={{ marginTop: '5px', fontSize: '0.72rem', color: '#16a34a', fontWeight: 700 }}>
                          ✓ {language === 'hi' ? 'पासवर्ड मेल खाते हैं' : 'Passwords match'}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                      <button type="button" onClick={() => setStep(0)} style={{
                        flex: 1, padding: '0.75rem',
                        background: '#f1f5f9', color: '#374151',
                        border: '1.5px solid #e2e8f0', borderRadius: '9px',
                        fontSize: '0.88rem', fontWeight: 700, cursor: 'pointer',
                      }}>
                        {language === 'hi' ? '← वापस' : '← Back'}
                      </button>
                      <button type="button" onClick={() => { if (validateStep()) setStep(2); }} style={{
                        flex: 2, padding: '0.75rem',
                        background: '#0e3b64', color: '#ffffff',
                        border: 'none', borderRadius: '9px',
                        fontSize: '0.88rem', fontWeight: 700, cursor: 'pointer',
                        boxShadow: '0 4px 14px rgba(14,59,100,0.35)',
                      }}
                      >
                        {language === 'hi' ? 'जारी रखें →' : 'Continue →'}
                      </button>
                    </div>
                  </div>
                )}

                {/* STEP 2: Declaration */}
                {step === 2 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {/* Summary */}
                    <div style={{
                      background: '#f8faff', border: '1px solid #bfdbfe',
                      borderRadius: '10px', padding: '1rem',
                    }}>
                      <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#1e40af', marginBottom: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        📋 {language === 'hi' ? 'पंजीकरण सारांश' : 'Registration Summary'}
                      </div>
                      {[
                        { label: language === 'hi' ? 'नाम' : 'Name', value: formData.fullName },
                        { label: language === 'hi' ? 'ईमेल' : 'Email', value: formData.email },
                        {
                          label: language === 'hi' ? 'मोबाइल' : 'Mobile',
                          value: formData.mobile.trim()
                            ? `+91 ${normalizeMobile(formData.mobile)}`
                            : language === 'hi'
                            ? 'प्रदान नहीं किया गया'
                            : 'Not provided',
                        },
                      ].map(({ label, value }) => (
                        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '4px 0', borderBottom: '1px solid #e0eaff' }}>
                          <span style={{ color: '#64748b', fontWeight: 600 }}>{label}</span>
                          <span style={{ color: '#0f172a', fontWeight: 700 }}>{value}</span>
                        </div>
                      ))}
                    </div>

                    {/* Declaration */}
                    <label style={{
                      display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                      background: '#fffbeb', border: '1px solid #fde68a',
                      borderRadius: '8px', padding: '0.85rem',
                      cursor: 'pointer',
                    }}>
                      <input
                        type="checkbox" name="declaration"
                        checked={formData.declaration} onChange={handleChange}
                        style={{ width: '18px', height: '18px', marginTop: '1px', cursor: 'pointer', accentColor: '#0e3b64' }}
                      />
                      <span style={{ fontSize: '0.78rem', color: '#374151', lineHeight: 1.65 }}>
                        {language === 'hi'
                          ? 'मैं घोषित करता/करती हूँ कि प्रदान की गई सभी जानकारियां सत्य हैं और मैं मध्य प्रदेश शासन की नागरिक सेवाओं का सदुपयोग करूँगा/करूँगी।'
                          : 'I hereby declare that all details provided are truthful and accurate. I will use this portal only for legitimate grievance redressal purposes.'}
                      </span>
                    </label>

                    <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.25rem' }}>
                      <button type="button" onClick={() => setStep(1)} style={{
                        flex: 1, padding: '0.75rem',
                        background: '#f1f5f9', color: '#374151',
                        border: '1.5px solid #e2e8f0', borderRadius: '9px',
                        fontSize: '0.88rem', fontWeight: 700, cursor: 'pointer',
                      }}>
                        {language === 'hi' ? '← वापस' : '← Back'}
                      </button>
                      <button type="submit" disabled={loading || !formData.declaration} style={{
                        flex: 2, padding: '0.75rem',
                        background: loading || !formData.declaration ? '#94a3b8' : '#166534',
                        color: '#ffffff', border: 'none', borderRadius: '9px',
                        fontSize: '0.88rem', fontWeight: 700,
                        cursor: loading || !formData.declaration ? 'not-allowed' : 'pointer',
                        boxShadow: loading || !formData.declaration ? 'none' : '0 4px 14px rgba(22,101,52,0.35)',
                      }}>
                        {loading
                          ? (language === 'hi' ? '⏳ पंजीकरण हो रहा है...' : '⏳ Registering...')
                          : (language === 'hi' ? '✅ पंजीकरण पूर्ण करें' : '✅ Complete Registration')}
                      </button>
                    </div>
                  </div>
                )}
              </form>

              <div style={{
                borderTop: '1px solid #f1f5f9', marginTop: '1.5rem',
                paddingTop: '1.25rem', textAlign: 'center',
                fontSize: '0.8rem', color: '#64748b',
              }}>
                {language === 'hi' ? 'पहले से खाता है?' : 'Already have an account?'}{' '}
                <Link href="/login" style={{ color: '#0e3b64', fontWeight: 700, textDecoration: 'none' }}>
                  {language === 'hi' ? 'यहाँ लॉगिन करें →' : 'Sign In →'}
                </Link>
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
          .reg-left-panel { display: none !important; }
        }
      `}</style>
    </div>
  );
}

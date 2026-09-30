'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import {
  Globe,
  LogOut,
  FileText,
  Menu,
  X,
  PlusCircle,
  Search,
  PhoneCall,
  Home,
  BarChart2,
  Shield,
  BellRing,
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { lang, toggleLanguage, t } = useLanguage();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMenu = () => setMobileMenuOpen(false);

  const getDashboardRoute = () => {
    if (!user) return '/dashboard';
    switch (user.role) {
      case 'DISTRICT_ADMIN':
        return '/admin';
      case 'OFFICER':
        return '/officer';
      default:
        return '/dashboard';
    }
  };

  return (
    <>
      {/* Top Branding Header: Scrolls smoothly out of view in normal document flow */}
      <header className="gov-site-header">
        {/* 1. Indian Tricolor Top Accent Strip */}
        <div className="gov-tricolor-strip" />

        {/* 2. Official Top Utility / Accessibility Bar */}
        <div className="gov-top-bar">
        <div className="container">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontWeight: '600', color: '#f3f4f6' }}>
              {lang === 'hi' ? 'मध्य प्रदेश शासन' : 'Government of Madhya Pradesh'}
            </span>
            <span style={{ color: '#4b5563' }}>|</span>
            <span style={{ color: '#9ca3af' }}>
              {lang === 'hi' ? 'लोक सेवा प्रबंधन विभाग' : 'Public Grievance Redressal Mission'}
            </span>
          </div>

          <div className="gov-top-bar-links">
            <a
              href="#main-content"
              style={{ color: '#9ca3af', textDecoration: 'none', fontSize: '0.72rem' }}
            >
              Skip to Main Content
            </a>
            <span style={{ color: '#4b5563' }}>|</span>
            <button
              onClick={toggleLanguage}
              className="gov-top-btn"
              title="Change Language"
            >
              <Globe size={12} />
              <strong>{lang === 'en' ? 'हिन्दी' : 'English'}</strong>
            </button>
          </div>
        </div>
      </div>

      {/* 3. Main Government Branding Banner */}
      <div className="gov-main-header">
        <div className="container gov-branding-row">
          <Link href="/" onClick={closeMenu} className="gov-brand-left">
            <div className="gov-emblem-box">
              <Image
                src="/logo.png"
                alt="JanSeva AI Emblem"
                width={48}
                height={48}
                style={{ objectFit: 'contain' }}
                priority
              />
            </div>
            <div className="gov-brand-text">
              <h1>JanSeva AI</h1>
              <div className="subtext-hi">
                जनसेवा AI - नागरिक सेवा एवं शिकायत निवारण पोर्टल
              </div>
              <div className="subtext-en">
                Government of Madhya Pradesh &bull; MPOnline Integrated
              </div>
            </div>
          </Link>

          {/* Right Header Badges: CM Helpline & Digital India */}
          <div className="gov-header-badges">
            <div className="gov-helpline-pill">
              <PhoneCall size={18} color="#92400e" />
              <div>
                <div style={{ fontSize: '0.675rem', fontWeight: '700', textTransform: 'uppercase' }}>
                  CM Helpline
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: '800', lineHeight: '1', color: '#78350f' }}>
                  181 (Toll Free)
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <span
                style={{
                  fontSize: '0.65rem',
                  background: '#ecfdf5',
                  color: '#065f46',
                  border: '1px solid #a7f3d0',
                  padding: '2px 8px',
                  borderRadius: '2px',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                55 Districts Online
              </span>
              <span style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>
                Time-Bound Redressal
              </span>
            </div>
          </div>
        </div>
      </div>
      </header>

      {/* 4. Primary Government Navigation Bar (Deep Navy) */}
      <nav className="gov-nav-bar">
        <div className="container gov-nav-container">
          <div className="desktop-only" style={{ display: 'flex', alignItems: 'center' }}>
            <ul className="gov-nav-links">
              <li>
                <Link
                  href="/"
                  className={`gov-nav-link ${pathname === '/' ? 'active' : ''}`}
                >
                  <Home size={15} /> {t('nav_home')}
                </Link>
              </li>
              <li>
                <Link
                  href="/submit"
                  className={`gov-nav-link accent ${pathname === '/submit' ? 'active' : ''}`}
                >
                  <PlusCircle size={15} /> File Grievance (शिकायत दर्ज करें)
                </Link>
              </li>
              <li>
                <Link
                  href="/track"
                  className={`gov-nav-link ${pathname === '/track' ? 'active' : ''}`}
                >
                  <Search size={15} /> Track Grievance (स्थिति जानें)
                </Link>
              </li>
              <li>
                <Link
                  href="/#analytics"
                  className={`gov-nav-link ${pathname === '/#analytics' ? 'active' : ''}`}
                >
                  <BarChart2 size={15} /> Public Analytics
                </Link>
              </li>
            </ul>
          </div>

          {/* User Auth & Language Buttons in Nav */}
          <div className="desktop-only" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {/* Bilingual Language Switcher in Nav Bar */}
            <button
              onClick={toggleLanguage}
              className="gov-top-btn"
              title="Change Language"
              style={{
                padding: '0.35rem 0.65rem',
                fontSize: '0.78rem',
                borderColor: 'rgba(255,255,255,0.25)',
                background: 'rgba(255,255,255,0.08)',
                color: '#f8fafc',
                marginRight: '0.25rem',
              }}
            >
              <Globe size={13} />
              <strong>{lang === 'en' ? 'हिन्दी' : 'English'}</strong>
            </button>
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Link
                  href={getDashboardRoute()}
                  className="btn"
                  style={{
                    background: '#ffffff',
                    color: 'var(--gov-navy)',
                    fontSize: '0.8rem',
                    padding: '0.35rem 0.75rem',
                    fontWeight: '700',
                  }}
                >
                  <FileText size={14} /> {t('nav_dashboard')} ({user.role})
                </Link>
                <button
                  onClick={() => {
                    logout();
                    router.push('/');
                  }}
                  className="btn"
                  style={{
                    background: 'transparent',
                    color: '#f8fafc',
                    borderColor: '#334e68',
                    fontSize: '0.8rem',
                    padding: '0.35rem 0.65rem',
                  }}
                >
                  <LogOut size={14} /> {t('nav_logout')}
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Link
                  href="/login"
                  className="btn"
                  style={{
                    background: '#164e80',
                    color: '#ffffff',
                    borderColor: '#1d70b8',
                    fontSize: '0.8rem',
                    padding: '0.35rem 0.75rem',
                  }}
                >
                  Official / Citizen Login
                </Link>
                <Link
                  href="/register"
                  className="btn"
                  style={{
                    background: '#ffffff',
                    color: 'var(--gov-navy)',
                    fontSize: '0.8rem',
                    padding: '0.35rem 0.75rem',
                    fontWeight: '700',
                  }}
                >
                  New Registration
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Hamburger Toggle */}
          <button
            className="mobile-only-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
            style={{ color: '#ffffff', padding: '0.4rem', display: 'none' }}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div
            style={{
              background: '#0a2135',
              borderTop: '1px solid #1f3a52',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            <Link
              href="/"
              onClick={closeMenu}
              className="gov-nav-link"
              style={{ padding: '0.5rem 0' }}
            >
              <Home size={16} /> {t('nav_home')}
            </Link>
            <Link
              href="/submit"
              onClick={closeMenu}
              className="gov-nav-link accent"
              style={{ padding: '0.5rem 0.75rem' }}
            >
              <PlusCircle size={16} /> File Grievance (शिकायत दर्ज करें)
            </Link>
            <Link
              href="/track"
              onClick={closeMenu}
              className="gov-nav-link"
              style={{ padding: '0.5rem 0' }}
            >
              <Search size={16} /> Track Grievance (स्थिति जानें)
            </Link>
            {user ? (
              <div style={{ paddingTop: '0.5rem', borderTop: '1px solid #1e3a5f' }}>
                <Link
                  href={getDashboardRoute()}
                  onClick={closeMenu}
                  className="gov-nav-link"
                >
                  <FileText size={16} /> {t('nav_dashboard')} ({user.role})
                </Link>
                <button
                  onClick={() => {
                    closeMenu();
                    logout();
                    router.push('/');
                  }}
                  className="gov-nav-link"
                  style={{ width: '100%', textAlign: 'left', color: '#fca5a5' }}
                >
                  <LogOut size={16} /> {t('nav_logout')}
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                <Link
                  href="/login"
                  onClick={closeMenu}
                  className="btn btn-outline"
                  style={{ flex: 1, textAlign: 'center', fontSize: '0.85rem' }}
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  onClick={closeMenu}
                  className="btn btn-primary"
                  style={{ flex: 1, textAlign: 'center', fontSize: '0.85rem' }}
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        )}
      </nav>

      {/* 5. Notice Ticker Bar */}
      <div className="gov-ticker-strip">
        <div className="container gov-ticker-content">
          <span className="gov-ticker-badge">
            <BellRing size={12} style={{ display: 'inline', marginRight: '3px' }} />
            सूचना / Notice
          </span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            नागरिक सेवाओं एवं शिकायतों का समयबद्ध निराकरण मध्य प्रदेश लोक सेवा गारंटी अधिनियम के अंतर्गत अनिवार्य है। आपातकालीन सहायता हेतु 181 पर संपर्क करें।
          </span>
        </div>
      </div>

      <style>{`
        @media (max-width: 860px) {
          .desktop-only { display: none !important; }
          .mobile-only-toggle { display: block !important; }
          .gov-header-badges { display: none !important; }
          .gov-brand-text h1 { font-size: 1.15rem !important; }
        }
      `}</style>
    </>
  );
};

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { PhoneCall, Mail, ExternalLink, ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="gov-footer">
      <div className="container" style={{ padding: '2.5rem 1.25rem 2rem' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '2rem',
          }}
        >
          {/* Column 1: About Government Portal */}
          <div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                marginBottom: '0.85rem',
              }}
            >
              <div
                style={{
                  background: '#ffffff',
                  padding: '3px',
                  borderRadius: '2px',
                  display: 'inline-flex',
                }}
              >
                <Image
                  src="/logo.png"
                  alt="JanSeva AI"
                  width={28}
                  height={28}
                  style={{ objectFit: 'contain' }}
                />
              </div>
              <span
                style={{
                  color: '#ffffff',
                  fontWeight: '800',
                  fontSize: '1.15rem',
                  letterSpacing: '0.02em',
                }}
              >
                JanSeva AI
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', lineHeight: '1.6', color: '#94a3b8' }}>
              आधिकारिक नागरिक शिकायत निवारण पोर्टल - मध्य प्रदेश शासन। लोक सेवा गारंटी अधिनियम के अंतर्गत सभी 55 जिलों में पारदर्शी, जवाबदेह एवं समयबद्ध नागरिक समाधान।
            </p>
            <div style={{ marginTop: '0.85rem', fontSize: '0.75rem', color: '#64748b' }}>
              ISO 9001:2015 Compliant Grievance Governance
            </div>
          </div>

          {/* Column 2: Government Links & Policies */}
          <div>
            <div
              style={{
                color: '#ffffff',
                fontWeight: '700',
                fontSize: '0.9rem',
                marginBottom: '0.85rem',
                borderBottom: '2px solid #1e3a5f',
                paddingBottom: '0.35rem',
              }}
            >
              नागरिक सेवाएं एवं नीतियां (Quick Links)
            </div>
            <ul
              style={{
                listStyle: 'none',
                fontSize: '0.8rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.45rem',
              }}
            >
              <li>
                <Link href="/submit">File Grievance (शिकायत दर्ज करें)</Link>
              </li>
              <li>
                <Link href="/track">Track Status (शिकायत की स्थिति)</Link>
              </li>
              <li>
                <Link href="/#analytics">Public Analytics (सार्वजनिक आंकड़े)</Link>
              </li>
              <li>
                <Link href="/login">Officer / Admin Access Portal</Link>
              </li>
              <li>
                <a href="#charter">Citizen's Charter (नागरिक अधिकार पत्र)</a>
              </li>
            </ul>
          </div>

          {/* Column 3: Important Government Helplines */}
          <div>
            <div
              style={{
                color: '#ffffff',
                fontWeight: '700',
                fontSize: '0.9rem',
                marginBottom: '0.85rem',
                borderBottom: '2px solid #1e3a5f',
                paddingBottom: '0.35rem',
              }}
            >
              महत्वपूर्ण हेल्पलाइन (Emergency Helplines)
            </div>
            <div
              style={{
                fontSize: '0.8rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <PhoneCall size={14} color="#f59e0b" /> CM Helpline:{' '}
                <strong style={{ color: '#ffffff' }}>181</strong> (Toll Free)
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <PhoneCall size={14} color="#f59e0b" /> Emergency Response:{' '}
                <strong style={{ color: '#ffffff' }}>112</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <PhoneCall size={14} color="#f59e0b" /> Women Helpline:{' '}
                <strong style={{ color: '#ffffff' }}>1090</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Mail size={14} color="#f59e0b" /> Support:{' '}
                <strong style={{ color: '#ffffff' }}>grievance@mp.gov.in</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mandatory NIC Style Legal Footer Bottom */}
      <div className="gov-footer-bottom">
        <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            Website Content Managed by <strong>Department of Public Grievance Redressal, Government of Madhya Pradesh</strong>.
          </div>
          <div>
            Designed, Developed and Hosted by <strong>JanSeva AI Tech Team</strong> &bull; Version 1.0.0
          </div>
        </div>
      </div>
    </footer>
  );
};

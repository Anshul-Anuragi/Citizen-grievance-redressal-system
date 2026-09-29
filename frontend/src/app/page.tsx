'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useLanguage } from '../contexts/LanguageContext';
import { PublicAnalyticsChart } from '../components/PublicAnalyticsChart';
import api from '../services/api';
import { PublicAnalytics } from '../types';
import {
  FilePlus,
  Shield,
  Search,
  CheckCircle2,
  Clock,
  ArrowRight,
  FileCheck,
  Send,
  Users,
  AlertCircle,
  HelpCircle,
  BarChart3,
} from 'lucide-react';

export default function HomePage() {
  const { t, lang } = useLanguage();
  const router = useRouter();
  const [analytics, setAnalytics] = useState<PublicAnalytics | null>(null);

  // Quick Tracker in Hero
  const [quickComplaintNo, setQuickComplaintNo] = useState('');
  const [quickTrackingCode, setQuickTrackingCode] = useState('');

  useEffect(() => {
    const fetchPublicAnalytics = async () => {
      try {
        const res = await api.get('/analytics/public');
        setAnalytics(res.data);
      } catch (err) {
        console.error('Failed to load public analytics:', err);
      }
    };
    fetchPublicAnalytics();
  }, []);

  const handleQuickTrack = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickComplaintNo && quickTrackingCode) {
      router.push(`/track?complaint_no=${encodeURIComponent(quickComplaintNo.trim())}&code=${encodeURIComponent(quickTrackingCode.trim())}`);
    } else {
      router.push('/track');
    }
  };

  return (
    <div id="main-content">
      {/* 1. Government Hero Section */}
      <section
        style={{
          background: 'linear-gradient(180deg, #e8f1f8 0%, #f4f6f9 100%)',
          borderBottom: '1px solid var(--border-strong)',
          padding: '2.5rem 0 2rem 0',
        }}
      >
        <div className="container">
          <div style={{ maxWidth: '820px', marginBottom: '2rem' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem',
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                padding: '0.25rem 0.75rem',
                borderRadius: '2px',
                fontSize: '0.78rem',
                fontWeight: '700',
                color: 'var(--gov-navy)',
                marginBottom: '0.85rem',
              }}
            >
              <Shield size={14} color="#047857" />
              <span>मध्य प्रदेश लोक सेवा गारंटी एवं जन शिकायत निवारण पोर्टल</span>
            </div>

            <h1
              style={{
                fontSize: '2.1rem',
                lineHeight: '1.25',
                color: 'var(--gov-navy-dark)',
                fontWeight: '800',
                marginBottom: '0.65rem',
              }}
            >
              जनसेवा AI - नागरिक सेवा एवं शिकायत निवारण
            </h1>
            <p
              style={{
                fontSize: '1.025rem',
                color: 'var(--text-secondary)',
                lineHeight: '1.6',
              }}
            >
              मध्य प्रदेश के सभी 55 जिलों के नागरिकों के लिए पारदर्शी, जवाबदेह और समयबद्ध जन-शिकायत निवारण प्रणाली। आर्टिफिशियल इंटेलिजेंस द्वारा स्वतः वर्गीकरण एवं समय-सीमा (SLA) आधारित निगरानी।
            </p>
          </div>

          {/* 2. Three Primary Citizen Service Counters */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
              gap: '1.25rem',
            }}
          >
            {/* Service Counter 1: File Grievance */}
            <div className="gov-service-box highlight">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.75rem' }}>
                <div
                  style={{
                    background: '#ffedd5',
                    color: '#c2410c',
                    width: '38px',
                    height: '38px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '2px',
                  }}
                >
                  <FilePlus size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.05rem', color: 'var(--gov-navy)', fontWeight: '700' }}>
                    शिकायत दर्ज करें (File Grievance)
                  </h3>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>For Registered Citizens</div>
                </div>
              </div>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', flex: 1, marginBottom: '1.25rem' }}>
                लॉगिन करके अपनी नागरिक समस्या दर्ज करें। आपको सीधे संबंधित जिले के विभागीय अधिकारी से संवाद एवं अपडेट प्राप्त होंगे।
              </p>
              <Link href="/submit" className="btn btn-saffron" style={{ width: '100%' }}>
                शिकायत पंजीकरण करें <ArrowRight size={15} />
              </Link>
            </div>

            {/* Service Counter 2: File Anonymous */}
            <div className="gov-service-box">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.75rem' }}>
                <div
                  style={{
                    background: '#e0f2fe',
                    color: '#0369a1',
                    width: '38px',
                    height: '38px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '2px',
                  }}
                >
                  <Shield size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.05rem', color: 'var(--gov-navy)', fontWeight: '700' }}>
                    अनाम शिकायत (Anonymous Grievance)
                  </h3>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Without Creating Account</div>
                </div>
              </div>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', flex: 1, marginBottom: '1.25rem' }}>
                बिना खाता बनाए गोपनीय रूप से शिकायत दर्ज करें। आपको सुरक्षित ट्रैकिंग कोड एवं शिकायत संख्या प्राप्त होगी।
              </p>
              <Link href="/submit?anonymous=true" className="btn btn-outline" style={{ width: '100%' }}>
                गोपनीय शिकायत दर्ज करें <ArrowRight size={15} />
              </Link>
            </div>

            {/* Service Counter 3: Instant Status Tracker Form */}
            <div className="gov-service-box green">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.75rem' }}>
                <div
                  style={{
                    background: '#dcfce7',
                    color: '#15803d',
                    width: '38px',
                    height: '38px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '2px',
                  }}
                >
                  <Search size={20} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.05rem', color: 'var(--gov-navy)', fontWeight: '700' }}>
                    स्थिति जानें (Track Status)
                  </h3>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Check Progress Instantly</div>
                </div>
              </div>

              <form onSubmit={handleQuickTrack} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                <input
                  type="text"
                  placeholder="Complaint ID (उदा: IND-GRV-2026-0001)"
                  className="form-input"
                  style={{ fontSize: '0.8rem', padding: '0.45rem 0.65rem' }}
                  value={quickComplaintNo}
                  onChange={(e) => setQuickComplaintNo(e.target.value)}
                />
                <input
                  type="text"
                  placeholder="Tracking Code (उदा: TRK-98A4B2)"
                  className="form-input"
                  style={{ fontSize: '0.8rem', padding: '0.45rem 0.65rem' }}
                  value={quickTrackingCode}
                  onChange={(e) => setQuickTrackingCode(e.target.value)}
                />
                <button type="submit" className="btn btn-green" style={{ width: '100%', marginTop: 'auto' }}>
                  स्थिति देखें <Search size={14} />
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Official Governance Metrics Counter Strip */}
      <section style={{ background: '#ffffff', borderBottom: '1px solid var(--border-strong)', padding: '1.75rem 0' }}>
        <div className="container">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '1rem',
              textAlign: 'center',
            }}
          >
            <div style={{ padding: '0.85rem', borderRight: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                कुल प्राप्त शिकायतें (Total Received)
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: 'var(--gov-navy)', marginTop: '0.25rem' }}>
                {analytics ? analytics.total_complaints.toLocaleString() : '---'}
              </div>
            </div>

            <div style={{ padding: '0.85rem', borderRight: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                प्रगति पर (In Progress Actions)
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: '#1d70b8', marginTop: '0.25rem' }}>
                {analytics ? analytics.in_progress_complaints.toLocaleString() : '---'}
              </div>
            </div>

            <div style={{ padding: '0.85rem', borderRight: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                निराकृत शिकायतें (Disposed / Resolved)
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: 'var(--gov-green)', marginTop: '0.25rem' }}>
                {analytics ? analytics.resolved_complaints.toLocaleString() : '---'}
              </div>
            </div>

            <div style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                निराकरण दर (SLA Compliance)
              </div>
              <div style={{ fontSize: '2rem', fontWeight: '800', color: '#b45309', marginTop: '0.25rem' }}>
                {analytics ? `${analytics.resolution_rate_percent}%` : '---'}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Citizens Charter & 4-Step Grievance Redressal Process */}
      <section style={{ padding: '3rem 0', background: 'var(--gov-bg)' }}>
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
            <span
              style={{
                fontSize: '0.75rem',
                color: 'var(--gov-navy)',
                fontWeight: '700',
                background: '#e0f2fe',
                padding: '3px 8px',
                borderRadius: '2px',
                textTransform: 'uppercase',
              }}
            >
              पारदर्शी समाधान प्रक्रिया (How It Works)
            </span>
            <h2 style={{ fontSize: '1.65rem', color: 'var(--gov-navy-dark)', marginTop: '0.5rem', fontWeight: '800' }}>
              चार-चरणीय शिकायत निवारण कार्यप्रणाली
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: '640px', margin: '0.35rem auto 0' }}>
              मध्य प्रदेश लोक सेवा गारंटी अधिनियम के तहत प्रत्येक चरण की समय-सीमा निश्चित है।
            </p>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '1.25rem',
            }}
          >
            <div className="card" style={{ borderTop: '3px solid var(--gov-navy)' }}>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                01
              </div>
              <h3 style={{ fontSize: '1rem', color: 'var(--gov-navy)', fontWeight: '700', marginBottom: '0.45rem' }}>
                शिकायत पंजीकरण (Submission)
              </h3>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                नागरिक पोर्टल पर फोटो, दस्तावेज या विवरण के साथ शिकायत दर्ज करते हैं। तत्काल शिकायत संख्या एवं पावती जारी होती है।
              </p>
            </div>

            <div className="card" style={{ borderTop: '3px solid #1d70b8' }}>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                02
              </div>
              <h3 style={{ fontSize: '1rem', color: 'var(--gov-navy)', fontWeight: '700', marginBottom: '0.45rem' }}>
                AI वर्गीकरण एवं अग्रेषण (Routing)
              </h3>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                JanSeva AI द्वारा शिकायत की गंभीरता एवं विभाग (PWD, PHE, MPPKVVCL, नगर निगम) का स्वतः निर्धारण कर सक्षम अधिकारी को प्रेषण।
              </p>
            </div>

            <div className="card" style={{ borderTop: '3px solid #f59e0b' }}>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                03
              </div>
              <h3 style={{ fontSize: '1rem', color: 'var(--gov-navy)', fontWeight: '700', marginBottom: '0.45rem' }}>
                क्षेत्रीय कार्यवाही (Investigation)
              </h3>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                जिला अधिकारी द्वारा स्थल निरीक्षण, तकनीकी सुधार एवं निवारण। नागरिक एवं अधिकारी के बीच सीधा संवाद उपलब्ध।
              </p>
            </div>

            <div className="card" style={{ borderTop: '3px solid var(--gov-green)' }}>
              <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#cbd5e1', marginBottom: '0.5rem' }}>
                04
              </div>
              <h3 style={{ fontSize: '1rem', color: 'var(--gov-navy)', fontWeight: '700', marginBottom: '0.45rem' }}>
                निराकरण एवं संतुष्टि फीडबैक (Resolution)
              </h3>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                कार्य पूर्ण होने पर विस्तृत विवरण अपलोड होता है। असंतुष्टि की स्थिति में नागरिक जिला कलेक्टर/प्रशासक से पुनः खोलने का अनुरोध कर सकते हैं।
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Public Analytics & Transparency Section */}
      <section id="analytics" style={{ padding: '3rem 0', background: '#ffffff', borderTop: '1px solid var(--border-strong)' }}>
        <div className="container">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <span
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--gov-navy)',
                  fontWeight: '700',
                  background: '#fef3c7',
                  padding: '3px 8px',
                  borderRadius: '2px',
                  textTransform: 'uppercase',
                }}
              >
                सार्वजनिक पारदर्शिता (Public Transparency)
              </span>
              <h2 style={{ fontSize: '1.65rem', color: 'var(--gov-navy-dark)', marginTop: '0.35rem', fontWeight: '800' }}>
                विभागीय श्रेणीवार आंकड़े एवं प्रवृत्तियां
              </h2>
            </div>

            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              अद्यतन: {new Date().toLocaleDateString('hi-IN', { year: 'numeric', month: 'long', day: 'numeric' })}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
            {/* Chart Card */}
            <div className="card">
              <div className="card-gov-header">
                <div className="card-gov-title">
                  <BarChart3 size={18} color="var(--gov-navy)" />
                  मुख्य नागरिक समस्याएं (Top Civic Categories)
                </div>
              </div>

              {analytics && analytics.category_trends ? (
                <PublicAnalyticsChart data={analytics.category_trends} />
              ) : (
                <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  लोड हो रहा है... (Loading analytics)
                </div>
              )}
            </div>

            {/* Performance Summary Table */}
            <div className="card">
              <div className="card-gov-header">
                <div className="card-gov-title">
                  <CheckCircle2 size={18} color="var(--gov-green)" />
                  निराकरण प्रदर्शन विवरणी (Disposal Performance)
                </div>
              </div>

              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>मापदंड (Metric)</th>
                      <th>संख्या (Count)</th>
                      <th>स्थिति (Status)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>कुल शिकायतें (Total Received)</td>
                      <td style={{ fontWeight: '700' }}>{analytics?.total_complaints || 0}</td>
                      <td><span className="badge badge-submitted">दर्ज</span></td>
                    </tr>
                    <tr>
                      <td>प्रगतिरत कार्यवाही (Under Action)</td>
                      <td style={{ fontWeight: '700', color: '#1d70b8' }}>{analytics?.in_progress_complaints || 0}</td>
                      <td><span className="badge badge-in-progress">प्रगति पर</span></td>
                    </tr>
                    <tr>
                      <td>सफलतापूर्वक निराकृत (Resolved)</td>
                      <td style={{ fontWeight: '700', color: 'var(--gov-green)' }}>{analytics?.resolved_complaints || 0}</td>
                      <td><span className="badge badge-resolved">निराकृत</span></td>
                    </tr>
                    <tr>
                      <td>समग्र निवारण दर (Overall Rate)</td>
                      <td style={{ fontWeight: '800', color: '#b45309' }}>{analytics ? `${analytics.resolution_rate_percent}%` : '0%'}</td>
                      <td><span className="badge badge-medium">सक्रिय</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <CheckCircle2 size={14} color="var(--gov-green)" />
                सभी 55 जिलों का डेटा आइसोलेशन एवं सुरक्षा मानकों के अनुरूप सुरक्षित है।
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Citizen Charter Service Standards Table */}
      <section id="charter" style={{ padding: '3rem 0', background: 'var(--gov-bg)', borderTop: '1px solid var(--border-strong)' }}>
        <div className="container">
          <div style={{ marginBottom: '1.5rem' }}>
            <span
              style={{
                fontSize: '0.75rem',
                color: 'var(--gov-navy)',
                fontWeight: '700',
                background: '#e2e8f0',
                padding: '3px 8px',
                borderRadius: '2px',
                textTransform: 'uppercase',
              }}
            >
              नागरिक अधिकार पत्र (Citizen's Charter)
            </span>
            <h2 style={{ fontSize: '1.65rem', color: 'var(--gov-navy-dark)', marginTop: '0.35rem', fontWeight: '800' }}>
              विभागीय सेवा मानक एवं समय-सीमा (SLA Matrix)
            </h2>
          </div>

          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>विभाग (Department)</th>
                  <th>सेवा / समस्या का प्रकार (Grievance Category)</th>
                  <th>सामान्य प्राथमिकता (Default Priority)</th>
                  <th>अधिकतम निवारण समय (Max SLA)</th>
                  <th>प्रथम अपीलीय प्राधिकारी (Escalation)</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>लोक स्वास्थ्य यांत्रिकी (PHE)</td>
                  <td>पेयजल आपूर्ति एवं पाइपलाइन लीकेज (Drinking Water)</td>
                  <td><span className="badge badge-high">High</span></td>
                  <td><strong>48 घंटे (2 Days)</strong></td>
                  <td>कार्यपालन यंत्री / जिला कलेक्टर</td>
                </tr>
                <tr>
                  <td>विद्युत वितरण कंपनी (MPPKVVCL)</td>
                  <td>ट्रांसफार्मर खराबी एवं बिजली कटौती (Power Outage)</td>
                  <td><span className="badge badge-high">High</span></td>
                  <td><strong>24 घंटे (1 Day)</strong></td>
                  <td>सहायक यंत्री / अधीक्षण यंत्री</td>
                </tr>
                <tr>
                  <td>लोक निर्माण विभाग (PWD)</td>
                  <td>सड़क गड्ढे एवं मरम्मत (Road Repair)</td>
                  <td><span className="badge badge-medium">Medium</span></td>
                  <td><strong>7 कार्यदिवस (7 Days)</strong></td>
                  <td>अनुविभागीय अधिकारी (SDO PWD)</td>
                </tr>
                <tr>
                  <td>नगरीय प्रशासन (Urban Administration)</td>
                  <td>कचरा उठान एवं नाली सफाई (Garbage & Sewage)</td>
                  <td><span className="badge badge-medium">Medium</span></td>
                  <td><strong>48 घंटे (2 Days)</strong></td>
                  <td>मुख्य नगर पालिका अधिकारी (CMO)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

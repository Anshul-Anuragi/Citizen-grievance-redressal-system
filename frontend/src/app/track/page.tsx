'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import api from '../../services/api';
import { StatusBadge } from '../../components/StatusBadge';
import { PriorityBadge } from '../../components/PriorityBadge';
import { Complaint } from '../../types';
import {
  Search,
  Shield,
  Clock,
  Send,
  MessageSquare,
  AlertCircle,
  Printer,
  CheckCircle,
  FileText,
} from 'lucide-react';

const anonymousAuth = () => ({
  headers: {
    Authorization: `Bearer ${
      typeof window !== 'undefined' ? sessionStorage.getItem('anon_token') : ''
    }`,
  },
});

function TrackContent() {
  const searchParams = useSearchParams();
  const initialNo = searchParams.get('complaint_no') || '';
  const initialCode = searchParams.get('code') || '';

  const [complaintNo, setComplaintNo] = useState(initialNo);
  const [trackingCode, setTrackingCode] = useState(initialCode);
  const [complaint, setComplaint] = useState<Complaint | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [newMessage, setNewMessage] = useState('');

  const executeTrack = async (noToTrack: string, codeToTrack: string) => {
    setError('');
    setLoading(true);

    try {
      // 1. Authenticate tracking credentials to get session token
      const authRes = await api.post('/complaints/track-anonymous', {
        complaint_no: noToTrack.trim().toUpperCase(),
        tracking_code: codeToTrack.trim(),
      });

      if (typeof window !== 'undefined') {
        sessionStorage.setItem('anon_token', authRes.data.access_token);
      }

      // 2. Fetch Detail
      const detailRes = await api.get(
        `/complaints/${authRes.data.complaint_no}`,
        anonymousAuth()
      );
      setComplaint(detailRes.data);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 'अवैध शिकायत संख्या या गोपनीय ट्रैकिंग कोड। कृपया पुनः जांचें।'
      );
      setComplaint(null);
    } finally {
      setLoading(false);
    }
  };

  const handleTrackSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeTrack(complaintNo, trackingCode);
  };

  useEffect(() => {
    if (initialNo && initialCode) {
      executeTrack(initialNo, initialCode);
    }
  }, [initialNo, initialCode]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !complaint) return;
    try {
      const res = await api.post(
        `/complaints/${complaint.id}/messages`,
        { message: newMessage },
        anonymousAuth()
      );
      setComplaint(res.data);
      setNewMessage('');
    } catch {
      alert('संदेश भेजने में त्रुटि हुई।');
    }
  };

  return (
    <div className="container" style={{ maxWidth: '860px', padding: '2.5rem 1.25rem 3.5rem' }}>
      {/* Breadcrumb Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
          <Link href="/" style={{ color: 'var(--gov-navy)' }}>मुख्य पृष्ठ (Home)</Link> &gt; शिकायत स्थिति ट्रैकर
        </div>
        <h1 style={{ fontSize: '1.75rem', color: 'var(--gov-navy-dark)', fontWeight: '800' }}>
          शिकायत निवारण स्थिति ट्रैकर (Track Grievance Status)
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          अपनी शिकायत संख्या एवं गुप्त ट्रैकिंग कोड दर्ज कर वर्तमान स्थिति एवं विभागीय कार्यवाही देखें।
        </p>
      </div>

      {/* Tracker Search Box */}
      <div className="card" style={{ marginBottom: '2rem', borderTop: '4px solid var(--gov-navy)' }}>
        {error && (
          <div
            style={{
              background: '#fee2e2',
              color: '#991b1b',
              border: '1px solid #fecaca',
              padding: '0.75rem 1rem',
              fontSize: '0.85rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <form
          onSubmit={handleTrackSubmit}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr)) auto',
            gap: '1rem',
            alignItems: 'end',
          }}
        >
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">
              शिकायत संख्या (Complaint ID)<span className="req">*</span>
            </label>
            <input
              type="text"
              required
              className="form-input"
              placeholder="उदा: IND-GRV-2026-000001"
              value={complaintNo}
              onChange={(e) => setComplaintNo(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">
              गोपनीय ट्रैकिंग कोड (Secret Tracking Code)<span className="req">*</span>
            </label>
            <input
              type="text"
              required
              className="form-input"
              placeholder="उदा: TRK-98A4B2"
              value={trackingCode}
              onChange={(e) => setTrackingCode(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ padding: '0.65rem 1.25rem', height: '38px' }}
          >
            <Search size={15} /> {loading ? 'खोज जारी...' : 'स्थिति खोजें'}
          </button>
        </form>
      </div>

      {/* Complaint Detail Sheet */}
      {complaint && (
        <div className="card" style={{ borderTop: '4px solid var(--gov-green)' }}>
          {/* Government Header Stamp */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              marginBottom: '1.25rem',
              borderBottom: '2px solid #e2e8f0',
              paddingBottom: '1rem',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                मध्य प्रदेश लोक सेवा अभिलेख (Official Status Sheet)
              </div>
              <h2 style={{ fontSize: '1.35rem', color: 'var(--gov-navy)', marginTop: '0.2rem', fontWeight: '800' }}>
                {complaint.subject}
              </h2>
              <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '0.15rem' }}>
                शिकायत संख्या: <strong style={{ fontFamily: 'monospace', color: 'var(--gov-navy)' }}>{complaint.complaint_no}</strong>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <StatusBadge status={complaint.status} />
              <PriorityBadge priority={complaint.priority} />
              <button
                type="button"
                onClick={() => window.print()}
                className="btn btn-outline"
                style={{ padding: '0.25rem 0.55rem', fontSize: '0.75rem' }}
                title="Print Status Sheet"
              >
                <Printer size={13} /> प्रिंट
              </button>
            </div>
          </div>

          {/* Metadata Table */}
          <div className="table-container" style={{ marginBottom: '1.5rem' }}>
            <table className="table">
              <tbody>
                <tr>
                  <th style={{ width: '25%' }}>ज़िला (District)</th>
                  <td><strong>{complaint.district_code}</strong></td>
                  <th style={{ width: '25%' }}>श्रेणी (Category)</th>
                  <td>{complaint.category?.name_en || 'नागरिक सेवा'}</td>
                </tr>
                <tr>
                  <th>घटना स्थल (Location)</th>
                  <td>{complaint.location_address}</td>
                  <th>SLA समय-सीमा (Deadline)</th>
                  <td style={{ color: complaint.is_overdue ? '#b91c1c' : 'inherit', fontWeight: '700' }}>
                    {new Date(complaint.sla_deadline).toLocaleString()} {complaint.is_overdue && '(समय समाप्त - OVERDUE)'}
                  </td>
                </tr>
                <tr>
                  <th>पंजीकरण दिनांक (Date)</th>
                  <td>{new Date(complaint.created_at).toLocaleString()}</td>
                  <th>नियुक्त अधिकारी (Assigned)</th>
                  <td>{complaint.assigned_officer_name || 'आवंटन प्रक्रियाधीन'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Description Box */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--gov-navy)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              शिकायत का मूल विवरण (Complaint Narrative)
            </h4>
            <div
              style={{
                fontSize: '0.875rem',
                color: '#334155',
                background: '#f8fafc',
                border: '1px solid #cbd5e1',
                padding: '0.85rem',
                lineHeight: '1.6',
              }}
            >
              {complaint.description}
            </div>
          </div>

          {/* Resolution Note if RESOLVED */}
          {complaint.resolution_summary && (
            <div
              style={{
                background: '#f0fdf4',
                border: '1px solid #bbf7d0',
                borderLeft: '4px solid var(--gov-green)',
                padding: '1rem',
                marginBottom: '1.5rem',
              }}
            >
              <h4 style={{ color: '#166534', fontSize: '0.95rem', fontWeight: '700', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <CheckCircle size={16} /> अंतिम निराकरण आख्या (Disposal Remarks)
              </h4>
              <p style={{ fontSize: '0.85rem', color: '#14532d', lineHeight: '1.5' }}>
                {complaint.resolution_summary}
              </p>
              {complaint.resolved_at && (
                <div style={{ fontSize: '0.75rem', color: '#166534', marginTop: '0.35rem' }}>
                  निराकरण दिनांक: {new Date(complaint.resolved_at).toLocaleString()}
                </div>
              )}
            </div>
          )}

          {/* Activity Audit Timeline */}
          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--gov-navy)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Clock size={15} /> कार्यवाही एवं गतिविधि इतिहास (Audit History)
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {complaint.status_history?.map((h) => (
                <div
                  key={h.id}
                  style={{
                    padding: '0.65rem 0.85rem',
                    borderLeft: '3px solid var(--gov-navy)',
                    background: '#fafbfc',
                    border: '1px solid #e2e8f0',
                    borderLeftWidth: '3px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>प्राधिकारी/भूमिका: <strong>{h.actor_role}</strong></span>
                    <span>{new Date(h.timestamp).toLocaleString()}</span>
                  </div>
                  <div style={{ fontWeight: '700', fontSize: '0.85rem', color: 'var(--gov-navy)', marginTop: '0.2rem' }}>
                    अद्यतन स्थिति: {h.new_status}
                  </div>
                  {h.remarks && (
                    <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.15rem' }}>
                      टिप्पणी: {h.remarks}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Officer-Citizen Direct Communication Thread */}
          <div>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--gov-navy)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <MessageSquare size={15} /> अधिकारी एवं नागरिक संवाद सूत्र (Communication Channel)
            </h4>

            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.65rem',
                marginBottom: '1rem',
                maxHeight: '240px',
                overflowY: 'auto',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                padding: '0.75rem',
              }}
            >
              {complaint.messages?.length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '1rem' }}>
                  अधिकारी द्वारा अभी कोई अतिरिक्त टिप्पणी नहीं भेजी गई है।
                </div>
              ) : (
                complaint.messages?.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      padding: '0.65rem 0.85rem',
                      background: m.sender_role === 'OFFICER' ? '#eff6ff' : '#ffffff',
                      border: '1px solid #cbd5e1',
                    }}
                  >
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                      <strong>{m.sender_role === 'OFFICER' ? 'विभागीय अधिकारी (Officer)' : 'नागरिक (Citizen)'}</strong> &bull;{' '}
                      {new Date(m.created_at).toLocaleString()}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#1e293b' }}>{m.message}</div>
                  </div>
                ))
              )}
            </div>

            <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                className="form-input"
                placeholder="अधिकारी को अतिरिक्त स्पष्टीकरण या उत्तर लिखें..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
              />
              <button type="submit" className="btn btn-primary" style={{ whiteSpace: 'nowrap' }}>
                <Send size={15} /> संदेश भेजें
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AnonymousTrackPage() {
  return (
    <Suspense
      fallback={
        <div style={{ padding: '4rem 1.5rem', textAlign: 'center', color: 'var(--gov-navy)' }}>
          ट्रैकर लोड हो रहा है... (Loading Tracker...)
        </div>
      }
    >
      <TrackContent />
    </Suspense>
  );
}

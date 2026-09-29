'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../../contexts/AuthContext';
import { AIRecommendationCard } from '../../components/AIRecommendationCard';
import api from '../../services/api';
import { Category, Department, AIRecommendation } from '../../types';
import { ALL_MP_DISTRICTS } from '../../constants/districts';
import {
  Send,
  Sparkles,
  AlertCircle,
  ShieldCheck,
  Upload,
  Info,
  CheckCircle2,
  Lock,
  User,
  Printer,
} from 'lucide-react';

function SubmitComplaintContent() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const isAnonQuery = searchParams.get('anonymous') === 'true';
  const [isAnonymous, setIsAnonymous] = useState(isAnonQuery || !user);

  const [districts, setDistricts] = useState(ALL_MP_DISTRICTS);
  const [categories, setCategories] = useState<Category[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [formData, setFormData] = useState({
    subject: '',
    description: '',
    district_code: 'IND',
    category_id: '',
    department_id: '',
    priority: 'MEDIUM' as 'LOW' | 'MEDIUM' | 'HIGH',
    location_address: '',
    contact_email: user?.email || '',
    contact_mobile: user?.mobile || '',
  });

  const [declarationChecked, setDeclarationChecked] = useState(false);
  const [recommendation, setRecommendation] = useState<AIRecommendation | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [anonSuccessData, setAnonSuccessData] = useState<any>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    if (user?.email && !formData.contact_email) {
      setFormData((prev) => ({
        ...prev,
        contact_email: user.email,
        contact_mobile: user.mobile || prev.contact_mobile,
      }));
    }
  }, [user]);

  useEffect(() => {
    const loadFormData = async () => {
      const results = await Promise.allSettled([
        api.get('/complaints/categories'),
        api.get('/complaints/districts'),
        api.get('/complaints/departments'),
      ]);

      const [catResult, distResult, deptResult] = results;

      if (catResult.status === 'fulfilled' && catResult.value.data?.length > 0) {
        const catList: Category[] = catResult.value.data;
        setCategories(catList);
        const firstCat = catList[0];
        const initialDeptId = firstCat.mappings?.[0]?.department_id || '';
        setFormData((prev) => ({
          ...prev,
          category_id: firstCat.id,
          department_id: prev.department_id || initialDeptId,
        }));
      }

      if (distResult.status === 'fulfilled' && distResult.value.data?.length > 0) {
        setDistricts(
          distResult.value.data.map((d: any) => ({
            code: d.code,
            name: d.name_en || d.name,
          }))
        );
      }

      if (deptResult.status === 'fulfilled' && deptResult.value.data?.length > 0) {
        setDepartments(deptResult.value.data);
      }
    };
    loadFormData();
  }, []);

  const handleCategoryChange = (catId: string) => {
    const selectedCat = categories.find((c) => c.id === catId);
    const targetDeptId =
      selectedCat?.mappings?.[0]?.department_id || formData.department_id;
    setFormData((prev) => ({
      ...prev,
      category_id: catId,
      department_id: targetDeptId,
    }));
  };

  const handleGetAiRecommendation = async () => {
    if (!formData.description || formData.description.length < 5) {
      setError('कृपया पहले समस्या का विवरण दर्ज करें ताकि AI तकनीकी श्रेणी का सुझाव दे सके।');
      return;
    }
    setError('');
    setAiLoading(true);
    try {
      const res = await api.post('/ai/recommend', {
        subject: formData.subject,
        description: formData.description,
      });
      setRecommendation(res.data);
    } catch (err) {
      console.error('AI Recommendation error:', err);
    } finally {
      setAiLoading(false);
    }
  };

  const handleApplyAiRecommendation = (rec: AIRecommendation) => {
    if (rec.suggested_category_id) {
      setFormData((prev) => ({
        ...prev,
        category_id: rec.suggested_category_id || prev.category_id,
        priority: rec.suggested_priority || prev.priority,
      }));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        setError('संलग्न फ़ाइल का आकार 10MB से अधिक नहीं होना चाहिए।');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!declarationChecked) {
      setError('कृपया स्व-घोषणा (Declaration) को स्वीकार करें।');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const payload = {
        ...formData,
        contact_email: formData.contact_email?.trim() || null,
        contact_mobile: formData.contact_mobile?.trim() || null,
      };

      let createdComplaintId: string | null = null;
      if (isAnonymous) {
        const res = await api.post('/complaints/submit-anonymous', payload);
        createdComplaintId = res.data.id;
        setAnonSuccessData(res.data);
      } else {
        const res = await api.post('/complaints/submit', payload);
        createdComplaintId = res.data.id;
      }

      if (selectedFile && createdComplaintId) {
        try {
          const fileData = new FormData();
          fileData.append('file', selectedFile);
          await api.post(
            `/attachments/upload?complaint_id=${createdComplaintId}`,
            fileData,
            {
              headers: { 'Content-Type': 'multipart/form-data' },
            }
          );
        } catch (uploadErr) {
          console.error('Attachment upload warning:', uploadErr);
        }
      }

      if (!isAnonymous && createdComplaintId) {
        router.push(`/complaints/${createdComplaintId}`);
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      let msg = 'शिकायत दर्ज करने में त्रुटि। कृपया सभी अनिवार्य फ़ील्ड जांचें।';
      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map((d: any) => d.msg || d.detail || JSON.stringify(d)).join(', ');
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // 1. Success Screen (Govt Acknowledgement Receipt)
  if (anonSuccessData) {
    return (
      <div className="container" style={{ maxWidth: '680px', padding: '3rem 1.25rem' }}>
        <div className="card" style={{ borderTop: '4px solid var(--gov-green)' }}>
          <div style={{ textAlign: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '1.25rem', marginBottom: '1.25rem' }}>
            <ShieldCheck size={44} color="#047857" style={{ margin: '0 auto 0.5rem auto' }} />
            <h2 style={{ fontSize: '1.45rem', color: 'var(--gov-navy)', fontWeight: '800' }}>
              शिकायत पावती रसीद (Grievance Registration Receipt)
            </h2>
            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
              मध्य प्रदेश लोक सेवा गारंटी पोर्टल &bull; JanSeva AI
            </div>
          </div>

          <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', padding: '1.25rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                  शिकायत संख्या (Complaint ID)
                </span>
                <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--gov-navy)', fontFamily: 'monospace' }}>
                  {anonSuccessData.complaint_no}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                  गोपनीय ट्रैकिंग कोड (Secret Tracking Code)
                </span>
                <div style={{ fontSize: '1.25rem', fontWeight: '800', color: '#b45309', fontFamily: 'monospace' }}>
                  {anonSuccessData.tracking_code}
                </div>
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', color: '#475569', lineHeight: '1.5', borderTop: '1px dashed #cbd5e1', paddingTop: '0.75rem' }}>
              ℹ️ <strong>महत्वपूर्ण निर्देश:</strong> कृपया इस शिकायत संख्या और ट्रैकिंग कोड को सुरक्षित नोट कर लें। इसके माध्यम से आप भविष्य में कभी भी अपनी शिकायत की प्रगति देख सकते हैं एवं विभागीय अधिकारी को अतिरिक्त विवरण भेज सकते हैं।
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => {
                if (typeof window !== 'undefined') {
                  sessionStorage.setItem('anon_token', anonSuccessData.anonymous_access_token);
                }
                router.push(`/track?complaint_no=${anonSuccessData.complaint_no}&code=${anonSuccessData.tracking_code}`);
              }}
              className="btn btn-primary"
              style={{ flex: 1 }}
            >
              शिकायत डैशबोर्ड देखें (Track Now)
            </button>
            <button
              onClick={() => window.print()}
              className="btn btn-outline"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Printer size={15} /> रसीद प्रिंट करें
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 2. Main Government Grievance Submission Form
  return (
    <div className="container" style={{ maxWidth: '800px', padding: '2.5rem 1.25rem 3.5rem' }}>
      {/* Breadcrumb / Section Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
          <Link href="/" style={{ color: 'var(--gov-navy)' }}>मुख्य पृष्ठ (Home)</Link> &gt; शिकायत पंजीकरण प्रपत्र
        </div>
        <h1 style={{ fontSize: '1.75rem', color: 'var(--gov-navy-dark)', fontWeight: '800' }}>
          लोक शिकायत पंजीकरण प्रपत्र (Public Grievance Form)
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          मध्य प्रदेश शासन के संबंधित जिला प्रशासन एवं विभाग को अपनी समस्या सीधे प्रेषित करें।
        </p>
      </div>

      {/* Advisory Notice Banner */}
      <div
        style={{
          background: '#fffbeb',
          border: '1px solid #fde68a',
          borderLeft: '4px solid #f59e0b',
          padding: '0.75rem 1rem',
          fontSize: '0.825rem',
          color: '#92400e',
          marginBottom: '1.5rem',
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'flex-start',
        }}
      >
        <Info size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong>नागरिकों हेतु दिशा-निर्देश:</strong> कृपया सही जिला एवं सटीक पता दर्ज करें। भ्रामक या असत्य जानकारी दर्ज करने पर शिकायत निरस्त की जा सकती है। आपातकालीन सहायता हेतु सीधे <strong>181</strong> पर कॉल करें।
        </div>
      </div>

      <div className="card" style={{ borderTop: '4px solid var(--gov-navy)' }}>
        {/* Mode Selector Tabs (Registered vs Anonymous) */}
        <div
          style={{
            display: 'flex',
            borderBottom: '2px solid #e2e8f0',
            marginBottom: '1.5rem',
            gap: '0.5rem',
          }}
        >
          <button
            type="button"
            onClick={() => setIsAnonymous(false)}
            style={{
              padding: '0.65rem 1rem',
              fontSize: '0.875rem',
              fontWeight: '700',
              borderBottom: !isAnonymous ? '3px solid var(--gov-navy)' : '3px solid transparent',
              color: !isAnonymous ? 'var(--gov-navy)' : 'var(--text-muted)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              background: 'none',
              cursor: 'pointer',
            }}
          >
            <User size={16} /> पंजीकृत नागरिक (Registered Citizen)
          </button>

          <button
            type="button"
            onClick={() => setIsAnonymous(true)}
            style={{
              padding: '0.65rem 1rem',
              fontSize: '0.875rem',
              fontWeight: '700',
              borderBottom: isAnonymous ? '3px solid var(--gov-navy)' : '3px solid transparent',
              color: isAnonymous ? 'var(--gov-navy)' : 'var(--text-muted)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              background: 'none',
              cursor: 'pointer',
            }}
          >
            <Lock size={16} /> गोपनीय / अनाम नागरिक (Anonymous Mode)
          </button>
        </div>

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

        <form onSubmit={handleSubmit}>
          {/* Section 1: Departmental Routing */}
          <div style={{ marginBottom: '1.5rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '1rem' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: '800', color: 'var(--gov-navy)', marginBottom: '0.85rem' }}>
              1. क्षेत्राधिकार एवं विभागीय वर्गीकरण (Jurisdiction & Category)
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">
                  ज़िला चुनें (District)<span className="req">*</span>
                </label>
                <select
                  required
                  className="form-select"
                  value={formData.district_code}
                  onChange={(e) => setFormData({ ...formData, district_code: e.target.value })}
                >
                  {districts.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
                <div className="form-help">मध्य प्रदेश के सभी 55 जिले उपलब्ध हैं।</div>
              </div>

              <div className="form-group">
                <label className="form-label">
                  समस्या की श्रेणी (Category)<span className="req">*</span>
                </label>
                <select
                  required
                  className="form-select"
                  value={formData.category_id}
                  onChange={(e) => handleCategoryChange(e.target.value)}
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name_hi ? `${c.name_hi} (${c.name_en})` : c.name_en}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">
                  संबंधित विभाग (Department)
                </label>
                <select
                  className="form-select"
                  value={formData.department_id || ''}
                  onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                >
                  {departments.length === 0 ? (
                    <option value="">श्रेणी द्वारा स्वतः निर्धारित</option>
                  ) : (
                    departments.map((dep) => (
                      <option key={dep.id} value={dep.id}>
                        {dep.name_en} ({dep.code})
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Grievance Details */}
          <div style={{ marginBottom: '1.5rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '1rem' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: '800', color: 'var(--gov-navy)', marginBottom: '0.85rem' }}>
              2. शिकायत का विस्तृत विवरण (Grievance Description)
            </div>

            <div className="form-group">
              <label className="form-label">
                शिकायत का विषय (Subject / Title)<span className="req">*</span>
              </label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="उदा: मुख्य मार्ग पर पेयजल पाइपलाइन टूटने से जलभराव"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              />
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <label className="form-label" style={{ marginBottom: 0 }}>
                  विस्तृत विवरण (Detailed Description)<span className="req">*</span>
                </label>
                <button
                  type="button"
                  onClick={handleGetAiRecommendation}
                  disabled={aiLoading}
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--gov-green)',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    padding: '2px 8px',
                    borderRadius: '2px',
                    cursor: 'pointer',
                  }}
                >
                  <Sparkles size={13} />
                  {aiLoading ? 'AI विश्लेषण जारी है...' : 'AI तकनीकी सहायता (Auto Suggest)'}
                </button>
              </div>
              <textarea
                required
                rows={4}
                className="form-textarea"
                placeholder="समस्या कब से है, स्थल की स्थिति, प्रभावित क्षेत्र तथा आवश्यक कार्यवाही का विवरण स्पष्ट लिखें..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>

            {/* AI Recommendation Card */}
            <AIRecommendationCard
              recommendation={recommendation}
              onApply={handleApplyAiRecommendation}
            />

            <div className="form-group">
              <label className="form-label">
                घटना स्थल / सटीक पता (Location Marker / Address)<span className="req">*</span>
              </label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="वार्ड क्रमांक, मोहल्ला, लैंडमार्क, कॉलोनी या सड़क का नाम..."
                value={formData.location_address}
                onChange={(e) => setFormData({ ...formData, location_address: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Upload size={15} /> साक्ष्य / संलग्नक फ़ाइल (Supporting Attachment - Optional)
              </label>
              <input
                type="file"
                accept="image/*,.pdf,video/mp4,audio/mpeg,audio/wav,audio/mp3"
                className="form-input"
                style={{ padding: '0.4rem 0.6rem' }}
                onChange={handleFileChange}
              />
              <div className="form-help">
                मान्य प्रारूप: JPG, PNG, PDF, MP4, MP3 (अधिकतम आकार: 10MB)
              </div>
            </div>
          </div>

          {/* Section 3: Priority & Contact Info */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: '800', color: 'var(--gov-navy)', marginBottom: '0.85rem' }}>
              3. प्राथमिकता एवं संपर्क विवरण (Priority & Citizen Contact)
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">प्राथमिकता (Initial Priority)</label>
                <select
                  className="form-select"
                  value={formData.priority}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      priority: e.target.value as 'LOW' | 'MEDIUM' | 'HIGH',
                    })
                  }
                >
                  <option value="LOW">सामान्य (Standard SLA: 1.5x)</option>
                  <option value="MEDIUM">मध्यम (Default SLA: 1.0x)</option>
                  <option value="HIGH">उच्च / आपात (Urgent SLA: 0.5x)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">मोबाइल नंबर (Mobile No. for SMS Updates)</label>
                <input
                  type="tel"
                  className="form-input"
                  placeholder="10 अंकों का मोबाइल नंबर"
                  value={formData.contact_mobile}
                  onChange={(e) => setFormData({ ...formData, contact_mobile: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">ईमेल पता (Email Address for Receipt)</label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="citizen@example.com"
                  value={formData.contact_email}
                  onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* Declaration Checkbox */}
          <div
            style={{
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              padding: '0.85rem',
              marginBottom: '1.5rem',
            }}
          >
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem', cursor: 'pointer', fontSize: '0.825rem' }}>
              <input
                type="checkbox"
                required
                checked={declarationChecked}
                onChange={(e) => setDeclarationChecked(e.target.checked)}
                style={{ marginTop: '2px' }}
              />
              <span>
                <strong>स्व-घोषणा (Citizen Declaration):</strong> मैं प्रमाणित करता/करती हूँ कि इस शिकायत में प्रस्तुत समस्त विवरण मेरे व्यक्तिगत ज्ञान में पूर्णतः सत्य हैं। यदि कोई तथ्य जानबूझकर भ्रामक पाया जाता है तो मेरी शिकायत निरस्त की जा सकती है।
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-saffron"
            style={{ width: '100%', padding: '0.75rem', fontSize: '0.95rem', fontWeight: '700' }}
          >
            {loading ? 'शिकायत पंजीकृत की जा रही है...' : 'शिकायत सबमिट करें (Submit Grievance)'}{' '}
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}

export default function SubmitComplaintPage() {
  return (
    <Suspense
      fallback={
        <div style={{ padding: '4rem 1.5rem', textAlign: 'center', color: 'var(--gov-navy)' }}>
          शिकायत प्रपत्र लोड हो रहा है... (Loading Grievance Form...)
        </div>
      }
    >
      <SubmitComplaintContent />
    </Suspense>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import api from '@/services/api';
import { Complaint, StatusHistoryItem, ComplaintMessage } from '@/types';
import StatusBadge from '@/components/StatusBadge';
import PriorityBadge from '@/components/PriorityBadge';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';

export default function ComplaintDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { user } = useAuth();
  const { language } = useLanguage();

  const [complaint, setComplaint] = useState<Complaint | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Message thread state
  const [newMessage, setNewMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);

  // Feedback state
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackComments, setFeedbackComments] = useState('');
  const [isSatisfied, setIsSatisfied] = useState(true);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);

  // Reopen request state
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [reopenJustification, setReopenJustification] = useState('');
  const [submittingReopen, setSubmittingReopen] = useState(false);
  const [reopenSuccess, setReopenSuccess] = useState(false);

  // Action status message
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchComplaintDetails = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await api.get(`/complaints/${id}`);
      setComplaint(res.data);
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.detail ||
          (language === 'hi'
            ? 'शिकायत विवरण लोड करने में असमर्थ। कृपया पुनः प्रयास करें।'
            : 'Unable to retrieve grievance details. You may not be authorized to view this record.')
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComplaintDetails();
  }, [id]);

  // Handle citizen/officer message send
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !complaint) return;

    setSendingMessage(true);
    setActionNotice(null);
    try {
      const res = await api.post(`/complaints/${complaint.id}/messages`, {
        message: newMessage.trim(),
      });
      setComplaint(res.data);
      setNewMessage('');
      setActionNotice(
        language === 'hi'
          ? 'संदेश आधिकारिक पत्रावली में दर्ज किया गया।'
          : 'Communication recorded in official record.'
      );
    } catch (err: any) {
      alert(
        err?.response?.data?.detail ||
          (language === 'hi' ? 'संदेश भेजने में त्रुटि।' : 'Failed to send message.')
      );
    } finally {
      setSendingMessage(false);
    }
  };

  // Handle citizen feedback submission
  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!complaint) return;

    setSubmittingFeedback(true);
    try {
      await api.post(`/complaints/${complaint.id}/feedback`, {
        rating: feedbackRating,
        comments: feedbackComments.trim() || undefined,
        is_satisfied: isSatisfied,
      });
      setFeedbackSuccess(true);
      fetchComplaintDetails();
    } catch (err: any) {
      alert(
        err?.response?.data?.detail ||
          (language === 'hi' ? 'फीडबैक सबमिट नहीं हो सका।' : 'Failed to submit feedback.')
      );
    } finally {
      setSubmittingFeedback(false);
    }
  };

  // Handle citizen reopen submission
  const handleSubmitReopen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!complaint || !reopenJustification.trim()) return;

    setSubmittingReopen(true);
    try {
      await api.post(`/complaints/${complaint.id}/reopen`, {
        justification: reopenJustification.trim(),
      });
      setReopenSuccess(true);
      setShowReopenModal(false);
      setReopenJustification('');
      fetchComplaintDetails();
      setActionNotice(
        language === 'hi'
          ? 'पुनः खोलने का अनुरोध जिला प्रशासक को प्रेषित कर दिया गया है।'
          : 'Reopen request has been submitted to District Admin for review.'
      );
    } catch (err: any) {
      alert(
        err?.response?.data?.detail ||
          (language === 'hi' ? 'अनुरोध विफल रहा।' : 'Failed to submit reopen request.')
      );
    } finally {
      setSubmittingReopen(false);
    }
  };

  // Escalate grievance
  const handleEscalate = async () => {
    if (!complaint) return;
    if (
      !confirm(
        language === 'hi'
          ? 'क्या आप इस शिकायत को उच्चाधिकारी के संज्ञान में एस्केलेट करना चाहते हैं?'
          : 'Are you sure you want to escalate this complaint to higher authorities?'
      )
    ) {
      return;
    }

    try {
      await api.post(`/complaints/${complaint.id}/escalate`);
      fetchComplaintDetails();
      setActionNotice(
        language === 'hi'
          ? 'शिकायत को वरिष्ठ अधिकारी स्तर पर एस्केलेट कर दिया गया है।'
          : 'Complaint has been escalated to senior grievance officers.'
      );
    } catch (err: any) {
      alert(
        err?.response?.data?.detail ||
          (language === 'hi' ? 'एस्केलेशन विफल रहा।' : 'Failed to escalate complaint.')
      );
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center bg-[#f8fafc]">
        <div className="w-10 h-10 border-4 border-[#0b2545] border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-700">
          {language === 'hi'
            ? 'शासकीय पत्रावली लोड हो रही है...'
            : 'Retrieving official grievance record...'}
        </p>
      </div>
    );
  }

  if (errorMsg || !complaint) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-red-50 border-l-4 border-red-600 p-6 rounded-r shadow-sm">
          <h2 className="text-lg font-bold text-red-900 mb-2">
            {language === 'hi' ? 'अभिलेख नहीं मिला' : 'Grievance Record Unavailable'}
          </h2>
          <p className="text-sm text-red-700 mb-4">{errorMsg}</p>
          <div className="flex space-x-3">
            <button
              onClick={() => router.back()}
              className="px-4 py-2 bg-slate-200 text-slate-800 text-xs font-bold rounded hover:bg-slate-300"
            >
              {language === 'hi' ? 'वापस जाएं' : 'Go Back'}
            </button>
            <Link
              href="/dashboard"
              className="px-4 py-2 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074]"
            >
              {language === 'hi' ? 'नागरिक डैशबोर्ड' : 'Citizen Dashboard'}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isResolvedOrClosed =
    complaint.status === 'RESOLVED' || complaint.status === 'CLOSED';

  return (
    <div className="min-h-screen bg-[#f8fafc] py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Top Breadcrumb & Actions Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
          <div className="flex items-center space-x-2 text-xs text-slate-500 font-medium">
            <Link href="/" className="hover:text-[#0b2545]">
              {language === 'hi' ? 'मुख्य पृष्ठ' : 'Home'}
            </Link>
            <span>/</span>
            <Link
              href={user?.role === 'OFFICER' ? '/officer' : user?.role?.includes('ADMIN') ? '/admin' : '/dashboard'}
              className="hover:text-[#0b2545]"
            >
              {user?.role === 'OFFICER'
                ? language === 'hi'
                  ? 'अधिकारी पोर्टल'
                  : 'Officer Portal'
                : user?.role?.includes('ADMIN')
                ? language === 'hi'
                  ? 'जिला प्रशासन'
                  : 'District Admin'
                : language === 'hi'
                ? 'डैशबोर्ड'
                : 'Dashboard'}
            </Link>
            <span>/</span>
            <span className="text-slate-800 font-bold">{complaint.complaint_no}</span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 bg-white border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm flex items-center"
            >
              <svg className="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
                />
              </svg>
              {language === 'hi' ? 'प्रिंट रसीद' : 'Print Record'}
            </button>
            {complaint.is_overdue && !isResolvedOrClosed && (
              <button
                onClick={handleEscalate}
                className="px-3 py-1.5 bg-rose-600 text-white rounded text-xs font-bold hover:bg-rose-700 shadow-sm"
              >
                {language === 'hi' ? 'एस्केलेट करें' : 'Escalate Overdue'}
              </button>
            )}
            {isResolvedOrClosed && (
              <button
                onClick={() => setShowReopenModal(true)}
                className="px-3 py-1.5 bg-amber-600 text-white rounded text-xs font-bold hover:bg-amber-700 shadow-sm"
              >
                {language === 'hi' ? 'पुनः खोलें (Reopen)' : 'Request Reopen'}
              </button>
            )}
          </div>
        </div>

        {actionNotice && (
          <div className="p-3 bg-emerald-50 border-l-4 border-emerald-600 rounded-r text-xs text-emerald-800 flex items-center justify-between">
            <span>{actionNotice}</span>
            <button
              onClick={() => setActionNotice(null)}
              className="text-emerald-700 font-bold ml-4"
            >
              ✕
            </button>
          </div>
        )}

        {/* Official Dossier Header Card */}
        <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
          <div className="h-1.5 w-full bg-gradient-to-r from-[#FF9933] via-white to-[#138808]" />
          <div className="p-6">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-slate-100 border border-slate-300 rounded text-slate-700">
                    MP Gov Grievance Dossier
                  </span>
                  {complaint.is_anonymous && (
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-amber-100 border border-amber-300 rounded text-amber-800">
                      Anonymous Submission
                    </span>
                  )}
                </div>
                <h1 className="text-xl sm:text-2xl font-bold text-[#0b2545] mt-1.5">
                  {complaint.complaint_no}
                </h1>
                <p className="text-xs text-slate-500 font-medium">
                  {language === 'hi' ? 'पंजीकरण दिनांक' : 'Registered On'}:{' '}
                  {new Date(complaint.created_at).toLocaleString('en-IN', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={complaint.status} />
                <PriorityBadge priority={complaint.priority} />
                {complaint.is_overdue && (
                  <span className="px-2.5 py-1 text-xs font-bold rounded bg-rose-100 text-rose-800 border border-rose-300 animate-pulse">
                    {language === 'hi' ? 'समयसीमा समाप्त (Overdue)' : 'SLA Breached'}
                  </span>
                )}
              </div>
            </div>

            {/* Core Metadata Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4 text-xs">
              <div className="p-3 bg-slate-50 rounded border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'जिला (District)' : 'District'}
                </span>
                <span className="font-bold text-slate-900 text-sm mt-0.5 block">
                  {complaint.district_code}
                </span>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'विभाग (Department)' : 'Department'}
                </span>
                <span className="font-bold text-slate-900 text-sm mt-0.5 block truncate">
                  {complaint.department?.name_en || complaint.department_id || 'General Administration'}
                </span>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'श्रेणी (Category)' : 'Category'}
                </span>
                <span className="font-bold text-slate-900 text-sm mt-0.5 block truncate">
                  {complaint.category?.name_en || 'Public Service'}
                </span>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'निवारण समयसीमा (SLA)' : 'SLA Target'}
                </span>
                <span className="font-bold text-slate-900 text-sm mt-0.5 block">
                  {new Date(complaint.sla_deadline).toLocaleDateString('en-IN', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                  })}
                </span>
              </div>
            </div>

            {/* Officer Assignment Info */}
            <div className="mt-2 p-3 bg-blue-50/60 border border-blue-200 rounded flex flex-col sm:flex-row sm:items-center justify-between text-xs text-blue-900 gap-2">
              <div>
                <span className="font-bold uppercase tracking-wider text-[10px] text-blue-700 block">
                  {language === 'hi' ? 'अधिकृत निवारण अधिकारी' : 'Assigned Grievance Officer'}
                </span>
                <span className="font-semibold text-sm">
                  {complaint.assigned_officer_name ||
                    (complaint.assigned_officer_id
                      ? `Officer ID: ${complaint.assigned_officer_id}`
                      : language === 'hi'
                      ? 'जिला प्रशासक द्वारा आबंटन प्रक्रियाधीन'
                      : 'Pending Assignment by District Admin')}
                </span>
              </div>
              {complaint.tracking_code && (
                <div className="bg-white px-2.5 py-1 rounded border border-blue-200 text-right">
                  <span className="text-[10px] text-slate-500 block">Secret Tracking Code:</span>
                  <span className="font-mono font-bold text-slate-800">{complaint.tracking_code}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Grievance Substance Card */}
        <div className="bg-white border border-slate-200 rounded shadow-sm p-6">
          <h2 className="text-sm font-bold text-[#0b2545] uppercase tracking-wider border-b border-slate-200 pb-2 mb-4 flex items-center">
            <span className="w-2.5 h-2.5 bg-[#0b2545] rounded-full mr-2" />
            {language === 'hi' ? 'शिकायत का विवरण' : 'Grievance Particulars'}
          </h2>

          <div className="space-y-4">
            <div>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                {language === 'hi' ? 'विषय (Subject)' : 'Subject'}
              </span>
              <p className="text-base font-bold text-slate-900 mt-1">{complaint.subject}</p>
            </div>

            <div>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                {language === 'hi' ? 'विस्तृत विवरण (Description)' : 'Full Description'}
              </span>
              <div className="mt-1 p-4 bg-slate-50 rounded border border-slate-200 text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">
                {complaint.description}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'घटना स्थल / पता' : 'Incident Location'}
                </span>
                <p className="text-xs font-medium text-slate-800 mt-1">
                  {complaint.location_address || 'Not specified'}
                </p>
              </div>

              <div>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'नागरिक संपर्क' : 'Contact Particulars'}
                </span>
                <p className="text-xs font-medium text-slate-800 mt-1">
                  {complaint.is_anonymous
                    ? 'Protected Anonymous Submission'
                    : `${complaint.contact_email || 'N/A'} | ${complaint.contact_mobile || 'N/A'}`}
                </p>
              </div>
            </div>

            {/* Attachments Section */}
            {complaint.attachments && complaint.attachments.length > 0 && (
              <div className="pt-4 border-t border-slate-200">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
                  {language === 'hi' ? 'संलग्न शासकीय दस्तावेज़ / साक्ष्य' : 'Attached Documents'} (
                  {complaint.attachments.length})
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {complaint.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="p-2.5 bg-slate-50 border border-slate-200 rounded flex items-center justify-between text-xs"
                    >
                      <div className="truncate mr-2">
                        <p className="font-semibold text-slate-800 truncate">{att.file_name}</p>
                        <p className="text-[10px] text-slate-500">
                          {(att.file_size / 1024).toFixed(1)} KB • {att.mime_type}
                        </p>
                      </div>
                      <a
                        href={`http://localhost:8000/api/v1/attachments/${att.id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2 py-1 bg-[#0b2545] text-white text-[11px] font-bold rounded hover:bg-[#134074]"
                      >
                        Download
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Official Resolution Summary (if resolved) */}
            {complaint.resolution_summary && (
              <div className="mt-4 p-4 bg-emerald-50 border-l-4 border-emerald-600 rounded-r">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-xs font-bold text-emerald-900 uppercase tracking-wider">
                    {language === 'hi' ? 'शासकीय निस्तारण सारांश (Resolution Summary)' : 'Official Resolution Summary'}
                  </h3>
                  {complaint.resolved_at && (
                    <span className="text-[10px] font-semibold text-emerald-800">
                      Resolved: {new Date(complaint.resolved_at).toLocaleDateString('en-IN')}
                    </span>
                  )}
                </div>
                <p className="text-xs text-emerald-950 font-medium whitespace-pre-wrap">
                  {complaint.resolution_summary}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Citizen Feedback Card */}
        {isResolvedOrClosed && (
          <div className="bg-white border border-slate-200 rounded shadow-sm p-6">
            <h2 className="text-sm font-bold text-[#0b2545] uppercase tracking-wider border-b border-slate-200 pb-2 mb-4">
              {language === 'hi' ? 'नागरिक संतुष्टि एवं फीडबैक' : 'Citizen Satisfaction & Feedback'}
            </h2>

            {complaint.feedback || feedbackSuccess ? (
              <div className="p-4 bg-blue-50/70 border border-blue-200 rounded text-xs text-blue-950">
                <div className="flex items-center space-x-1 mb-2">
                  <span className="font-bold">Rating:</span>
                  {[1, 2, 3, 4, 5].map((s) => (
                    <span
                      key={s}
                      className={
                        s <= (complaint.feedback?.rating || feedbackRating)
                          ? 'text-amber-500 text-base'
                          : 'text-slate-300 text-base'
                      }
                    >
                      ★
                    </span>
                  ))}
                  <span className="ml-2 font-bold">
                    ({(complaint.feedback?.rating || feedbackRating)} / 5)
                  </span>
                </div>
                <p className="font-medium">
                  <span className="font-bold">Status:</span>{' '}
                  {(complaint.feedback?.is_satisfied ?? isSatisfied)
                    ? 'Satisfied with government action'
                    : 'Not satisfied with government action'}
                </p>
                {(complaint.feedback?.comments || feedbackComments) && (
                  <p className="mt-1 text-slate-700 italic">
                    "{complaint.feedback?.comments || feedbackComments}"
                  </p>
                )}
              </div>
            ) : (
              <form onSubmit={handleSubmitFeedback} className="space-y-4">
                <p className="text-xs text-slate-600">
                  {language === 'hi'
                    ? 'कृपया निवारण की गुणवत्ता पर अपना बहुमूल्य फीडबैक प्रदान करें:'
                    : 'Please rate the quality of grievance resolution provided by the officer:'}
                </p>

                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-slate-700">Rating:</span>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setFeedbackRating(star)}
                      className={`text-2xl ${
                        star <= feedbackRating ? 'text-amber-500' : 'text-slate-300'
                      } hover:scale-110 transition-transform`}
                    >
                      ★
                    </button>
                  ))}
                </div>

                <div className="flex items-center space-x-4 text-xs font-semibold">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="satisfied"
                      checked={isSatisfied === true}
                      onChange={() => setIsSatisfied(true)}
                      className="mr-1.5 text-[#0b2545]"
                    />
                    {language === 'hi' ? 'संतुष्ट (Satisfied)' : 'Satisfied'}
                  </label>
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="satisfied"
                      checked={isSatisfied === false}
                      onChange={() => setIsSatisfied(false)}
                      className="mr-1.5 text-[#0b2545]"
                    />
                    {language === 'hi' ? 'असंतुष्ट (Not Satisfied)' : 'Not Satisfied'}
                  </label>
                </div>

                <div>
                  <textarea
                    rows={2}
                    value={feedbackComments}
                    onChange={(e) => setFeedbackComments(e.target.value)}
                    placeholder={
                      language === 'hi'
                        ? 'अतिरिक्त टिप्पणी लिखें (वैकल्पिक)...'
                        : 'Write additional feedback comments (optional)...'
                    }
                    className="w-full p-2.5 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                  />
                </div>

                <button
                  type="submit"
                  disabled={submittingFeedback}
                  className="px-4 py-2 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074] disabled:opacity-50"
                >
                  {submittingFeedback ? 'Submitting...' : 'Submit Citizen Feedback'}
                </button>
              </form>
            )}
          </div>
        )}

        {/* Audit Trail & Status History */}
        <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200">
            <h2 className="text-xs font-bold text-[#0b2545] uppercase tracking-wider flex items-center">
              <svg className="w-4 h-4 mr-1.5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {language === 'hi' ? 'शासकीय कार्यप्रवाह एवं कार्यवाही इतिहास' : 'Official Action & Audit Trail'}
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/90 text-slate-800 border-b border-slate-200">
                  <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Timestamp</th>
                  <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Actor / Role</th>
                  <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Status Change</th>
                  <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Official Remarks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 font-medium">
                {complaint.status_history && complaint.status_history.length > 0 ? (
                  complaint.status_history.map((hist: StatusHistoryItem) => (
                    <tr key={hist.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 text-slate-600 whitespace-nowrap">
                        {new Date(hist.timestamp).toLocaleString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 bg-slate-200/80 text-slate-800 text-[10px] font-bold rounded">
                          {hist.actor_role}
                        </span>
                      </td>
                      <td className="py-2.5 px-4">
                        <span className="font-semibold text-slate-900">
                          {hist.old_status ? `${hist.old_status} → ` : ''}
                          {hist.new_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-slate-700">{hist.remarks || '-'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-4 text-center text-slate-500">
                      No status history recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Two-Way Citizen-Officer Communication Channel */}
        <div className="bg-white border border-slate-200 rounded shadow-sm p-6">
          <h2 className="text-sm font-bold text-[#0b2545] uppercase tracking-wider border-b border-slate-200 pb-2 mb-4 flex items-center">
            <svg className="w-4 h-4 mr-1.5 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            {language === 'hi' ? 'नागरिक-अधिकारी संवाद' : 'Citizen-Officer Official Communication'}
          </h2>

          <div className="space-y-3 mb-6 max-h-80 overflow-y-auto pr-1">
            {complaint.messages && complaint.messages.length > 0 ? (
              complaint.messages.map((msg: ComplaintMessage) => {
                const isOfficer = msg.sender_role === 'OFFICER' || msg.sender_role === 'DISTRICT_ADMIN';
                return (
                  <div
                    key={msg.id}
                    className={`p-3 rounded text-xs border ${
                      isOfficer
                        ? 'bg-blue-50/80 border-blue-200 ml-4'
                        : 'bg-slate-50 border-slate-200 mr-4'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-slate-800">
                        {isOfficer ? 'Grievance Officer' : 'Citizen / Complainant'}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(msg.created_at).toLocaleString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <p className="text-slate-800 leading-relaxed">{msg.message}</p>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-500 italic py-2">
                {language === 'hi'
                  ? 'इस शिकायत पर अभी तक कोई संदेश दर्ज नहीं है।'
                  : 'No official messages logged on this grievance yet.'}
              </p>
            )}
          </div>

          <form onSubmit={handleSendMessage} className="flex gap-2">
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder={
                language === 'hi'
                  ? 'आधिकारिक उत्तर अथवा स्पष्टीकरण लिखें...'
                  : 'Type query, clarification, or update...'
              }
              className="flex-1 px-3 py-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545] focus:border-[#0b2545]"
            />
            <button
              type="submit"
              disabled={sendingMessage || !newMessage.trim()}
              className="px-4 py-2 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074] disabled:opacity-50 uppercase tracking-wider"
            >
              {sendingMessage ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      </div>

      {/* Reopen Request Modal */}
      {showReopenModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 border border-slate-300">
            <h3 className="text-base font-bold text-[#0b2545] mb-2">
              {language === 'hi' ? 'शिकायत पुनः खोलने का आवेदन' : 'Request Grievance Reopen'}
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              {language === 'hi'
                ? 'यदि आप समाधान से संतुष्ट नहीं हैं, तो कृपया कारण बताएं। जिला प्रशासक इसकी समीक्षा करेंगे।'
                : 'Please state the precise reasons why the grievance was inadequately resolved. District Admin will review this appeal.'}
            </p>

            <form onSubmit={handleSubmitReopen} className="space-y-4">
              <textarea
                required
                rows={4}
                value={reopenJustification}
                onChange={(e) => setReopenJustification(e.target.value)}
                placeholder={
                  language === 'hi'
                    ? 'पुनः खोलने का कारण एवं असंतुष्टि का आधार...'
                    : 'Provide detailed justification for reopening...'
                }
                className="w-full p-2.5 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
              />

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowReopenModal(false)}
                  className="px-4 py-2 bg-slate-200 text-slate-800 text-xs font-bold rounded hover:bg-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReopen || !reopenJustification.trim()}
                  className="px-4 py-2 bg-amber-600 text-white text-xs font-bold rounded hover:bg-amber-700 disabled:opacity-50"
                >
                  {submittingReopen ? 'Submitting...' : 'Submit Appeal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

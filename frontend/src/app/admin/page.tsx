'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import api from '@/services/api';
import { Complaint, Officer, ReopenRequest, AIInsights, Category, Department } from '@/types';
import StatusBadge from '@/components/StatusBadge';
import PriorityBadge from '@/components/PriorityBadge';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';

export default function DistrictAdminPage() {
  return (
    <ProtectedRoute allowedRoles={['DISTRICT_ADMIN', 'SUPER_ADMIN']}>
      <DistrictAdminContent />
    </ProtectedRoute>
  );
}

function DistrictAdminContent() {
  const { user } = useAuth();
  const { language } = useLanguage();

  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'COMPLAINTS' | 'REOPENS' | 'OFFICERS'>('OVERVIEW');

  // Dashboard Stats
  const [stats, setStats] = useState<any>(null);
  const [insights, setInsights] = useState<AIInsights | null>(null);

  // Complaints
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [overdueOnly, setOverdueOnly] = useState(false);

  // Reopen Requests
  const [reopenRequests, setReopenRequests] = useState<ReopenRequest[]>([]);

  // Officers Roster
  const [officers, setOfficers] = useState<Officer[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  // Assignment Modal
  const [assigningComplaint, setAssigningComplaint] = useState<Complaint | null>(null);
  const [selectedOfficerId, setSelectedOfficerId] = useState('');
  const [assignRemarks, setAssignRemarks] = useState('');
  const [aiRecommendation, setAiRecommendation] = useState<any>(null);
  const [submittingAssign, setSubmittingAssign] = useState(false);

  // Correction Modal
  const [correctingComplaint, setCorrectingComplaint] = useState<Complaint | null>(null);
  const [corrCategoryId, setCorrCategoryId] = useState('');
  const [corrDepartmentId, setCorrDepartmentId] = useState('');
  const [corrPriority, setCorrPriority] = useState('');
  const [corrRemarks, setCorrRemarks] = useState('');
  const [submittingCorr, setSubmittingCorr] = useState(false);

  // New Officer Modal / Inline
  const [showAddOfficerModal, setShowAddOfficerModal] = useState(false);
  const [newOfficerForm, setNewOfficerForm] = useState({
    email: '',
    password: '',
    full_name: '',
    mobile: '',
    department_id: '',
  });

  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<string | null>(null);

  // Load Initial Data
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [dashRes, compRes, offRes, catRes, deptRes] = await Promise.all([
        api.get('/district-admin/dashboard'),
        api.get('/district-admin/complaints'),
        api.get('/district-admin/officers'),
        api.get('/complaints/categories'),
        api.get('/complaints/departments'),
      ]);

      setStats(dashRes.data);
      setComplaints(compRes.data || []);
      setOfficers(offRes.data || []);
      setCategories(catRes.data || []);
      setDepartments(deptRes.data || []);

      // Load AI insights for district
      try {
        const aiRes = await api.get('/ai/insights');
        setInsights(aiRes.data);
      } catch {
        // AI insights optional fallback
      }

      // Load reopens
      try {
        const reopensRes = await api.get('/district-admin/reopen-requests');
        setReopenRequests(reopensRes.data || []);
      } catch {
        // ignore
      }
    } catch (err) {
      console.error('Error loading admin dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  // Filter complaints
  const filteredComplaints = complaints.filter((c) => {
    const matchesStatus = !statusFilter || c.status === statusFilter;
    const matchesOverdue = !overdueOnly || c.is_overdue;
    const matchesSearch =
      !searchQuery ||
      c.complaint_no.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.subject.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesOverdue && matchesSearch;
  });

  // Open Assign Modal and fetch AI recommendation
  const openAssignModal = async (c: Complaint) => {
    setAssigningComplaint(c);
    setSelectedOfficerId('');
    setAssignRemarks('');
    setAiRecommendation(null);

    try {
      const recRes = await api.get(`/district-admin/recommend-officer/${c.id}`);
      setAiRecommendation(recRes.data);
      if (recRes.data?.officer_id) {
        setSelectedOfficerId(recRes.data.officer_id);
      }
    } catch {
      // ignore
    }
  };

  // Submit Officer Assignment
  const handleAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assigningComplaint || !selectedOfficerId) return;

    setSubmittingAssign(true);
    try {
      await api.post(`/district-admin/complaints/${assigningComplaint.id}/assign`, {
        officer_id: selectedOfficerId,
        remarks: assignRemarks.trim() || undefined,
      });

      setNotification(`Grievance ${assigningComplaint.complaint_no} assigned successfully.`);
      setAssigningComplaint(null);
      loadDashboardData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to assign officer.');
    } finally {
      setSubmittingAssign(false);
    }
  };

  // Open Correction Modal
  const openCorrectionModal = (c: Complaint) => {
    setCorrectingComplaint(c);
    setCorrCategoryId(c.category_id || '');
    setCorrDepartmentId(c.department_id || '');
    setCorrPriority(c.priority || 'MEDIUM');
    setCorrRemarks('');
  };

  // Submit Correction
  const handleCorrectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!correctingComplaint) return;

    setSubmittingCorr(true);
    try {
      await api.patch(`/district-admin/complaints/${correctingComplaint.id}/correct`, {
        category_id: corrCategoryId || undefined,
        department_id: corrDepartmentId || undefined,
        priority: corrPriority || undefined,
        remarks: corrRemarks.trim() || undefined,
      });

      setNotification(`Metadata corrected for grievance ${correctingComplaint.complaint_no}.`);
      setCorrectingComplaint(null);
      loadDashboardData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to correct complaint.');
    } finally {
      setSubmittingCorr(false);
    }
  };

  // Approve Reopen
  const handleApproveReopen = async (requestId: string) => {
    if (!confirm('Approve reopening of this grievance and return to active queue?')) return;
    try {
      await api.post(`/district-admin/reopen-requests/${requestId}/approve`);
      setNotification('Reopen request approved.');
      loadDashboardData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Action failed.');
    }
  };

  // Reject Reopen
  const handleRejectReopen = async (requestId: string) => {
    const reason = prompt('Enter justification for rejecting the citizen reopen appeal:');
    if (!reason) return;
    try {
      await api.post(`/district-admin/reopen-requests/${requestId}/reject`, { reason });
      setNotification('Reopen request rejected.');
      loadDashboardData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Action failed.');
    }
  };

  // Create Officer
  const handleCreateOfficer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/district-admin/officers', newOfficerForm);
      setNotification('New Grievance Officer inducted successfully.');
      setShowAddOfficerModal(false);
      setNewOfficerForm({ email: '', password: '', full_name: '', mobile: '', department_id: '' });
      loadDashboardData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create officer.');
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Tricolor Stripe */}
        <div className="h-1.5 w-full bg-gradient-to-r from-[#FF9933] via-white to-[#138808] rounded shadow-sm" />

        {/* District Collectorate Header Banner */}
        <div className="bg-white border border-slate-200 rounded p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 relative flex-shrink-0 bg-slate-50 border border-slate-300 rounded p-1">
              <Image src="/logo.png" alt="State Seal" width={48} height={48} className="object-contain" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-amber-100 border border-amber-300 rounded text-amber-900">
                  District Collectorate Command
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  Jurisdiction: <span className="font-bold text-slate-900">{stats?.district_code || user?.district_code || 'BPL'}</span>
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-[#0b2545] mt-1">
                JanSeva AI • District Magistrate Portal
              </h1>
              <p className="text-xs text-slate-600 mt-0.5">
                Statutory District Grievance Redressal Authority • Government of Madhya Pradesh
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={loadDashboardData}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded text-xs font-bold text-slate-700 shadow-sm"
            >
              ↻ Refresh Data
            </button>
            <button
              onClick={() => setShowAddOfficerModal(true)}
              className="px-3 py-2 bg-[#0b2545] hover:bg-[#134074] text-white text-xs font-bold rounded shadow-sm"
            >
              + Register Officer
            </button>
          </div>
        </div>

        {/* District Isolation Notice */}
        <div className="p-3 bg-blue-50/80 border-l-4 border-[#0b2545] rounded-r text-xs text-blue-950 flex items-center justify-between">
          <div>
            <span className="font-bold">District Data Isolation Active: </span>
            You are operating with full statutory authority strictly within District{' '}
            <span className="font-bold underline">{stats?.district_code || user?.district_code || 'BPL'}</span>. Access to other districts is restricted by state law.
          </div>
        </div>

        {notification && (
          <div className="p-3 bg-emerald-50 border-l-4 border-emerald-600 rounded-r text-xs text-emerald-800 flex items-center justify-between">
            <span>{notification}</span>
            <button onClick={() => setNotification(null)} className="font-bold ml-4">✕</button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-white rounded-t shadow-sm px-4 pt-2">
          <button
            onClick={() => setActiveTab('OVERVIEW')}
            className={`py-3 px-4 text-xs font-bold border-b-2 uppercase tracking-wider transition-colors ${
              activeTab === 'OVERVIEW'
                ? 'border-[#0b2545] text-[#0b2545]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {language === 'hi' ? 'जिला समीक्षा' : 'District Overview'}
          </button>
          <button
            onClick={() => setActiveTab('COMPLAINTS')}
            className={`py-3 px-4 text-xs font-bold border-b-2 uppercase tracking-wider transition-colors ${
              activeTab === 'COMPLAINTS'
                ? 'border-[#0b2545] text-[#0b2545]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {language === 'hi' ? 'शिकायत प्रबंधन' : 'Complaints Register'} ({complaints.length})
          </button>
          <button
            onClick={() => setActiveTab('REOPENS')}
            className={`py-3 px-4 text-xs font-bold border-b-2 uppercase tracking-wider transition-colors ${
              activeTab === 'REOPENS'
                ? 'border-[#0b2545] text-[#0b2545]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {language === 'hi' ? 'अपील / पुनः खोलना' : 'Reopen Appeals'} ({reopenRequests.length})
          </button>
          <button
            onClick={() => setActiveTab('OFFICERS')}
            className={`py-3 px-4 text-xs font-bold border-b-2 uppercase tracking-wider transition-colors ${
              activeTab === 'OFFICERS'
                ? 'border-[#0b2545] text-[#0b2545]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {language === 'hi' ? 'अधिकारी दल' : 'Officers Roster'} ({officers.length})
          </button>
        </div>

        {/* Tab 1: OVERVIEW */}
        {activeTab === 'OVERVIEW' && (
          <div className="space-y-6">
            {/* Stat Counter Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <div className="bg-white border border-slate-200 rounded p-4 shadow-sm">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Complaints</p>
                <p className="text-2xl font-bold text-[#0b2545] mt-1">{stats?.total_complaints || 0}</p>
              </div>

              <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-blue-600">
                <p className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">Pending Assignment</p>
                <p className="text-2xl font-bold text-blue-800 mt-1">{stats?.submitted || 0}</p>
              </div>

              <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-amber-500">
                <p className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">In Progress</p>
                <p className="text-2xl font-bold text-amber-600 mt-1">{stats?.in_progress || 0}</p>
              </div>

              <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-emerald-600">
                <p className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">Resolved</p>
                <p className="text-2xl font-bold text-emerald-700 mt-1">{stats?.resolved || 0}</p>
              </div>

              <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-rose-600">
                <p className="text-[10px] font-bold text-rose-700 uppercase tracking-wider">SLA Overdue</p>
                <p className="text-2xl font-bold text-rose-600 mt-1">{stats?.overdue || 0}</p>
              </div>

              <div className="bg-white border border-slate-200 rounded p-4 shadow-sm">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Active Officers</p>
                <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.active_officers || officers.length}</p>
              </div>
            </div>

            {/* AI Executive Advisory Card */}
            {insights && (
              <div className="bg-white border border-slate-200 rounded p-6 shadow-sm">
                <div className="flex items-center space-x-2 border-b border-slate-200 pb-3 mb-4">
                  <span className="p-1 bg-amber-100 rounded text-amber-800 font-bold text-xs">AI</span>
                  <h2 className="text-sm font-bold text-[#0b2545] uppercase tracking-wider">
                    Executive AI Grievance Intelligence Report
                  </h2>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {insights.summary_text}
                </p>

                {insights.highlights && (
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider block mb-1">
                      Key Highlights:
                    </span>
                    <ul className="list-disc list-inside text-xs text-slate-600 space-y-1">
                      {insights.highlights.map((h, i) => (
                        <li key={i}>{h}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: COMPLAINTS */}
        {activeTab === 'COMPLAINTS' && (
          <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
            {/* Filter controls */}
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  placeholder="Search complaint no or subject..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="px-3 py-1.5 border border-slate-300 rounded text-xs w-64 focus:ring-1 focus:ring-[#0b2545]"
                />

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-2.5 py-1.5 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-[#0b2545]"
                >
                  <option value="">All Statuses</option>
                  <option value="SUBMITTED">SUBMITTED</option>
                  <option value="ASSIGNED">ASSIGNED</option>
                  <option value="IN_PROGRESS">IN_PROGRESS</option>
                  <option value="ON_HOLD">ON_HOLD</option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="REOPENED">REOPENED</option>
                </select>

                <label className="flex items-center text-xs font-bold text-rose-700 cursor-pointer ml-2">
                  <input
                    type="checkbox"
                    checked={overdueOnly}
                    onChange={(e) => setOverdueOnly(e.target.checked)}
                    className="mr-1 h-3.5 w-3.5 text-rose-600 rounded"
                  />
                  Overdue Only
                </label>
              </div>

              <div className="text-xs text-slate-500 font-semibold">
                Showing {filteredComplaints.length} of {complaints.length} records
              </div>
            </div>

            {/* Complaints Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 text-slate-800 border-b border-slate-200">
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Complaint No</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Subject & Category</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Assigned Officer</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Status</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Priority</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">SLA Target</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filteredComplaints.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50">
                      <td className="py-3 px-4 font-bold text-[#0b2545] whitespace-nowrap">
                        <Link href={`/complaints/${item.id}`} className="hover:underline">
                          {item.complaint_no}
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-semibold text-slate-900 truncate max-w-xs">{item.subject}</p>
                        <p className="text-[10px] text-slate-500">{item.category?.name_en || 'Public Service'}</p>
                      </td>
                      <td className="py-3 px-4 text-slate-700 whitespace-nowrap">
                        {item.assigned_officer_name || (
                          <span className="text-amber-700 font-semibold text-[11px]">Unassigned</span>
                        )}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <PriorityBadge priority={item.priority} />
                      </td>
                      <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                        {new Date(item.sla_deadline).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                        })}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap space-x-1">
                        <button
                          onClick={() => openAssignModal(item)}
                          className="px-2 py-1 bg-[#0b2545] text-white text-[11px] font-bold rounded hover:bg-[#134074]"
                        >
                          Assign
                        </button>
                        <button
                          onClick={() => openCorrectionModal(item)}
                          className="px-2 py-1 bg-slate-100 border border-slate-300 text-slate-700 text-[11px] font-bold rounded hover:bg-slate-200"
                        >
                          Correct
                        </button>
                        <Link
                          href={`/complaints/${item.id}`}
                          className="px-2 py-1 bg-slate-100 border border-slate-300 text-slate-700 text-[11px] font-bold rounded hover:bg-slate-200"
                        >
                          Dossier
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: REOPENS */}
        {activeTab === 'REOPENS' && (
          <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden p-6">
            <h2 className="text-sm font-bold text-[#0b2545] uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
              Citizen Grievance Reopen Appeals Review Queue
            </h2>

            {reopenRequests.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center font-medium">
                No pending grievance reopen requests in District {stats?.district_code || 'BPL'}.
              </p>
            ) : (
              <div className="space-y-4">
                {reopenRequests.map((req) => (
                  <div key={req.id} className="p-4 bg-slate-50 border border-slate-200 rounded flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-xs text-[#0b2545]">
                          Complaint #{req.complaint?.complaint_no || req.complaint_id}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {new Date(req.created_at).toLocaleDateString('en-IN')}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-slate-800">{req.complaint?.subject}</p>
                      <p className="text-xs text-slate-600 italic bg-white p-2.5 rounded border border-slate-200">
                        Citizen Justification: "{req.justification}"
                      </p>
                    </div>

                    <div className="flex items-center space-x-2 flex-shrink-0">
                      <button
                        onClick={() => handleApproveReopen(req.id)}
                        className="px-3 py-1.5 bg-emerald-600 text-white text-xs font-bold rounded hover:bg-emerald-700"
                      >
                        Approve Reopen
                      </button>
                      <button
                        onClick={() => handleRejectReopen(req.id)}
                        className="px-3 py-1.5 bg-rose-600 text-white text-xs font-bold rounded hover:bg-rose-700"
                      >
                        Reject Appeal
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: OFFICERS ROSTER */}
        {activeTab === 'OFFICERS' && (
          <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden p-6">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-200">
              <h2 className="text-sm font-bold text-[#0b2545] uppercase tracking-wider">
                Grievance Redressal Officers Roster
              </h2>
              <button
                onClick={() => setShowAddOfficerModal(true)}
                className="px-3 py-1.5 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074]"
              >
                + Register New Officer
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 text-slate-800 border-b border-slate-200">
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Officer ID</th>
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Name & Email</th>
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Department</th>
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Active Workload</th>
                    <th className="py-2.5 px-4 font-bold uppercase tracking-wider">Availability</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {officers.map((off) => (
                    <tr key={off.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 font-mono font-bold text-slate-800">{off.officer_id}</td>
                      <td className="py-2.5 px-4">
                        <p className="font-semibold text-slate-900">{off.full_name}</p>
                        <p className="text-[10px] text-slate-500">{off.email}</p>
                      </td>
                      <td className="py-2.5 px-4 text-slate-700">
                        {off.department?.name_en || off.department_id}
                      </td>
                      <td className="py-2.5 px-4 font-bold text-slate-900">{off.active_workload} active</td>
                      <td className="py-2.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            off.is_available
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-200 text-slate-700'
                          }`}
                        >
                          {off.is_available ? 'Available' : 'Unavailable'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Officer Assignment Modal */}
      {assigningComplaint && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 border border-slate-300">
            <h3 className="text-base font-bold text-[#0b2545] mb-1">
              Assign Grievance Officer
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              Grievance #{assigningComplaint.complaint_no} • {assigningComplaint.subject}
            </p>

            {aiRecommendation && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-950">
                <span className="font-bold">AI Officer Recommendation: </span>
                <span>{aiRecommendation.reasoning || 'Selected based on lowest workload & department matching.'}</span>
              </div>
            )}

            <form onSubmit={handleAssignSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Select Grievance Officer *
                </label>
                <select
                  required
                  value={selectedOfficerId}
                  onChange={(e) => setSelectedOfficerId(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-[#0b2545]"
                >
                  <option value="">-- Choose Officer --</option>
                  {officers.map((off) => (
                    <option key={off.id} value={off.id}>
                      {off.full_name} ({off.department?.name_en || 'Dept'}) - {off.active_workload} active
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Administrative Directive / Remarks
                </label>
                <textarea
                  rows={2}
                  value={assignRemarks}
                  onChange={(e) => setAssignRemarks(e.target.value)}
                  placeholder="e.g. Please expedite field inspection within 48 hours..."
                  className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setAssigningComplaint(null)}
                  className="px-4 py-2 bg-slate-200 text-slate-800 text-xs font-bold rounded hover:bg-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAssign || !selectedOfficerId}
                  className="px-4 py-2 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074] disabled:opacity-50"
                >
                  {submittingAssign ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Metadata Correction Modal */}
      {correctingComplaint && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 border border-slate-300">
            <h3 className="text-base font-bold text-[#0b2545] mb-1">
              Correct Grievance Classification
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              Grievance #{correctingComplaint.complaint_no}
            </p>

            <form onSubmit={handleCorrectionSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Category
                </label>
                <select
                  value={corrCategoryId}
                  onChange={(e) => setCorrCategoryId(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-[#0b2545]"
                >
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name_en} ({cat.name_hi})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Department
                </label>
                <select
                  value={corrDepartmentId}
                  onChange={(e) => setCorrDepartmentId(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-[#0b2545]"
                >
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name_en} ({dept.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Priority
                </label>
                <select
                  value={corrPriority}
                  onChange={(e) => setCorrPriority(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-[#0b2545]"
                >
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Reason for Correction
                </label>
                <input
                  type="text"
                  value={corrRemarks}
                  onChange={(e) => setCorrRemarks(e.target.value)}
                  placeholder="e.g. Misclassified by citizen during filing"
                  className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCorrectingComplaint(null)}
                  className="px-4 py-2 bg-slate-200 text-slate-800 text-xs font-bold rounded hover:bg-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingCorr}
                  className="px-4 py-2 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074] disabled:opacity-50"
                >
                  {submittingCorr ? 'Saving...' : 'Apply Correction'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Officer Modal */}
      {showAddOfficerModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 border border-slate-300">
            <h3 className="text-base font-bold text-[#0b2545] mb-1">
              Induct Grievance Redressal Officer
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              Add new officer to District {stats?.district_code || 'BPL'} roster.
            </p>

            <form onSubmit={handleCreateOfficer} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={newOfficerForm.full_name}
                  onChange={(e) => setNewOfficerForm({ ...newOfficerForm, full_name: e.target.value })}
                  placeholder="e.g. Ramesh Verma"
                  className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Official Email *
                </label>
                <input
                  type="email"
                  required
                  value={newOfficerForm.email}
                  onChange={(e) => setNewOfficerForm({ ...newOfficerForm, email: e.target.value })}
                  placeholder="officer.bhopal@mp.gov.in"
                  className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Temporary Password *
                </label>
                <input
                  type="password"
                  required
                  value={newOfficerForm.password}
                  onChange={(e) => setNewOfficerForm({ ...newOfficerForm, password: e.target.value })}
                  placeholder="••••••••••••"
                  className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Department *
                </label>
                <select
                  required
                  value={newOfficerForm.department_id}
                  onChange={(e) => setNewOfficerForm({ ...newOfficerForm, department_id: e.target.value })}
                  className="w-full p-2 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-[#0b2545]"
                >
                  <option value="">-- Choose Department --</option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name_en}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddOfficerModal(false)}
                  className="px-4 py-2 bg-slate-200 text-slate-800 text-xs font-bold rounded hover:bg-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074]"
                >
                  Register Officer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

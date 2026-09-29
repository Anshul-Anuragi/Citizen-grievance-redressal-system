'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import api from '@/services/api';
import { Complaint } from '@/types';
import StatusBadge from '@/components/StatusBadge';
import PriorityBadge from '@/components/PriorityBadge';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';

export default function OfficerPage() {
  return (
    <ProtectedRoute allowedRoles={['OFFICER', 'SUPER_ADMIN']}>
      <OfficerContent />
    </ProtectedRoute>
  );
}

function OfficerContent() {
  const { user } = useAuth();
  const { language } = useLanguage();

  const [stats, setStats] = useState<any>(null);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [notification, setNotification] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [overdueOnly, setOverdueOnly] = useState(false);

  // Hold Modal
  const [holdComplaint, setHoldComplaint] = useState<Complaint | null>(null);
  const [holdRemarks, setHoldRemarks] = useState('');
  const [submittingHold, setSubmittingHold] = useState(false);

  // Resolve Modal
  const [resolveComplaint, setResolveComplaint] = useState<Complaint | null>(null);
  const [resolveSummary, setResolveSummary] = useState('');
  const [resolveRemarks, setResolveRemarks] = useState('');
  const [submittingResolve, setSubmittingResolve] = useState(false);

  const fetchOfficerData = async () => {
    try {
      setLoading(true);
      const [dashRes, compRes] = await Promise.all([
        api.get('/officer/dashboard'),
        api.get('/officer/assigned-complaints'),
      ]);
      setStats(dashRes.data);
      setComplaints(compRes.data || []);
    } catch (err) {
      console.error('Error fetching officer data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOfficerData();
  }, []);

  // Filter complaints
  const filtered = complaints.filter((c) => {
    const matchesStatus = !statusFilter || c.status === statusFilter;
    const matchesOverdue = !overdueOnly || c.is_overdue;
    const matchesSearch =
      !searchQuery ||
      c.complaint_no.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.subject.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesOverdue && matchesSearch;
  });

  // Start progress
  const handleStartProgress = async (complaintId: string) => {
    try {
      await api.post(`/officer/complaints/${complaintId}/start`);
      setNotification('Grievance marked as IN_PROGRESS.');
      fetchOfficerData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to start progress.');
    }
  };

  // Submit Hold
  const handleHoldSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!holdComplaint || !holdRemarks.trim()) return;

    setSubmittingHold(true);
    try {
      await api.post(`/officer/complaints/${holdComplaint.id}/hold`, {
        remarks: holdRemarks.trim(),
      });
      setNotification(`Grievance ${holdComplaint.complaint_no} placed ON_HOLD.`);
      setHoldComplaint(null);
      setHoldRemarks('');
      fetchOfficerData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to place on hold.');
    } finally {
      setSubmittingHold(false);
    }
  };

  // Submit Resolve
  const handleResolveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolveComplaint || !resolveSummary.trim()) return;

    setSubmittingResolve(true);
    try {
      await api.post(`/officer/complaints/${resolveComplaint.id}/resolve`, {
        resolution_summary: resolveSummary.trim(),
        remarks: resolveRemarks.trim() || undefined,
      });
      setNotification(`Grievance ${resolveComplaint.complaint_no} marked as RESOLVED.`);
      setResolveComplaint(null);
      setResolveSummary('');
      setResolveRemarks('');
      fetchOfficerData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to resolve grievance.');
    } finally {
      setSubmittingResolve(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Tricolor Stripe */}
        <div className="h-1.5 w-full bg-gradient-to-r from-[#FF9933] via-white to-[#138808] rounded shadow-sm" />

        {/* Officer Header Card */}
        <div className="bg-white border border-slate-200 rounded p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 relative flex-shrink-0 bg-slate-50 border border-slate-300 rounded p-1">
              <Image src="/logo.png" alt="State Seal" width={48} height={48} className="object-contain" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-emerald-100 border border-emerald-300 rounded text-emerald-900">
                  Grievance Officer Portal
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  Officer ID: <span className="font-bold text-slate-900">{stats?.officer_id || user?.id?.slice(0, 8)}</span>
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  District: <span className="font-bold text-slate-900">{stats?.district_code || user?.district_code || 'BPL'}</span>
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-[#0b2545] mt-1">
                {user?.full_name || 'Designated Grievance Officer'}
              </h1>
              <p className="text-xs text-slate-600 mt-0.5">
                Statutory Redressal Desk • Government of Madhya Pradesh
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={fetchOfficerData}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded text-xs font-bold text-slate-700 shadow-sm"
            >
              ↻ Refresh Tasks
            </button>
          </div>
        </div>

        {notification && (
          <div className="p-3 bg-emerald-50 border-l-4 border-emerald-600 rounded-r text-xs text-emerald-800 flex items-center justify-between">
            <span>{notification}</span>
            <button onClick={() => setNotification(null)} className="font-bold ml-4">✕</button>
          </div>
        )}

        {/* Workload Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-white border border-slate-200 rounded p-4 shadow-sm">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Assigned</p>
            <p className="text-2xl font-bold text-[#0b2545] mt-1">{stats?.total_assigned || complaints.length}</p>
          </div>

          <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-blue-600">
            <p className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">Newly Assigned</p>
            <p className="text-2xl font-bold text-blue-800 mt-1">{stats?.assigned || 0}</p>
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
        </div>

        {/* Assigned Grievances Register */}
        <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
          {/* Controls Bar */}
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
              Assigned Tasks: {filtered.length} of {complaints.length}
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-600 font-semibold">
              Loading assigned grievances...
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-sm font-bold text-slate-700">No Assigned Grievances in this queue.</p>
              <p className="text-xs text-slate-500 mt-1">All assigned tasks are clear or no complaints match current filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 text-slate-800 border-b border-slate-200">
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Complaint No</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Subject & Category</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Status</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Priority</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">SLA Target</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider text-right">Action Desk</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filtered.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 font-bold text-[#0b2545] whitespace-nowrap">
                        <Link href={`/complaints/${item.id}`} className="hover:underline flex items-center">
                          {item.complaint_no}
                          {item.is_overdue && (
                            <span className="ml-1.5 w-2 h-2 rounded-full bg-rose-500" title="SLA Breached" />
                          )}
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-semibold text-slate-900 truncate max-w-xs">{item.subject}</p>
                        <p className="text-[10px] text-slate-500">{item.category?.name_en || 'Public Service'}</p>
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
                        {(item.status === 'ASSIGNED' || item.status === 'REOPENED') && (
                          <button
                            onClick={() => handleStartProgress(item.id)}
                            className="px-2.5 py-1 bg-blue-700 text-white text-[11px] font-bold rounded hover:bg-blue-800"
                          >
                            Commence Work
                          </button>
                        )}
                        {item.status === 'IN_PROGRESS' && (
                          <>
                            <button
                              onClick={() => {
                                setHoldComplaint(item);
                                setHoldRemarks('');
                              }}
                              className="px-2 py-1 bg-amber-600 text-white text-[11px] font-bold rounded hover:bg-amber-700"
                            >
                              Hold
                            </button>
                            <button
                              onClick={() => {
                                setResolveComplaint(item);
                                setResolveSummary('');
                                setResolveRemarks('');
                              }}
                              className="px-2.5 py-1 bg-emerald-700 text-white text-[11px] font-bold rounded hover:bg-emerald-800"
                            >
                              Resolve
                            </button>
                          </>
                        )}
                        {item.status === 'ON_HOLD' && (
                          <button
                            onClick={() => {
                              setResolveComplaint(item);
                              setResolveSummary('');
                              setResolveRemarks('');
                            }}
                            className="px-2.5 py-1 bg-emerald-700 text-white text-[11px] font-bold rounded hover:bg-emerald-800"
                          >
                            Resolve
                          </button>
                        )}
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
          )}
        </div>
      </div>

      {/* Put On Hold Modal */}
      {holdComplaint && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 border border-slate-300">
            <h3 className="text-base font-bold text-[#0b2545] mb-1">
              Place Grievance On Hold
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              Grievance #{holdComplaint.complaint_no} • {holdComplaint.subject}
            </p>

            <form onSubmit={handleHoldSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Reason for Hold (Mandatory) *
                </label>
                <textarea
                  required
                  rows={3}
                  value={holdRemarks}
                  onChange={(e) => setHoldRemarks(e.target.value)}
                  placeholder="e.g. Awaiting field lab test results / Inter-departmental clearance..."
                  className="w-full p-2.5 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setHoldComplaint(null)}
                  className="px-4 py-2 bg-slate-200 text-slate-800 text-xs font-bold rounded hover:bg-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingHold || !holdRemarks.trim()}
                  className="px-4 py-2 bg-amber-600 text-white text-xs font-bold rounded hover:bg-amber-700 disabled:opacity-50"
                >
                  {submittingHold ? 'Updating...' : 'Confirm Hold'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resolve Grievance Modal */}
      {resolveComplaint && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 border border-slate-300">
            <h3 className="text-base font-bold text-[#0b2545] mb-1">
              Final Grievance Redressal / Resolution
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              Grievance #{resolveComplaint.complaint_no} • {resolveComplaint.subject}
            </p>

            <form onSubmit={handleResolveSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Official Resolution Summary (Citizen Facing) *
                </label>
                <textarea
                  required
                  rows={4}
                  value={resolveSummary}
                  onChange={(e) => setResolveSummary(e.target.value)}
                  placeholder="Detail the concrete steps taken to resolve the grievance (e.g. Pipeline repaired by municipal team on 28-Sep, water supply restored)..."
                  className="w-full p-2.5 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Internal Remarks / Notes (Optional)
                </label>
                <input
                  type="text"
                  value={resolveRemarks}
                  onChange={(e) => setResolveRemarks(e.target.value)}
                  placeholder="e.g. Field inspection signed off by AE"
                  className="w-full p-2 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545]"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setResolveComplaint(null)}
                  className="px-4 py-2 bg-slate-200 text-slate-800 text-xs font-bold rounded hover:bg-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingResolve || !resolveSummary.trim()}
                  className="px-4 py-2 bg-emerald-700 text-white text-xs font-bold rounded hover:bg-emerald-800 disabled:opacity-50"
                >
                  {submittingResolve ? 'Submitting...' : 'Mark Grievance Resolved'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

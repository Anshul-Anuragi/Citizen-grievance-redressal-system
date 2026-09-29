'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/services/api';
import { Complaint, ComplaintStatus } from '@/types';
import StatusBadge from '@/components/StatusBadge';
import PriorityBadge from '@/components/PriorityBadge';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';

export default function CitizenDashboardPage() {
  return (
    <ProtectedRoute allowedRoles={['CITIZEN', 'SUPER_ADMIN']}>
      <CitizenDashboardContent />
    </ProtectedRoute>
  );
}

function CitizenDashboardContent() {
  const { user } = useAuth();
  const { language } = useLanguage();
  const router = useRouter();

  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const fetchMyComplaints = async () => {
    try {
      setLoading(true);
      const res = await api.get('/complaints/my-complaints');
      setComplaints(res.data || []);
    } catch (err) {
      console.error('Failed to fetch citizen complaints:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyComplaints();
  }, []);

  // Filter complaints
  const filtered = complaints.filter((c) => {
    const matchesSearch =
      searchTerm === '' ||
      c.complaint_no.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.subject.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'ALL' || c.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // Calculate summary counts
  const totalCount = complaints.length;
  const inProgressCount = complaints.filter(
    (c) => c.status === 'IN_PROGRESS' || c.status === 'ASSIGNED' || c.status === 'SUBMITTED'
  ).length;
  const resolvedCount = complaints.filter(
    (c) => c.status === 'RESOLVED' || c.status === 'CLOSED'
  ).length;
  const overdueCount = complaints.filter((c) => c.is_overdue).length;

  return (
    <div className="min-h-screen bg-[#f8fafc] py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Tricolor Stripe */}
        <div className="h-1.5 w-full bg-gradient-to-r from-[#FF9933] via-white to-[#138808] rounded shadow-sm" />

        {/* Welcome & Portal Header */}
        <div className="bg-white border border-slate-200 rounded p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 bg-blue-50 border border-blue-200 rounded text-[#0b2545]">
                Citizen Grievance Workspace
              </span>
              <span className="text-xs text-slate-500 font-medium">
                Citizen ID: {user?.id?.slice(0, 8) || 'N/A'}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#0b2545] mt-1">
              {language === 'hi' ? 'नमस्ते,' : 'Welcome,'} {user?.full_name || 'Citizen'}
            </h1>
            <p className="text-xs text-slate-600 mt-1">
              {language === 'hi'
                ? 'मध्य प्रदेश जनसेवा निवारण प्रणाली में आपकी पंजीकृत शिकायतों का सिंहावलोकन।'
                : 'Overview of all your registered grievances under the Government of Madhya Pradesh.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/submit"
              className="px-4 py-2 bg-[#0b2545] hover:bg-[#134074] text-white text-xs font-bold rounded shadow-sm transition-colors uppercase tracking-wider flex items-center"
            >
              <span className="mr-1.5 text-base leading-none">+</span>
              {language === 'hi' ? 'नई शिकायत दर्ज करें' : 'File New Grievance'}
            </Link>
            <Link
              href="/track"
              className="px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-bold rounded shadow-sm transition-colors uppercase tracking-wider"
            >
              {language === 'hi' ? 'ट्रैकिंग कोड द्वारा खोजें' : 'Track by Code'}
            </Link>
          </div>
        </div>

        {/* Statistical Summary Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded p-4 shadow-sm">
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              {language === 'hi' ? 'कुल दर्ज शिकायतें' : 'Total Complaints'}
            </p>
            <p className="text-2xl font-bold text-[#0b2545] mt-1">{totalCount}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Lifetime submissions</p>
          </div>

          <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-amber-500">
            <p className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">
              {language === 'hi' ? 'प्रक्रियाधीन / लंबित' : 'Under Action'}
            </p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{inProgressCount}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Assigned or in progress</p>
          </div>

          <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-emerald-600">
            <p className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">
              {language === 'hi' ? 'निस्तारित शिकायतें' : 'Resolved'}
            </p>
            <p className="text-2xl font-bold text-emerald-700 mt-1">{resolvedCount}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Successfully closed</p>
          </div>

          <div className="bg-white border border-slate-200 rounded p-4 shadow-sm border-l-4 border-l-rose-600">
            <p className="text-[11px] font-bold text-rose-700 uppercase tracking-wider">
              {language === 'hi' ? 'समयसीमा समाप्त (Overdue)' : 'Overdue SLA'}
            </p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{overdueCount}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">High priority escalation</p>
          </div>
        </div>

        {/* Complaints Register Table Section */}
        <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden">
          {/* Controls Bar */}
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="w-full sm:w-72">
              <input
                type="text"
                placeholder={
                  language === 'hi'
                    ? 'शिकायत संख्या या विषय खोजें...'
                    : 'Search complaint no or subject...'
                }
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-[#0b2545] focus:border-[#0b2545]"
              />
            </div>

            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <span className="text-xs font-bold text-slate-600 uppercase tracking-wider whitespace-nowrap">
                Status:
              </span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-2.5 py-1.5 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-[#0b2545]"
              >
                <option value="ALL">All Statuses</option>
                <option value="SUBMITTED">SUBMITTED</option>
                <option value="ASSIGNED">ASSIGNED</option>
                <option value="IN_PROGRESS">IN_PROGRESS</option>
                <option value="ON_HOLD">ON_HOLD</option>
                <option value="RESOLVED">RESOLVED</option>
                <option value="CLOSED">CLOSED</option>
                <option value="REOPENED">REOPENED</option>
              </select>
              <button
                onClick={fetchMyComplaints}
                title="Refresh complaints list"
                className="p-1.5 border border-slate-300 rounded bg-white hover:bg-slate-100 text-slate-600 text-xs"
              >
                ↻
              </button>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-600 font-semibold">
              Loading complaints register...
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-12 h-12 mx-auto mb-3 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 text-xl font-bold">
                📋
              </div>
              <p className="text-sm font-bold text-slate-700">
                {language === 'hi'
                  ? 'कोई शिकायत नहीं मिली'
                  : 'No Grievance Records Found'}
              </p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                {language === 'hi'
                  ? 'आपने अभी तक कोई शिकायत दर्ज नहीं की है या दिए गए फ़िल्टर से कोई मेल नहीं खाता।'
                  : 'You have not submitted any complaints matching this criteria yet.'}
              </p>
              <div className="mt-4">
                <Link
                  href="/submit"
                  className="px-4 py-2 bg-[#0b2545] text-white text-xs font-bold rounded hover:bg-[#134074]"
                >
                  File First Grievance
                </Link>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 text-slate-800 border-b border-slate-200">
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Complaint No</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Subject & Category</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">District</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Status</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Priority</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider">Target SLA</th>
                    <th className="py-3 px-4 font-bold uppercase tracking-wider text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filtered.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 font-bold text-[#0b2545] whitespace-nowrap">
                        <Link
                          href={`/complaints/${item.id}`}
                          className="hover:underline flex items-center"
                        >
                          {item.complaint_no}
                          {item.is_overdue && (
                            <span className="ml-1.5 w-2 h-2 rounded-full bg-rose-500 inline-block" title="SLA Overdue" />
                          )}
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-semibold text-slate-900 truncate max-w-xs">{item.subject}</p>
                        <p className="text-[10px] text-slate-500 mt-0.5 truncate">
                          {item.category?.name_en || 'Public Service'}
                        </p>
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800 whitespace-nowrap">
                        {item.district_code}
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
                          year: 'numeric',
                        })}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <Link
                          href={`/complaints/${item.id}`}
                          className="px-2.5 py-1 bg-slate-100 hover:bg-[#0b2545] hover:text-white border border-slate-300 rounded text-[11px] font-bold text-slate-700 transition-colors"
                        >
                          View Dossier →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Helpful Government Grievance Guidelines Box */}
        <div className="bg-amber-50/70 border border-amber-200 rounded p-4 text-xs text-amber-950 flex items-start space-x-3">
          <span className="text-xl">ℹ️</span>
          <div>
            <p className="font-bold">
              {language === 'hi' ? 'नागरिक अधिकार पत्र (Citizen Charter):' : 'Citizen Charter SLA Notice:'}
            </p>
            <p className="text-amber-900 mt-0.5 leading-relaxed">
              Under the Madhya Pradesh Public Services Guarantee Act, every grievance is bound to a strict resolution timeline. If your grievance exceeds the SLA deadline without resolution, it is marked as overdue and automatically reported to the District Magistrate.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

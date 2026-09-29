import React from 'react';
import { ComplaintStatus } from '../types';

interface StatusBadgeProps {
  status: ComplaintStatus | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const statusMap: Record<string, { label: string; className: string }> = {
    SUBMITTED: { label: 'दर्ज (Submitted)', className: 'badge-submitted' },
    RECEIVED: { label: 'प्राप्त (Received)', className: 'badge-received' },
    ASSIGNED: { label: 'आवंटित (Assigned)', className: 'badge-assigned' },
    IN_PROGRESS: { label: 'प्रगति पर (In Progress)', className: 'badge-in-progress' },
    ON_HOLD: { label: 'स्थगित (On Hold)', className: 'badge-on-hold' },
    RESOLVED: { label: 'निराकृत (Resolved)', className: 'badge-resolved' },
    CLOSED: { label: 'बंद (Closed)', className: 'badge-closed' },
    REJECTED: { label: 'अस्वीकृत (Rejected)', className: 'badge-rejected' },
    REOPENED: { label: 'पुनः खुला (Reopened)', className: 'badge-reopened' },
  };

  const conf = statusMap[status] || { label: status, className: 'badge-closed' };

  return <span className={`badge ${conf.className}`}>{conf.label}</span>;
};

export default StatusBadge;

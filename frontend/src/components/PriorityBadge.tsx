import React from 'react';
import { Priority } from '../types';

interface PriorityBadgeProps {
  priority: Priority | string;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
  const map: Record<string, { label: string; className: string }> = {
    LOW: { label: 'सामान्य (Low)', className: 'badge-low' },
    MEDIUM: { label: 'मध्यम (Medium)', className: 'badge-medium' },
    HIGH: { label: 'उच्च प्राथमिकता (High)', className: 'badge-high' },
  };

  const conf = map[priority] || { label: priority, className: 'badge-medium' };

  return <span className={`badge ${conf.className}`}>{conf.label}</span>;
};

export default PriorityBadge;

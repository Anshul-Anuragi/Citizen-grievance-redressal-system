'use client';

import React, { useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import { UserRole } from '../types';

interface ProtectedRouteProps {
  children: ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.replace('/login');
      } else if (allowedRoles && !allowedRoles.includes(user.role)) {
        router.replace('/');
      }
    }
  }, [user, loading, allowedRoles, router]);

  if (loading) {
    return (
      <div
        style={{
          padding: '5rem 1.5rem',
          textAlign: 'center',
          color: 'var(--text-muted)',
        }}
      >
        <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: 'var(--gov-navy)' }}>
          सत्र सत्यापित किया जा रहा है... (Verifying secure session...)
        </div>
      </div>
    );
  }

  if (!user) return null;
  if (allowedRoles && !allowedRoles.includes(user.role)) return null;

  return <>{children}</>;
};

export default ProtectedRoute;

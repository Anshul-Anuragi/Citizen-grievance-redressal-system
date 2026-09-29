'use client';

import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const GOV_CHART_COLORS = ['#0e3b64', '#1d70b8', '#b45309', '#047857', '#64748b', '#475569'];

interface ChartDataItem {
  name_en: string;
  count: number;
}

interface PublicAnalyticsChartProps {
  data: ChartDataItem[];
}

export const PublicAnalyticsChart: React.FC<PublicAnalyticsChartProps> = ({ data }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !data || data.length === 0) {
    return (
      <div
        style={{
          height: 260,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.85rem',
        }}
      >
        डेटा लोड हो रहा है... (Loading analytics)
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 15, right: 20, left: 0, bottom: 35 }}>
          <XAxis
            dataKey="name_en"
            angle={-15}
            textAnchor="end"
            interval={0}
            tick={{ fontSize: 11, fill: '#475569' }}
          />
          <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#475569' }} />
          <Tooltip
            contentStyle={{
              background: '#ffffff',
              borderRadius: '2px',
              border: '1px solid #cbd5e1',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              fontSize: '0.8rem',
            }}
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={GOV_CHART_COLORS[index % GOV_CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PublicAnalyticsChart;

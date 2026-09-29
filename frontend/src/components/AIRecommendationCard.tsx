import React from 'react';
import { Sparkles, CheckCircle2 } from 'lucide-react';
import { AIRecommendation } from '../types';

interface AIRecommendationCardProps {
  recommendation: AIRecommendation | null;
  onApply?: (rec: AIRecommendation) => void;
}

export const AIRecommendationCard: React.FC<AIRecommendationCardProps> = ({
  recommendation,
  onApply,
}) => {
  if (!recommendation) return null;

  const {
    suggested_category_name,
    suggested_priority,
    confidence,
    reasoning,
    provider,
  } = recommendation;

  return (
    <div
      style={{
        background: '#f0fdf4',
        border: '1px solid #bbf7d0',
        borderLeft: '4px solid var(--gov-green)',
        borderRadius: 'var(--radius-xs)',
        padding: '0.85rem 1rem',
        marginBottom: '1rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '0.35rem',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            color: 'var(--gov-green)',
            fontWeight: '700',
            fontSize: '0.85rem',
          }}
        >
          <Sparkles size={16} />
          <span>स्वचालित AI श्रेणी एवं प्राथमिकता अनुशंसा (AI Assistant)</span>
          <span
            style={{
              fontSize: '0.675rem',
              padding: '0.1rem 0.4rem',
              borderRadius: '2px',
              background: '#dcfce7',
              color: '#166534',
              border: '1px solid #86efac',
            }}
          >
            {provider === 'gemini' ? 'Gemini AI' : 'Rule Engine'}
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#047857' }}>
          विश्वास स्तर: {Math.round((confidence || 0) * 100)}%
        </div>
      </div>

      <div style={{ fontSize: '0.825rem', color: '#334155', marginBottom: '0.65rem' }}>
        <div>
          <strong>अनुशंसित श्रेणी (Category):</strong> {suggested_category_name || 'नागरिक सेवा'}
        </div>
        <div>
          <strong>अनुशंसित प्राथमिकता (Priority):</strong> {suggested_priority || 'MEDIUM'}
        </div>
        <div style={{ fontSize: '0.775rem', color: '#64748b', marginTop: '0.2rem' }}>
          <em>आधार: {reasoning}</em>
        </div>
      </div>

      {onApply && (
        <button
          type="button"
          onClick={() => onApply(recommendation)}
          className="btn btn-green"
          style={{ fontSize: '0.775rem', padding: '0.3rem 0.65rem' }}
        >
          <CheckCircle2 size={13} /> यह अनुशंसा लागू करें (Apply Recommendation)
        </button>
      )}
    </div>
  );
};

export default AIRecommendationCard;

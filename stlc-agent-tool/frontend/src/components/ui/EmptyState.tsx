import React from 'react';
import { cn } from './Button';

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  headline: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, headline, description, action, className, ...props }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center min-h-[400px] border border-dashed border-border rounded-lg bg-main/50',
        className
      )}
      {...props}
    >
      {icon && <div className="mb-4 text-secondary">{icon}</div>}
      <h3 className="mb-2 text-lg font-semibold text-primary">{headline}</h3>
      {description && <p className="mb-6 text-sm text-secondary max-w-sm">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}

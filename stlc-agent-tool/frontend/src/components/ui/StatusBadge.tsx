import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react';
import { cn } from './Button';

interface StatusBadgeProps {
  status: 'pass' | 'fail' | 'flaky' | 'pending';
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = {
    pass: {
      icon: CheckCircle,
      text: 'Pass',
      classes: 'text-success border-success/30 bg-success/10',
    },
    fail: {
      icon: XCircle,
      text: 'Fail',
      classes: 'text-fail border-fail/30 bg-fail/10',
    },
    flaky: {
      icon: AlertTriangle,
      text: 'Flaky',
      classes: 'text-warning border-warning/30 bg-warning/10',
    },
    pending: {
      icon: Clock,
      text: 'Pending',
      classes: 'text-info border-info/30 bg-info/10',
    },
  };

  const { icon: Icon, text, classes } = config[status];

  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-xs font-medium', classes, className)}>
      <Icon className="w-3.5 h-3.5" />
      {text}
    </span>
  );
}

import React, { useState, useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, Info, XCircle } from 'lucide-react';
import { cn } from './Button';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastProps {
  id: string;
  type?: ToastType;
  title: string;
  message?: string;
  onClose: (id: string) => void;
  duration?: number;
}

export function Toast({ id, type = 'info', title, message, onClose, duration = 5000 }: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => onClose(id), duration);
      return () => clearTimeout(timer);
    }
  }, [duration, id, onClose]);

  const config = {
    success: { icon: CheckCircle, classes: 'border-success text-success' },
    error: { icon: XCircle, classes: 'border-fail text-fail' },
    warning: { icon: AlertTriangle, classes: 'border-warning text-warning' },
    info: { icon: Info, classes: 'border-info text-info' },
  };

  const { icon: Icon, classes } = config[type];

  return (
    <div className={cn("flex w-full max-w-sm overflow-hidden bg-elevated border rounded-lg shadow-md pointer-events-auto", classes)}>
      <div className="flex items-start p-4">
        <Icon className="w-5 h-5 mt-0.5 shrink-0" />
        <div className="ml-3 w-0 flex-1 pt-0.5">
          <p className="text-sm font-medium text-primary">{title}</p>
          {message && <p className="mt-1 text-sm text-secondary">{message}</p>}
        </div>
        <div className="ml-4 flex shrink-0">
          <button
            type="button"
            className="inline-flex rounded-md bg-transparent text-secondary hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            onClick={() => onClose(id)}
          >
            <span className="sr-only">Close</span>
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}

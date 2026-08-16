import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from './Button';

interface AccordionProps {
  title: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

// NOTE: This exact Accordion component is designed to be fully portable.
// It will be reused unmodified by Batch 11 for the HTML reporting exports.
// Do NOT introduce heavy context or complex dependencies here.
export function Accordion({ title, children, defaultOpen = false, className }: AccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={cn('border border-border rounded-md overflow-hidden', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between bg-card px-4 py-3 text-left focus-visible:outline-none focus-visible:bg-elevated hover:bg-elevated transition-colors"
        aria-expanded={isOpen}
      >
        <div className="font-medium text-primary">{title}</div>
        {isOpen ? (
          <ChevronDown className="h-5 w-5 text-secondary" />
        ) : (
          <ChevronRight className="h-5 w-5 text-secondary" />
        )}
      </button>
      {isOpen && (
        <div className="bg-main px-4 py-3 text-sm text-text-primary border-t border-border">
          {children}
        </div>
      )}
    </div>
  );
}

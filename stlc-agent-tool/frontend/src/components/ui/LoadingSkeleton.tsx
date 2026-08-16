import React from 'react';
import { cn } from './Button';

export function LoadingSkeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-border/50', className)}
      {...props}
    />
  );
}

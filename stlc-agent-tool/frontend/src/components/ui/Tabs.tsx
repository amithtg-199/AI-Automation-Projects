import React, { useState } from 'react';
import { cn } from './Button';

interface TabsProps {
  defaultValue: string;
  className?: string;
  children: React.ReactNode;
}

export const TabsContext = React.createContext<{
  value: string;
  setValue: (val: string) => void;
}>({ value: '', setValue: () => {} });

export function Tabs({ defaultValue, className, children }: TabsProps) {
  const [value, setValue] = useState(defaultValue);
  return (
    <TabsContext.Provider value={{ value, setValue }}>
      <div className={cn('w-full', className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'inline-flex h-9 border-b border-border w-full justify-start',
        className
      )}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string }) {
  const { value: selectedValue, setValue } = React.useContext(TabsContext);
  const isSelected = selectedValue === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isSelected}
      onClick={() => setValue(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap px-4 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary border-b-2',
        isSelected
          ? 'border-primary text-primary'
          : 'border-transparent text-secondary hover:text-primary hover:border-border',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { value: string }) {
  const { value: selectedValue } = React.useContext(TabsContext);
  
  if (selectedValue !== value) return null;
  
  return (
    <div
      role="tabpanel"
      className={cn('mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary', className)}
      {...props}
    >
      {children}
    </div>
  );
}

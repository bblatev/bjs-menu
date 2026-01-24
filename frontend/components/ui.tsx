'use client';

import React, { forwardRef, ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';
import Link from 'next/link';

// ============================================
// BUTTON COMPONENT
// ============================================
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'success' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    children, 
    variant = 'primary', 
    size = 'md', 
    isLoading = false,
    leftIcon,
    rightIcon,
    className = '',
    disabled,
    ...props 
  }, ref) => {
    const baseStyles = `
      inline-flex items-center justify-center gap-2 font-semibold 
      rounded-xl transition-all duration-200 ease-out
      focus:outline-none focus:ring-2 focus:ring-offset-2
      disabled:opacity-50 disabled:cursor-not-allowed
      active:scale-[0.98]
    `;
    
    const variants = {
      primary: `
        bg-gradient-to-br from-primary-500 to-primary-600 text-white
        hover:from-primary-400 hover:to-primary-500 hover:shadow-lg hover:shadow-primary-500/25
        focus:ring-primary-500
      `,
      secondary: `
        bg-white text-surface-700 border border-surface-200
        hover:bg-surface-50 hover:border-primary-300
        focus:ring-primary-500
      `,
      accent: `
        bg-gradient-to-br from-accent-500 to-accent-600 text-white
        hover:from-accent-400 hover:to-accent-500 hover:shadow-lg hover:shadow-accent-500/25
        focus:ring-accent-500
      `,
      success: `
        bg-gradient-to-br from-success-500 to-success-600 text-white
        hover:from-success-400 hover:to-success-500 hover:shadow-lg hover:shadow-success-500/25
        focus:ring-success-500
      `,
      danger: `
        bg-gradient-to-br from-error-500 to-error-600 text-white
        hover:from-error-400 hover:to-error-500 hover:shadow-lg hover:shadow-error-500/25
        focus:ring-error-500
      `,
      ghost: `
        bg-transparent text-surface-600
        hover:bg-surface-100 hover:text-surface-900
        focus:ring-primary-500
      `,
    };
    
    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-5 py-2.5 text-sm',
      lg: 'px-8 py-3.5 text-base',
    };
    
    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : leftIcon}
        {children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);
Button.displayName = 'Button';

// ============================================
// INPUT COMPONENT
// ============================================
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, leftIcon, rightIcon, className = '', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-surface-600 mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            className={`
              w-full px-4 py-3 rounded-xl border bg-white
              text-surface-900 placeholder:text-surface-400
              transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500
              ${leftIcon ? 'pl-10' : ''}
              ${rightIcon ? 'pr-10' : ''}
              ${error ? 'border-error-500 focus:ring-error-500/20 focus:border-error-500' : 'border-surface-200 hover:border-surface-300'}
              ${className}
            `}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400">
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-1.5 text-sm text-error-600">{error}</p>
        )}
      </div>
    );
  }
);
Input.displayName = 'Input';

// ============================================
// CARD COMPONENT
// ============================================
interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export const Card = ({ children, className = '', hover = false, onClick }: CardProps) => (
  <div 
    className={`
      bg-white rounded-2xl border border-surface-200 
      shadow-sm overflow-hidden
      ${hover ? 'hover:shadow-lg hover:border-surface-300 hover:-translate-y-0.5 transition-all duration-300 cursor-pointer' : ''}
      ${className}
    `}
    onClick={onClick}
  >
    {children}
  </div>
);

export const CardHeader = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <div className={`px-6 py-4 border-b border-surface-100 bg-gradient-to-r from-surface-50 to-white ${className}`}>
    {children}
  </div>
);

export const CardBody = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <div className={`p-6 ${className}`}>
    {children}
  </div>
);

export const CardFooter = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <div className={`px-6 py-4 border-t border-surface-100 bg-surface-50 ${className}`}>
    {children}
  </div>
);

// ============================================
// BADGE COMPONENT
// ============================================
interface BadgeProps {
  children: ReactNode;
  variant?: 'primary' | 'success' | 'warning' | 'error' | 'accent' | 'neutral';
  size?: 'sm' | 'md';
  dot?: boolean;
}

export const Badge = ({ children, variant = 'neutral', size = 'md', dot = false }: BadgeProps) => {
  const variants = {
    primary: 'bg-primary-100 text-primary-700',
    success: 'bg-success-100 text-success-700',
    warning: 'bg-warning-100 text-warning-700',
    error: 'bg-error-100 text-error-700',
    accent: 'bg-accent-100 text-accent-700',
    neutral: 'bg-surface-100 text-surface-600',
  };
  
  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
  };
  
  return (
    <span className={`inline-flex items-center gap-1.5 font-semibold rounded-full uppercase tracking-wide ${variants[variant]} ${sizes[size]}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${variant === 'success' ? 'bg-success-500' : variant === 'error' ? 'bg-error-500' : 'bg-current'}`} />}
      {children}
    </span>
  );
};

// ============================================
// STAT CARD COMPONENT
// ============================================
interface StatCardProps {
  label: string;
  value: string | number;
  change?: { value: number; label?: string };
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
}

export const StatCard = ({ label, value, change, icon, trend }: StatCardProps) => (
  <Card className="p-5">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-surface-500 mb-1">{label}</p>
        <p className="text-3xl font-display font-bold text-surface-900">{value}</p>
        {change && (
          <div className={`flex items-center gap-1 mt-2 text-sm font-medium ${
            trend === 'up' ? 'text-success-600' : trend === 'down' ? 'text-error-600' : 'text-surface-500'
          }`}>
            {trend === 'up' && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            )}
            {trend === 'down' && (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
            )}
            <span>{change.value > 0 ? '+' : ''}{change.value}%</span>
            {change.label && <span className="text-surface-400">{change.label}</span>}
          </div>
        )}
      </div>
      {icon && (
        <div className="p-3 bg-primary-50 rounded-xl text-primary-600">
          {icon}
        </div>
      )}
    </div>
  </Card>
);

// ============================================
// NAVIGATION ITEM COMPONENT
// ============================================
interface NavItemProps {
  href: string;
  icon: ReactNode;
  label: string;
  active?: boolean;
  badge?: string | number;
}

export const NavItem = ({ href, icon, label, active = false, badge }: NavItemProps) => (
  <Link
    href={href}
    className={`
      flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm
      transition-all duration-200
      ${active 
        ? 'bg-primary-50 text-primary-700 shadow-sm' 
        : 'text-surface-600 hover:bg-surface-100 hover:text-surface-900'
      }
    `}
  >
    <span className={`${active ? 'text-primary-600' : 'text-surface-400'}`}>{icon}</span>
    <span className="flex-1">{label}</span>
    {badge && (
      <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
        active ? 'bg-primary-600 text-white' : 'bg-surface-200 text-surface-600'
      }`}>
        {badge}
      </span>
    )}
  </Link>
);

// ============================================
// AVATAR COMPONENT
// ============================================
interface AvatarProps {
  src?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  status?: 'online' | 'offline' | 'busy';
}

export const Avatar = ({ src, name, size = 'md', status }: AvatarProps) => {
  const sizes = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
    xl: 'w-16 h-16 text-lg',
  };
  
  const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  
  return (
    <div className="relative inline-flex">
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={name} className={`${sizes[size]} rounded-full object-cover ring-2 ring-white`} />
      ) : (
        <div className={`${sizes[size]} rounded-full bg-gradient-to-br from-primary-400 to-primary-600 text-white font-semibold flex items-center justify-center ring-2 ring-white`}>
          {initials}
        </div>
      )}
      {status && (
        <span className={`absolute bottom-0 right-0 w-3 h-3 rounded-full ring-2 ring-white ${
          status === 'online' ? 'bg-success-500' : status === 'busy' ? 'bg-warning-500' : 'bg-surface-400'
        }`} />
      )}
    </div>
  );
};

// ============================================
// EMPTY STATE COMPONENT
// ============================================
interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export const EmptyState = ({ icon, title, description, action }: EmptyStateProps) => (
  <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
    {icon && (
      <div className="w-16 h-16 rounded-2xl bg-surface-100 flex items-center justify-center text-surface-400 mb-4">
        {icon}
      </div>
    )}
    <h3 className="text-lg font-semibold text-surface-900 mb-1">{title}</h3>
    {description && <p className="text-sm text-surface-500 max-w-sm mb-4">{description}</p>}
    {action && (
      <Button variant="primary" onClick={action.onClick}>
        {action.label}
      </Button>
    )}
  </div>
);

// ============================================
// LOADING SPINNER COMPONENT
// ============================================
export const Spinner = ({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) => {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' };
  return (
    <svg className={`animate-spin ${sizes[size]} text-primary-600`} viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
};

// ============================================
// SKELETON COMPONENT
// ============================================
export const Skeleton = ({ className = '' }: { className?: string }) => (
  <div className={`animate-pulse bg-gradient-to-r from-surface-200 via-surface-100 to-surface-200 bg-[length:200%_100%] rounded-lg ${className}`} />
);

// ============================================
// DIVIDER COMPONENT
// ============================================
export const Divider = ({ label }: { label?: string }) => (
  <div className="flex items-center gap-4 my-6">
    <div className="flex-1 h-px bg-surface-200" />
    {label && <span className="text-sm text-surface-400 font-medium">{label}</span>}
    <div className="flex-1 h-px bg-surface-200" />
  </div>
);

// ============================================
// TOOLTIP COMPONENT (Simple)
// ============================================
interface TooltipProps {
  children: ReactNode;
  content: string;
}

export const Tooltip = ({ children, content }: TooltipProps) => (
  <div className="relative group inline-flex">
    {children}
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-800 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 whitespace-nowrap z-50">
      {content}
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
    </div>
  </div>
);

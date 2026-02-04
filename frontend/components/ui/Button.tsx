'use client';

import { ButtonHTMLAttributes, forwardRef, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: `
    bg-amber-500 text-gray-900
    hover:bg-amber-600
    focus:ring-amber-500
    disabled:bg-amber-300
  `,
  secondary: `
    bg-surface-100 dark:bg-surface-700
    text-surface-900 dark:text-surface-100
    hover:bg-surface-200 dark:hover:bg-surface-600
    focus:ring-surface-500
    disabled:bg-surface-50 dark:disabled:bg-surface-800
  `,
  outline: `
    border-2 border-surface-300 dark:border-surface-600
    text-surface-700 dark:text-surface-300
    hover:bg-surface-50 dark:hover:bg-surface-800
    focus:ring-surface-500
    disabled:border-surface-200 disabled:text-surface-400
  `,
  ghost: `
    text-surface-600 dark:text-surface-400
    hover:bg-surface-100 dark:hover:bg-surface-800
    focus:ring-surface-500
    disabled:text-surface-400
  `,
  danger: `
    bg-red-500 text-white
    hover:bg-red-600
    focus:ring-red-500
    disabled:bg-red-300
  `,
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      children,
      disabled,
      className = '',
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`
          inline-flex items-center justify-center
          font-medium rounded-lg
          transition-all duration-150
          focus:outline-none focus:ring-2 focus:ring-offset-2
          disabled:cursor-not-allowed
          active:scale-[0.98]
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${fullWidth ? 'w-full' : ''}
          ${className}
        `}
        aria-busy={isLoading}
        {...props}
      >
        {isLoading ? (
          <>
            <LoadingSpinner size={size} />
            <span>Loading...</span>
          </>
        ) : (
          <>
            {leftIcon && <span aria-hidden="true">{leftIcon}</span>}
            {children}
            {rightIcon && <span aria-hidden="true">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

function LoadingSpinner({ size }: { size: ButtonSize }) {
  const sizeClass = size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-5 h-5' : 'w-4 h-4';

  return (
    <svg
      className={`animate-spin ${sizeClass}`}
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

// Icon button for toolbar actions
interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ label, variant = 'ghost', size = 'md', children, className = '', ...props }, ref) => {
    const sizeClasses = {
      sm: 'w-8 h-8',
      md: 'w-10 h-10',
      lg: 'w-12 h-12',
    };

    const variantClasses = {
      ghost: 'hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-600 dark:text-surface-400',
      outline: 'border border-surface-300 dark:border-surface-600 hover:bg-surface-50 dark:hover:bg-surface-800',
    };

    return (
      <button
        ref={ref}
        aria-label={label}
        className={`
          inline-flex items-center justify-center
          rounded-lg transition-colors
          focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
          disabled:opacity-50 disabled:cursor-not-allowed
          ${sizeClasses[size]}
          ${variantClasses[variant]}
          ${className}
        `}
        {...props}
      >
        {children}
      </button>
    );
  }
);

IconButton.displayName = 'IconButton';

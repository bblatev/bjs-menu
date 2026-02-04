'use client';

import { ReactNode, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react';

interface FormFieldProps {
  label: string;
  name: string;
  error?: string;
  touched?: boolean;
  required?: boolean;
  helpText?: string;
  children: ReactNode;
}

export function FormField({
  label,
  name,
  error,
  touched,
  required,
  helpText,
  children,
}: FormFieldProps) {
  const showError = touched && error;
  const inputId = `field-${name}`;
  const errorId = `${inputId}-error`;
  const helpId = `${inputId}-help`;

  return (
    <div className="space-y-1">
      <label
        htmlFor={inputId}
        className="block text-sm font-medium text-surface-700 dark:text-surface-300"
      >
        {label}
        {required && (
          <span className="text-red-500 ml-1" aria-hidden="true">
            *
          </span>
        )}
      </label>

      <div className="relative">
        {children}
      </div>

      {helpText && !showError && (
        <p id={helpId} className="text-xs text-surface-500 dark:text-surface-400">
          {helpText}
        </p>
      )}

      {showError && (
        <p
          id={errorId}
          className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1"
          role="alert"
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'onBlur'> {
  name: string;
  error?: string;
  touched?: boolean;
  onChange?: (name: string, value: string) => void;
  onBlur?: (name: string) => void;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ name, error, touched, onChange, onBlur, className = '', ...props }, ref) => {
    const showError = touched && error;
    const inputId = `field-${name}`;
    const errorId = `${inputId}-error`;

    return (
      <input
        ref={ref}
        id={inputId}
        name={name}
        onChange={(e) => onChange?.(name, e.target.value)}
        onBlur={() => onBlur?.(name)}
        aria-invalid={showError ? 'true' : 'false'}
        aria-describedby={showError ? errorId : undefined}
        className={`
          w-full px-3 py-2 rounded-lg border transition-colors
          ${showError
            ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
            : 'border-surface-300 dark:border-surface-600 focus:ring-primary-500 focus:border-primary-500'
          }
          bg-white dark:bg-surface-800
          text-surface-900 dark:text-surface-100
          placeholder-surface-400 dark:placeholder-surface-500
          focus:outline-none focus:ring-2 focus:ring-opacity-50
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}
        `}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'onChange' | 'onBlur'> {
  name: string;
  error?: string;
  touched?: boolean;
  onChange?: (name: string, value: string) => void;
  onBlur?: (name: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ name, error, touched, onChange, onBlur, options, placeholder, className = '', ...props }, ref) => {
    const showError = touched && error;
    const inputId = `field-${name}`;
    const errorId = `${inputId}-error`;

    return (
      <select
        ref={ref}
        id={inputId}
        name={name}
        onChange={(e) => onChange?.(name, e.target.value)}
        onBlur={() => onBlur?.(name)}
        aria-invalid={showError ? 'true' : 'false'}
        aria-describedby={showError ? errorId : undefined}
        className={`
          w-full px-3 py-2 rounded-lg border transition-colors
          ${showError
            ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
            : 'border-surface-300 dark:border-surface-600 focus:ring-primary-500 focus:border-primary-500'
          }
          bg-white dark:bg-surface-800
          text-surface-900 dark:text-surface-100
          focus:outline-none focus:ring-2 focus:ring-opacity-50
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}
        `}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  }
);

Select.displayName = 'Select';

interface TextareaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'onChange' | 'onBlur'> {
  name: string;
  error?: string;
  touched?: boolean;
  onChange?: (name: string, value: string) => void;
  onBlur?: (name: string) => void;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ name, error, touched, onChange, onBlur, className = '', ...props }, ref) => {
    const showError = touched && error;
    const inputId = `field-${name}`;
    const errorId = `${inputId}-error`;

    return (
      <textarea
        ref={ref}
        id={inputId}
        name={name}
        onChange={(e) => onChange?.(name, e.target.value)}
        onBlur={() => onBlur?.(name)}
        aria-invalid={showError ? 'true' : 'false'}
        aria-describedby={showError ? errorId : undefined}
        className={`
          w-full px-3 py-2 rounded-lg border transition-colors resize-y min-h-[100px]
          ${showError
            ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
            : 'border-surface-300 dark:border-surface-600 focus:ring-primary-500 focus:border-primary-500'
          }
          bg-white dark:bg-surface-800
          text-surface-900 dark:text-surface-100
          placeholder-surface-400 dark:placeholder-surface-500
          focus:outline-none focus:ring-2 focus:ring-opacity-50
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}
        `}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'type'> {
  name: string;
  label: string;
  error?: string;
  touched?: boolean;
  onChange?: (name: string, checked: boolean) => void;
}

export function Checkbox({
  name,
  label,
  error,
  touched,
  onChange,
  className = '',
  ...props
}: CheckboxProps) {
  const showError = touched && error;
  const inputId = `field-${name}`;

  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        id={inputId}
        name={name}
        onChange={(e) => onChange?.(name, e.target.checked)}
        className={`
          w-4 h-4 rounded border transition-colors
          ${showError
            ? 'border-red-500 text-red-500 focus:ring-red-500'
            : 'border-surface-300 dark:border-surface-600 text-primary-500 focus:ring-primary-500'
          }
          bg-white dark:bg-surface-800
          focus:ring-2 focus:ring-opacity-50
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}
        `}
        {...props}
      />
      <span className="text-sm text-surface-700 dark:text-surface-300">{label}</span>
    </label>
  );
}

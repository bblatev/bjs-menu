import { useState, useCallback } from 'react';

type ValidationRule<T> = {
  validate: (value: T) => boolean;
  message: string;
};

type FieldRules<T> = {
  [K in keyof T]?: ValidationRule<T[K]>[];
};

type FieldErrors<T> = {
  [K in keyof T]?: string;
};

type TouchedFields<T> = {
  [K in keyof T]?: boolean;
};

export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  rules: FieldRules<T>
) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<FieldErrors<T>>({});
  const [touched, setTouched] = useState<TouchedFields<T>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateField = useCallback(
    (name: keyof T, value: T[keyof T]): string | undefined => {
      const fieldRules = rules[name];
      if (!fieldRules) return undefined;

      for (const rule of fieldRules) {
        if (!rule.validate(value)) {
          return rule.message;
        }
      }
      return undefined;
    },
    [rules]
  );

  const validateAll = useCallback((): boolean => {
    const newErrors: FieldErrors<T> = {};
    let isValid = true;

    for (const key of Object.keys(rules) as (keyof T)[]) {
      const error = validateField(key, values[key]);
      if (error) {
        newErrors[key] = error;
        isValid = false;
      }
    }

    setErrors(newErrors);
    return isValid;
  }, [rules, values, validateField]);

  const handleChange = useCallback(
    (name: keyof T, value: T[keyof T]) => {
      setValues((prev) => ({ ...prev, [name]: value }));

      // Clear error when field is modified
      if (touched[name]) {
        const error = validateField(name, value);
        setErrors((prev) => ({ ...prev, [name]: error }));
      }
    },
    [touched, validateField]
  );

  const handleBlur = useCallback(
    (name: keyof T) => {
      setTouched((prev) => ({ ...prev, [name]: true }));
      const error = validateField(name, values[name]);
      setErrors((prev) => ({ ...prev, [name]: error }));
    },
    [values, validateField]
  );

  const handleSubmit = useCallback(
    async (onSubmit: (values: T) => Promise<void> | void) => {
      // Mark all fields as touched
      const allTouched = Object.keys(rules).reduce(
        (acc, key) => ({ ...acc, [key]: true }),
        {} as TouchedFields<T>
      );
      setTouched(allTouched);

      if (!validateAll()) {
        return false;
      }

      setIsSubmitting(true);
      try {
        await onSubmit(values);
        return true;
      } finally {
        setIsSubmitting(false);
      }
    },
    [rules, values, validateAll]
  );

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
  }, [initialValues]);

  const setFieldValue = useCallback((name: keyof T, value: T[keyof T]) => {
    handleChange(name, value);
  }, [handleChange]);

  return {
    values,
    errors,
    touched,
    isSubmitting,
    handleChange,
    handleBlur,
    handleSubmit,
    validateAll,
    reset,
    setFieldValue,
    setValues,
  };
}

// Common validation rules
export const validators = {
  required: (message = 'This field is required'): ValidationRule<any> => ({
    validate: (value) => {
      if (value === null || value === undefined) return false;
      if (typeof value === 'string') return value.trim().length > 0;
      if (Array.isArray(value)) return value.length > 0;
      return true;
    },
    message,
  }),

  email: (message = 'Please enter a valid email'): ValidationRule<string> => ({
    validate: (value) => {
      if (!value) return true; // Use required for empty check
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    },
    message,
  }),

  minLength: (min: number, message?: string): ValidationRule<string> => ({
    validate: (value) => !value || value.length >= min,
    message: message || `Must be at least ${min} characters`,
  }),

  maxLength: (max: number, message?: string): ValidationRule<string> => ({
    validate: (value) => !value || value.length <= max,
    message: message || `Must be no more than ${max} characters`,
  }),

  min: (min: number, message?: string): ValidationRule<number> => ({
    validate: (value) => value === undefined || value === null || value >= min,
    message: message || `Must be at least ${min}`,
  }),

  max: (max: number, message?: string): ValidationRule<number> => ({
    validate: (value) => value === undefined || value === null || value <= max,
    message: message || `Must be no more than ${max}`,
  }),

  pattern: (regex: RegExp, message: string): ValidationRule<string> => ({
    validate: (value) => !value || regex.test(value),
    message,
  }),

  phone: (message = 'Please enter a valid phone number'): ValidationRule<string> => ({
    validate: (value) => {
      if (!value) return true;
      return /^[\d\s\-+()]{10,}$/.test(value);
    },
    message,
  }),

  url: (message = 'Please enter a valid URL'): ValidationRule<string> => ({
    validate: (value) => {
      if (!value) return true;
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message,
  }),
};

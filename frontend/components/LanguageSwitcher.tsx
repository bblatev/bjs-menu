'use client';
import { useTranslation } from 'react-i18next';

const languages = [
  { code: 'bg', label: 'БГ' },
  { code: 'en', label: 'EN' },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const handleChange = (lng: string) => {
    i18n.changeLanguage(lng);
    if (typeof window !== 'undefined') {
      localStorage.setItem('language', lng);
    }
  };

  return (
    <div className="flex items-center gap-1" role="group" aria-label="Language selector">
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => handleChange(lang.code)}
          className={`px-2 py-1 text-xs rounded ${
            i18n.language === lang.code
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 dark:bg-surface-700 text-gray-700 dark:text-surface-300'
          }`}
          aria-pressed={i18n.language === lang.code}
        >
          {lang.label}
        </button>
      ))}
    </div>
  );
}

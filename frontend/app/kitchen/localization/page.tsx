'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorAlert } from '@/components/ui/ErrorAlert';

import { API_URL, getAuthHeaders } from '@/lib/api';

interface Language {
  code: string;
  name: string;
  native_name: string;
  flag: string;
  rtl: boolean;
}

interface StationSetting {
  station_id: string;
  station_name: string;
  language_code: string;
  show_translations: boolean;
  primary_font_size: number;
  secondary_font_size: number;
}

interface Translation {
  key: string;
  en: string;
  [lang: string]: string;
}

const LANGUAGES: Language[] = [
  { code: 'en', name: 'English', native_name: 'English', flag: '🇺🇸', rtl: false },
  { code: 'es', name: 'Spanish', native_name: 'Español', flag: '🇪🇸', rtl: false },
  { code: 'zh', name: 'Chinese', native_name: '中文', flag: '🇨🇳', rtl: false },
  { code: 'vi', name: 'Vietnamese', native_name: 'Tiếng Việt', flag: '🇻🇳', rtl: false },
  { code: 'ko', name: 'Korean', native_name: '한국어', flag: '🇰🇷', rtl: false },
  { code: 'ja', name: 'Japanese', native_name: '日本語', flag: '🇯🇵', rtl: false },
  { code: 'tl', name: 'Filipino', native_name: 'Tagalog', flag: '🇵🇭', rtl: false },
  { code: 'fr', name: 'French', native_name: 'Français', flag: '🇫🇷', rtl: false },
  { code: 'de', name: 'German', native_name: 'Deutsch', flag: '🇩🇪', rtl: false },
  { code: 'it', name: 'Italian', native_name: 'Italiano', flag: '🇮🇹', rtl: false },
  { code: 'pt', name: 'Portuguese', native_name: 'Português', flag: '🇵🇹', rtl: false },
  { code: 'ru', name: 'Russian', native_name: 'Русский', flag: '🇷🇺', rtl: false },
  { code: 'ar', name: 'Arabic', native_name: 'العربية', flag: '🇸🇦', rtl: true },
  { code: 'hi', name: 'Hindi', native_name: 'हिन्दी', flag: '🇮🇳', rtl: false },
  { code: 'bg', name: 'Bulgarian', native_name: 'Български', flag: '🇧🇬', rtl: false },
];

export default function KDSLocalizationPage() {
  const [stations, setStations] = useState<StationSetting[]>([]);
  const [translations, setTranslations] = useState<Translation[]>([]);
  const [activeTab, setActiveTab] = useState<'stations' | 'translations' | 'preview'>('stations');
  const [selectedLanguage, setSelectedLanguage] = useState('es');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [stationsRes, translationsRes] = await Promise.all([
        fetch(`${API_URL}/kds-localization/stations`),
        fetch(`${API_URL}/kds-localization/translations`),
      ]);

      if (stationsRes.ok) {
        const data = await stationsRes.json();
        setStations(data);
      }
      if (translationsRes.ok) {
        const data = await translationsRes.json();
        setTranslations(data);
      }
    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load localization settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const updateStation = async (stationId: string, updates: Partial<StationSetting>) => {
    try {
      const res = await fetch(`${API_URL}/kds-localization/stations/${stationId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        loadData();
      }
    } catch (error) {
      console.error('Error updating station:', error);
    }
  };

  const updateTranslation = async (key: string, langCode: string, value: string) => {
    try {
      const res = await fetch(`${API_URL}/kds-localization/translations/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language_code: langCode, value }),
      });
      if (res.ok) {
        setTranslations(prev =>
          prev.map(t => t.key === key ? { ...t, [langCode]: value } : t)
        );
      }
    } catch (error) {
      console.error('Error updating translation:', error);
    }
  };

  const getLanguage = (code: string) => LANGUAGES.find(l => l.code === code);

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Header */}
      <div className="bg-white border-b border-surface-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/kitchen" className="p-2 rounded-lg hover:bg-surface-100">
                <svg className="w-5 h-5 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-surface-900">KDS Localization</h1>
                <p className="text-sm text-surface-500">Multilingual kitchen display settings</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-surface-500">{LANGUAGES.length} languages supported</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Language Overview */}
        <div className="bg-white rounded-xl border border-surface-200 p-4 mb-6">
          <h3 className="font-medium text-surface-900 mb-3">Supported Languages</h3>
          <div className="flex flex-wrap gap-2">
            {LANGUAGES.map((lang) => (
              <div
                key={lang.code}
                className="flex items-center gap-2 px-3 py-1.5 bg-surface-50 rounded-lg"
              >
                <span className="text-lg">{lang.flag}</span>
                <span className="text-sm text-surface-700">{lang.name}</span>
                {lang.rtl && (
                  <span className="text-xs px-1 bg-amber-100 text-amber-700 rounded">RTL</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'stations', label: 'Station Settings', icon: '🖥️' },
            { id: 'translations', label: 'Translations', icon: '🌐' },
            { id: 'preview', label: 'Live Preview', icon: '👁️' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                activeTab === tab.id
                  ? 'bg-amber-500 text-gray-900'
                  : 'bg-white text-surface-600 hover:bg-surface-100'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Stations Tab */}
        {activeTab === 'stations' && (
          <div className="space-y-4">
            {stations.length === 0 ? (
              <div className="bg-white rounded-xl p-12 border border-surface-200 text-center">
                <div className="text-6xl mb-4">🖥️</div>
                <h3 className="text-xl font-semibold text-surface-900 mb-2">No Kitchen Stations</h3>
                <p className="text-surface-500">Configure kitchen stations in the KDS settings first.</p>
              </div>
            ) : (
              stations.map((station) => {
                const lang = getLanguage(station.language_code);
                return (
                  <motion.div
                    key={station.station_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white rounded-xl border border-surface-200 p-6"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-surface-100 rounded-lg flex items-center justify-center text-2xl">
                          🖥️
                        </div>
                        <div>
                          <h3 className="font-semibold text-surface-900">{station.station_name}</h3>
                          <p className="text-sm text-surface-500">Station ID: {station.station_id}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{lang?.flag}</span>
                        <span className="text-surface-700">{lang?.name}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-surface-700 mb-2">
                          Display Language
                        </label>
                        <select
                          value={station.language_code}
                          onChange={(e) => updateStation(station.station_id, { language_code: e.target.value })}
                          className="w-full px-3 py-2 border border-surface-200 rounded-lg"
                        >
                          {LANGUAGES.map((l) => (
                            <option key={l.code} value={l.code}>
                              {l.flag} {l.name} ({l.native_name})
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-surface-700 mb-2">
                          Primary Font Size
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min="14"
                            max="32"
                            value={station.primary_font_size}
                            onChange={(e) => updateStation(station.station_id, { primary_font_size: parseInt(e.target.value) })}
                            className="flex-1"
                          />
                          <span className="text-sm text-surface-600 w-12">{station.primary_font_size}px</span>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-surface-700 mb-2">
                          Secondary Font Size
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min="10"
                            max="24"
                            value={station.secondary_font_size}
                            onChange={(e) => updateStation(station.station_id, { secondary_font_size: parseInt(e.target.value) })}
                            className="flex-1"
                          />
                          <span className="text-sm text-surface-600 w-12">{station.secondary_font_size}px</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 pt-4 border-t border-surface-100">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={station.show_translations}
                          onChange={(e) => updateStation(station.station_id, { show_translations: e.target.checked })}
                          className="rounded border-surface-300 text-amber-500 focus:ring-amber-500"
                        />
                        <span className="text-sm text-surface-700">
                          Show English alongside translated text (bilingual mode)
                        </span>
                      </label>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        )}

        {/* Translations Tab */}
        {activeTab === 'translations' && (
          <div className="bg-white rounded-xl border border-surface-200 overflow-hidden">
            <div className="p-4 border-b border-surface-100 flex items-center justify-between">
              <h3 className="font-semibold text-surface-900">Menu Item Translations</h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-surface-500">Translate to:</span>
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className="px-3 py-1.5 border border-surface-200 rounded-lg text-sm"
                >
                  {LANGUAGES.filter(l => l.code !== 'en').map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.flag} {l.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <table className="w-full">
              <thead className="bg-surface-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 w-1/3">
                    English (Original)
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 w-1/3">
                    {getLanguage(selectedLanguage)?.flag} {getLanguage(selectedLanguage)?.name} Translation
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-surface-700 w-1/3">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {translations.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-12 text-center text-surface-500">
                      No translations configured. Add menu items to start translating.
                    </td>
                  </tr>
                ) : (
                  translations.map((t) => (
                    <tr key={t.key} className="border-t border-surface-100">
                      <td className="px-4 py-3">
                        <div className="font-medium text-surface-900">{t.en}</div>
                        <div className="text-xs text-surface-400 font-mono">{t.key}</div>
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="text"
                          value={t[selectedLanguage] || ''}
                          onChange={(e) => updateTranslation(t.key, selectedLanguage, e.target.value)}
                          placeholder={`Enter ${getLanguage(selectedLanguage)?.name} translation...`}
                          className="w-full px-3 py-2 border border-surface-200 rounded-lg text-sm"
                          dir={getLanguage(selectedLanguage)?.rtl ? 'rtl' : 'ltr'}
                        />
                      </td>
                      <td className="px-4 py-3">
                        {t[selectedLanguage] ? (
                          <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                            Translated
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">
                            Pending
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Preview Tab */}
        {activeTab === 'preview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* English Preview */}
            <div className="bg-gray-900 rounded-xl p-4 text-white">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-lg">🇺🇸 English</h3>
                <span className="text-xs text-gray-400">Original</span>
              </div>
              <div className="space-y-3">
                <div className="bg-gray-800 rounded-lg p-3">
                  <div className="text-amber-400 font-bold text-lg">Order #1042</div>
                  <div className="text-white mt-2">1x Grilled Salmon</div>
                  <div className="text-gray-400 text-sm pl-4">- No onions</div>
                  <div className="text-gray-400 text-sm pl-4">- Extra lemon</div>
                  <div className="text-white mt-2">2x Caesar Salad</div>
                  <div className="text-gray-400 text-sm pl-4">- Dressing on side</div>
                </div>
                <div className="flex gap-2">
                  <button className="flex-1 py-2 bg-green-600 rounded-lg font-medium">Done</button>
                  <button className="flex-1 py-2 bg-red-600 rounded-lg font-medium">Bump</button>
                </div>
              </div>
            </div>

            {/* Translated Preview */}
            <div className="bg-gray-900 rounded-xl p-4 text-white">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-lg">
                  {getLanguage(selectedLanguage)?.flag} {getLanguage(selectedLanguage)?.name}
                </h3>
                <span className="text-xs text-gray-400">Translated</span>
              </div>
              <div className="space-y-3" dir={getLanguage(selectedLanguage)?.rtl ? 'rtl' : 'ltr'}>
                <div className="bg-gray-800 rounded-lg p-3">
                  <div className="text-amber-400 font-bold text-lg">
                    {selectedLanguage === 'es' ? 'Pedido #1042' :
                     selectedLanguage === 'zh' ? '订单 #1042' :
                     selectedLanguage === 'ko' ? '주문 #1042' :
                     selectedLanguage === 'ja' ? '注文 #1042' :
                     selectedLanguage === 'ar' ? 'طلب #1042' :
                     selectedLanguage === 'fr' ? 'Commande #1042' :
                     'Order #1042'}
                  </div>
                  <div className="text-white mt-2">
                    1x {selectedLanguage === 'es' ? 'Salmón a la Parrilla' :
                        selectedLanguage === 'zh' ? '烤三文鱼' :
                        selectedLanguage === 'ko' ? '구운 연어' :
                        selectedLanguage === 'ja' ? 'グリルサーモン' :
                        selectedLanguage === 'fr' ? 'Saumon Grillé' :
                        'Grilled Salmon'}
                  </div>
                  <div className="text-gray-400 text-sm pl-4">
                    - {selectedLanguage === 'es' ? 'Sin cebolla' :
                       selectedLanguage === 'zh' ? '不要洋葱' :
                       selectedLanguage === 'ko' ? '양파 빼기' :
                       selectedLanguage === 'ja' ? '玉ねぎ抜き' :
                       selectedLanguage === 'fr' ? 'Sans oignons' :
                       'No onions'}
                  </div>
                  <div className="text-gray-400 text-sm pl-4">
                    - {selectedLanguage === 'es' ? 'Limón extra' :
                       selectedLanguage === 'zh' ? '多加柠檬' :
                       selectedLanguage === 'ko' ? '레몬 추가' :
                       selectedLanguage === 'ja' ? 'レモン追加' :
                       selectedLanguage === 'fr' ? 'Citron supplémentaire' :
                       'Extra lemon'}
                  </div>
                  <div className="text-white mt-2">
                    2x {selectedLanguage === 'es' ? 'Ensalada César' :
                        selectedLanguage === 'zh' ? '凯撒沙拉' :
                        selectedLanguage === 'ko' ? '시저 샐러드' :
                        selectedLanguage === 'ja' ? 'シーザーサラダ' :
                        selectedLanguage === 'fr' ? 'Salade César' :
                        'Caesar Salad'}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button className="flex-1 py-2 bg-green-600 rounded-lg font-medium">
                    {selectedLanguage === 'es' ? 'Listo' :
                     selectedLanguage === 'zh' ? '完成' :
                     selectedLanguage === 'ko' ? '완료' :
                     selectedLanguage === 'ja' ? '完了' :
                     selectedLanguage === 'fr' ? 'Terminé' :
                     'Done'}
                  </button>
                  <button className="flex-1 py-2 bg-red-600 rounded-lg font-medium">
                    {selectedLanguage === 'es' ? 'Retirar' :
                     selectedLanguage === 'zh' ? '清除' :
                     selectedLanguage === 'ko' ? '제거' :
                     selectedLanguage === 'ja' ? '消去' :
                     selectedLanguage === 'fr' ? 'Retirer' :
                     'Bump'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

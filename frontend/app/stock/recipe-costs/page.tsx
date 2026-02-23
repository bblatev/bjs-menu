'use client';

import { useState, useEffect, useRef } from 'react';
import AdminLayout from '@/components/AdminLayout';
import { api, API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
interface Ingredient {
  id: number;
  name: string;
  quantity: number;
  unit: string;
  cost_per_unit: number;
  total_cost: number;
  percentage: number;
}

interface Recipe {
  id: number;
  name: string;
  category: string;
  selling_price: number;
  total_cost: number;
  food_cost_percentage: number;
  target_cost_percentage: number;
  gross_profit: number;
  profit_margin: number;
  portions_per_batch: number;
  cost_per_portion: number;
  ingredients: Ingredient[];
  last_updated: string;
  status: 'profitable' | 'marginal' | 'unprofitable';
}

interface RecipeStats {
  total_recipes: number;
  avg_food_cost: number;
  target_food_cost: number;
  recipes_above_target: number;
  total_potential_savings: number;
  most_profitable_category: string;
}

interface CostTrend {
  month: string;
  actual_cost: number;
  target_cost: number;
}

export default function RecipeCostsPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [stats, setStats] = useState<RecipeStats | null>(null);
  const [costTrends, setCostTrends] = useState<CostTrend[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showUnprofitableOnly, setShowUnprofitableOnly] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showImportModal, setShowImportModal] = useState(false);
  const [importData, setImportData] = useState('');
  const [importResult, setImportResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);


  useEffect(() => {
    fetchRecipeData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchRecipeData = async () => {
    setLoading(true);
    try {
      const [recipesData, statsData] = await Promise.all([
        api.get<any>('/recipes/costs'),
        api.get<any>('/recipes/costs/stats')
      ]);

      setRecipes(recipesData.recipes || recipesData);
      setStats(statsData);
    } catch {
      loadDemoData();
    } finally {
      setLoading(false);
    }
  };

  const loadDemoData = () => {
    const demoRecipes: Recipe[] = [
      {
        id: 1,
        name: 'Пилешка супа',
        category: 'Супи',
        selling_price: 8.50,
        total_cost: 2.35,
        food_cost_percentage: 27.6,
        target_cost_percentage: 30,
        gross_profit: 6.15,
        profit_margin: 72.4,
        portions_per_batch: 10,
        cost_per_portion: 2.35,
        ingredients: [
          { id: 1, name: 'Пилешко месо', quantity: 0.5, unit: 'кг', cost_per_unit: 12.00, total_cost: 6.00, percentage: 25.5 },
          { id: 2, name: 'Моркови', quantity: 0.2, unit: 'кг', cost_per_unit: 2.50, total_cost: 0.50, percentage: 2.1 },
          { id: 3, name: 'Картофи', quantity: 0.3, unit: 'кг', cost_per_unit: 1.80, total_cost: 0.54, percentage: 2.3 },
          { id: 4, name: 'Зеленчуков бульон', quantity: 1, unit: 'л', cost_per_unit: 3.50, total_cost: 3.50, percentage: 14.9 },
          { id: 5, name: 'Подправки', quantity: 1, unit: 'порция', cost_per_unit: 0.80, total_cost: 0.80, percentage: 3.4 }
        ],
        last_updated: '2024-12-28',
        status: 'profitable'
      },
      {
        id: 2,
        name: 'Телешки стек',
        category: 'Основни',
        selling_price: 32.00,
        total_cost: 14.50,
        food_cost_percentage: 45.3,
        target_cost_percentage: 35,
        gross_profit: 17.50,
        profit_margin: 54.7,
        portions_per_batch: 1,
        cost_per_portion: 14.50,
        ingredients: [
          { id: 1, name: 'Телешко филе', quantity: 0.3, unit: 'кг', cost_per_unit: 45.00, total_cost: 13.50, percentage: 93.1 },
          { id: 2, name: 'Масло', quantity: 0.03, unit: 'кг', cost_per_unit: 18.00, total_cost: 0.54, percentage: 3.7 },
          { id: 3, name: 'Подправки', quantity: 1, unit: 'порция', cost_per_unit: 0.46, total_cost: 0.46, percentage: 3.2 }
        ],
        last_updated: '2024-12-28',
        status: 'unprofitable'
      },
      {
        id: 3,
        name: 'Цезар салата',
        category: 'Салати',
        selling_price: 14.00,
        total_cost: 4.20,
        food_cost_percentage: 30.0,
        target_cost_percentage: 28,
        gross_profit: 9.80,
        profit_margin: 70.0,
        portions_per_batch: 1,
        cost_per_portion: 4.20,
        ingredients: [
          { id: 1, name: 'Айсберг', quantity: 0.15, unit: 'кг', cost_per_unit: 5.00, total_cost: 0.75, percentage: 17.9 },
          { id: 2, name: 'Пилешки гърди', quantity: 0.1, unit: 'кг', cost_per_unit: 15.00, total_cost: 1.50, percentage: 35.7 },
          { id: 3, name: 'Пармезан', quantity: 0.03, unit: 'кг', cost_per_unit: 35.00, total_cost: 1.05, percentage: 25.0 },
          { id: 4, name: 'Крутони', quantity: 0.03, unit: 'кг', cost_per_unit: 8.00, total_cost: 0.24, percentage: 5.7 },
          { id: 5, name: 'Цезар сос', quantity: 0.04, unit: 'л', cost_per_unit: 16.50, total_cost: 0.66, percentage: 15.7 }
        ],
        last_updated: '2024-12-27',
        status: 'marginal'
      },
      {
        id: 4,
        name: 'Тирамису',
        category: 'Десерти',
        selling_price: 9.50,
        total_cost: 2.85,
        food_cost_percentage: 30.0,
        target_cost_percentage: 32,
        gross_profit: 6.65,
        profit_margin: 70.0,
        portions_per_batch: 8,
        cost_per_portion: 2.85,
        ingredients: [
          { id: 1, name: 'Маскарпоне', quantity: 0.25, unit: 'кг', cost_per_unit: 28.00, total_cost: 7.00, percentage: 30.7 },
          { id: 2, name: 'Савоярди', quantity: 0.2, unit: 'кг', cost_per_unit: 15.00, total_cost: 3.00, percentage: 13.2 },
          { id: 3, name: 'Яйца', quantity: 4, unit: 'бр', cost_per_unit: 0.40, total_cost: 1.60, percentage: 7.0 },
          { id: 4, name: 'Захар', quantity: 0.15, unit: 'кг', cost_per_unit: 2.50, total_cost: 0.38, percentage: 1.7 },
          { id: 5, name: 'Кафе', quantity: 0.1, unit: 'л', cost_per_unit: 25.00, total_cost: 2.50, percentage: 11.0 },
          { id: 6, name: 'Какао', quantity: 0.02, unit: 'кг', cost_per_unit: 18.00, total_cost: 0.36, percentage: 1.6 }
        ],
        last_updated: '2024-12-26',
        status: 'profitable'
      },
      {
        id: 5,
        name: 'Шопска салата',
        category: 'Салати',
        selling_price: 10.00,
        total_cost: 2.40,
        food_cost_percentage: 24.0,
        target_cost_percentage: 28,
        gross_profit: 7.60,
        profit_margin: 76.0,
        portions_per_batch: 1,
        cost_per_portion: 2.40,
        ingredients: [
          { id: 1, name: 'Домати', quantity: 0.2, unit: 'кг', cost_per_unit: 4.50, total_cost: 0.90, percentage: 37.5 },
          { id: 2, name: 'Краставици', quantity: 0.15, unit: 'кг', cost_per_unit: 3.00, total_cost: 0.45, percentage: 18.8 },
          { id: 3, name: 'Чушки', quantity: 0.1, unit: 'кг', cost_per_unit: 5.00, total_cost: 0.50, percentage: 20.8 },
          { id: 4, name: 'Сирене', quantity: 0.05, unit: 'кг', cost_per_unit: 11.00, total_cost: 0.55, percentage: 22.9 }
        ],
        last_updated: '2024-12-28',
        status: 'profitable'
      },
      {
        id: 6,
        name: 'Паста Карбонара',
        category: 'Основни',
        selling_price: 16.00,
        total_cost: 5.80,
        food_cost_percentage: 36.3,
        target_cost_percentage: 32,
        gross_profit: 10.20,
        profit_margin: 63.7,
        portions_per_batch: 1,
        cost_per_portion: 5.80,
        ingredients: [
          { id: 1, name: 'Спагети', quantity: 0.15, unit: 'кг', cost_per_unit: 6.00, total_cost: 0.90, percentage: 15.5 },
          { id: 2, name: 'Бекон', quantity: 0.08, unit: 'кг', cost_per_unit: 22.00, total_cost: 1.76, percentage: 30.3 },
          { id: 3, name: 'Пармезан', quantity: 0.05, unit: 'кг', cost_per_unit: 35.00, total_cost: 1.75, percentage: 30.2 },
          { id: 4, name: 'Яйца', quantity: 2, unit: 'бр', cost_per_unit: 0.40, total_cost: 0.80, percentage: 13.8 },
          { id: 5, name: 'Сметана', quantity: 0.05, unit: 'л', cost_per_unit: 11.80, total_cost: 0.59, percentage: 10.2 }
        ],
        last_updated: '2024-12-27',
        status: 'marginal'
      },
      {
        id: 7,
        name: 'Мохито',
        category: 'Коктейли',
        selling_price: 12.00,
        total_cost: 3.20,
        food_cost_percentage: 26.7,
        target_cost_percentage: 25,
        gross_profit: 8.80,
        profit_margin: 73.3,
        portions_per_batch: 1,
        cost_per_portion: 3.20,
        ingredients: [
          { id: 1, name: 'Бял ром', quantity: 0.05, unit: 'л', cost_per_unit: 32.00, total_cost: 1.60, percentage: 50.0 },
          { id: 2, name: 'Мента', quantity: 0.01, unit: 'кг', cost_per_unit: 25.00, total_cost: 0.25, percentage: 7.8 },
          { id: 3, name: 'Лайм', quantity: 0.5, unit: 'бр', cost_per_unit: 0.80, total_cost: 0.40, percentage: 12.5 },
          { id: 4, name: 'Захар', quantity: 0.02, unit: 'кг', cost_per_unit: 2.50, total_cost: 0.05, percentage: 1.6 },
          { id: 5, name: 'Сода', quantity: 0.1, unit: 'л', cost_per_unit: 2.00, total_cost: 0.20, percentage: 6.3 },
          { id: 6, name: 'Лед', quantity: 0.15, unit: 'кг', cost_per_unit: 4.67, total_cost: 0.70, percentage: 21.9 }
        ],
        last_updated: '2024-12-28',
        status: 'marginal'
      },
      {
        id: 8,
        name: 'Пица Маргарита',
        category: 'Пици',
        selling_price: 14.00,
        total_cost: 3.50,
        food_cost_percentage: 25.0,
        target_cost_percentage: 28,
        gross_profit: 10.50,
        profit_margin: 75.0,
        portions_per_batch: 1,
        cost_per_portion: 3.50,
        ingredients: [
          { id: 1, name: 'Тесто', quantity: 0.25, unit: 'кг', cost_per_unit: 4.00, total_cost: 1.00, percentage: 28.6 },
          { id: 2, name: 'Доматен сос', quantity: 0.08, unit: 'л', cost_per_unit: 6.00, total_cost: 0.48, percentage: 13.7 },
          { id: 3, name: 'Моцарела', quantity: 0.12, unit: 'кг', cost_per_unit: 15.00, total_cost: 1.80, percentage: 51.4 },
          { id: 4, name: 'Босилек', quantity: 0.005, unit: 'кг', cost_per_unit: 30.00, total_cost: 0.15, percentage: 4.3 },
          { id: 5, name: 'Зехтин', quantity: 0.01, unit: 'л', cost_per_unit: 7.00, total_cost: 0.07, percentage: 2.0 }
        ],
        last_updated: '2024-12-28',
        status: 'profitable'
      }
    ];

    const demoStats: RecipeStats = {
      total_recipes: 156,
      avg_food_cost: 29.8,
      target_food_cost: 30,
      recipes_above_target: 23,
      total_potential_savings: 4250,
      most_profitable_category: 'Салати'
    };

    const demoTrends: CostTrend[] = [
      { month: 'Юли', actual_cost: 31.2, target_cost: 30 },
      { month: 'Авг', actual_cost: 30.8, target_cost: 30 },
      { month: 'Сеп', actual_cost: 30.5, target_cost: 30 },
      { month: 'Окт', actual_cost: 30.1, target_cost: 30 },
      { month: 'Ное', actual_cost: 29.9, target_cost: 30 },
      { month: 'Дек', actual_cost: 29.8, target_cost: 30 }
    ];

    setRecipes(demoRecipes);
    setStats(demoStats);
    setCostTrends(demoTrends);
  };

  const categories = ['all', ...new Set(recipes.map(r => r.category))];

  const filteredRecipes = recipes.filter(recipe => {
    if (selectedCategory !== 'all' && recipe.category !== selectedCategory) return false;
    if (showUnprofitableOnly && recipe.status === 'profitable') return false;
    if (searchTerm && !recipe.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'profitable': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'marginal': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'unprofitable': return 'bg-red-500/20 text-red-400 border-red-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'profitable': return 'Печеливш';
      case 'marginal': return 'Маргинален';
      case 'unprofitable': return 'Непечеливш';
      default: return status;
    }
  };

  const getCostColor = (actual: number, target: number) => {
    const diff = actual - target;
    if (diff <= -5) return 'text-green-400';
    if (diff <= 0) return 'text-blue-400';
    if (diff <= 5) return 'text-yellow-400';
    return 'text-red-400';
  };

  const recalculateCosts = () => {
    toast.success('Преизчисляване на разходите базирано на актуални цени на съставките...');
    fetchRecipeData();
  };

  const exportReport = async () => {
    try {
      // CSV export returns text, not JSON - use raw fetch with cookie auth headers
      const response = await fetch(`${API_URL}/recipes/export`, { credentials: 'include', headers: getAuthHeaders() });

      if (response.ok) {
        const csvText = await response.text();
        const blob = new Blob([csvText], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `recipes_export_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Рецептите са експортирани успешно');
      } else {
        toast.error('Грешка при експортиране');
      }
    } catch {
      toast.error('Грешка при експортиране');
    }
  };

  const handleImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setImportData(event.target?.result as string);
    };
    reader.readAsText(file);
  };

  const handleImportRecipes = async () => {
    try {
      if (!importData.trim()) {
        toast.error('Няма данни за импортиране');
        return;
      }

      const blob = new Blob([importData], { type: 'text/csv' });
      const file = new File([blob], 'recipes_import.csv', { type: 'text/csv' });
      const formData = new FormData();
      formData.append('file', file);

      const result = await api.post<any>('/recipes/import', formData);
      setImportResult(result);
      fetchRecipeData();
      toast.success(`Импортирани: ${result.recipes_created} рецепти, ${result.lines_added} реда`);
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || 'Грешка при импортиране');
    }
  };

  return (
    <AdminLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Управление на разходите по рецепти</h1>
            <p className="text-gray-400 mt-1">Анализ на себестойност и оптимизация на печалбата</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={recalculateCosts}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
             aria-label="Close">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Преизчисли разходите
            </button>
            <button
              onClick={() => setShowImportModal(true)}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Импорт CSV
            </button>
            <button
              onClick={exportReport}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Експорт CSV
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Общо рецепти</p>
                  <p className="text-2xl font-bold text-white">{stats.total_recipes}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Среден food cost</p>
                  <p className="text-2xl font-bold text-white">{stats.avg_food_cost}%</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Целеви food cost</p>
                  <p className="text-2xl font-bold text-white">{stats.target_food_cost}%</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Над целта</p>
                  <p className="text-2xl font-bold text-white">{stats.recipes_above_target}</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Потенц. спестяване</p>
                  <p className="text-2xl font-bold text-white">{stats.total_potential_savings.toLocaleString()} лв</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-500/20 rounded-lg">
                  <svg className="w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-400">Най-печеливша</p>
                  <p className="text-lg font-bold text-white">{stats.most_profitable_category}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Cost Trend Chart */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Тренд на food cost (последни 6 месеца)</h3>
          <div className="h-48 relative">
            <svg className="w-full h-full" viewBox="0 0 500 150" preserveAspectRatio="none">
              {/* Grid lines */}
              {[20, 25, 30, 35, 40].map((val, i) => (
                <g key={i}>
                  <line x1="40" y1={150 - (val - 15) * 4} x2="500" y2={150 - (val - 15) * 4} stroke="#374151" strokeWidth="1" />
                  <text x="30" y={155 - (val - 15) * 4} fill="#9ca3af" fontSize="10" textAnchor="end">{val}%</text>
                </g>
              ))}

              {/* Target line */}
              <line x1="40" y1={150 - (30 - 15) * 4} x2="500" y2={150 - (30 - 15) * 4} stroke="#ef4444" strokeWidth="2" strokeDasharray="5,5" />

              {/* Actual cost line */}
              <polyline
                fill="none"
                stroke="#3b82f6"
                strokeWidth="3"
                points={costTrends.map((d, i) => `${40 + i * 92},${150 - (d.actual_cost - 15) * 4}`).join(' ')}
              />

              {/* Data points */}
              {costTrends.map((d, i) => (
                <circle key={i} cx={40 + i * 92} cy={150 - (d.actual_cost - 15) * 4} r="5" fill="#3b82f6" />
              ))}
            </svg>

            {/* X-axis labels */}
            <div className="absolute bottom-0 left-10 right-0 flex justify-between px-4 text-xs text-gray-400">
              {costTrends.map((d, i) => (
                <span key={i}>{d.month}</span>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-1 bg-blue-500 rounded" />
              <span className="text-sm text-gray-400">Реален food cost</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-red-500 border-dashed" />
              <span className="text-sm text-gray-400">Целеви food cost (30%)</span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="relative">
            <svg className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Търси рецепта..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 w-64"
            />
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          >
            <option value="all">Всички категории</option>
            {categories.filter(c => c !== 'all').map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={showUnprofitableOnly}
              onChange={(e) => setShowUnprofitableOnly(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500"
            />
            Само проблемни рецепти
          </label>
        </div>

        {/* Recipes Table */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-900/50">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Рецепта</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Категория</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Продажна цена</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Себестойност</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Food Cost %</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Печалба</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Маржин</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-400">Статус</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        Зареждане...
                      </div>
                    </td>
                  </tr>
                ) : filteredRecipes.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                      Няма намерени рецепти
                    </td>
                  </tr>
                ) : (
                  filteredRecipes.map((recipe) => (
                    <tr
                      key={recipe.id}
                      onClick={() => setSelectedRecipe(recipe)}
                      className="border-t border-gray-700/50 hover:bg-gray-700/30 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <span className="text-white font-medium">{recipe.name}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-gray-400">{recipe.category}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-white">{(recipe.selling_price || 0).toFixed(2)} лв</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-gray-300">{(recipe.total_cost || 0).toFixed(2)} лв</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-medium ${getCostColor(recipe.food_cost_percentage, recipe.target_cost_percentage)}`}>
                          {(recipe.food_cost_percentage || 0).toFixed(1)}%
                        </span>
                        <span className="text-xs text-gray-500 ml-1">/ {recipe.target_cost_percentage}%</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-green-400">{(recipe.gross_profit || 0).toFixed(2)} лв</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-white">{(recipe.profit_margin || 0).toFixed(1)}%</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs border ${getStatusColor(recipe.status)}`}>
                          {getStatusLabel(recipe.status)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recipe Detail Modal */}
        {selectedRecipe && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-bold text-white">{selectedRecipe.name}</h2>
                  <p className="text-gray-400">{selectedRecipe.category}</p>
                </div>
                <button
                  onClick={() => setSelectedRecipe(null)}
                  className="p-2 hover:bg-gray-700 rounded-lg text-gray-400"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Продажна цена</p>
                    <p className="text-2xl font-bold text-white">{(selectedRecipe.selling_price || 0).toFixed(2)} лв</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Себестойност</p>
                    <p className="text-2xl font-bold text-white">{(selectedRecipe.total_cost || 0).toFixed(2)} лв</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Брутна печалба</p>
                    <p className="text-2xl font-bold text-green-400">{(selectedRecipe.gross_profit || 0).toFixed(2)} лв</p>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <p className="text-sm text-gray-400">Food Cost</p>
                    <p className={`text-2xl font-bold ${getCostColor(selectedRecipe.food_cost_percentage, selectedRecipe.target_cost_percentage)}`}>
                      {(selectedRecipe.food_cost_percentage || 0).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Ingredients Table */}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">Съставки</h3>
                  <div className="bg-gray-700/30 rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-gray-700/50">
                          <th className="px-4 py-2 text-left text-sm font-medium text-gray-400">Съставка</th>
                          <th className="px-4 py-2 text-right text-sm font-medium text-gray-400">Количество</th>
                          <th className="px-4 py-2 text-right text-sm font-medium text-gray-400">Цена/ед.</th>
                          <th className="px-4 py-2 text-right text-sm font-medium text-gray-400">Стойност</th>
                          <th className="px-4 py-2 text-right text-sm font-medium text-gray-400">% от разхода</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedRecipe.ingredients.map((ing) => (
                          <tr key={ing.id} className="border-t border-gray-600/50">
                            <td className="px-4 py-2 text-white">{ing.name}</td>
                            <td className="px-4 py-2 text-right text-gray-300">{ing.quantity} {ing.unit}</td>
                            <td className="px-4 py-2 text-right text-gray-300">{(ing.cost_per_unit || 0).toFixed(2)} лв</td>
                            <td className="px-4 py-2 text-right text-white">{(ing.total_cost || 0).toFixed(2)} лв</td>
                            <td className="px-4 py-2 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <div className="w-16 h-2 bg-gray-600 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-blue-500 rounded-full"
                                    style={{ width: `${ing.percentage}%` }}
                                  />
                                </div>
                                <span className="text-gray-400 text-sm w-12">{(ing.percentage || 0).toFixed(1)}%</span>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t border-gray-500 bg-gray-700/30">
                          <td colSpan={3} className="px-4 py-2 text-white font-medium">Общо</td>
                          <td className="px-4 py-2 text-right text-white font-bold">{(selectedRecipe.total_cost || 0).toFixed(2)} лв</td>
                          <td className="px-4 py-2 text-right text-gray-400">100%</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>

                {/* Cost Breakdown Visual */}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">Разпределение на разходите</h3>
                  <div className="h-8 bg-gray-700 rounded-full overflow-hidden flex">
                    {selectedRecipe.ingredients.map((ing, index) => {
                      const colors = ['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500'];
                      return (
                        <div
                          key={ing.id}
                          className={`${colors[index % colors.length]} h-full transition-all relative group`}
                          style={{ width: `${ing.percentage}%` }}
                          title={`${ing.name}: ${(ing.percentage || 0).toFixed(1)}%`}
                        >
                          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 whitespace-nowrap z-10">
                            {ing.name}: {(ing.percentage || 0).toFixed(1)}%
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="flex flex-wrap gap-3 mt-3">
                    {selectedRecipe.ingredients.map((ing, index) => {
                      const colors = ['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500'];
                      return (
                        <div key={ing.id} className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded-full ${colors[index % colors.length]}`} />
                          <span className="text-sm text-gray-400">{ing.name}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Recommendations */}
                {selectedRecipe.food_cost_percentage > selectedRecipe.target_cost_percentage && (
                  <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                    <h4 className="text-yellow-400 font-medium mb-2">Препоръки за оптимизация</h4>
                    <ul className="list-disc list-inside text-gray-300 space-y-1 text-sm">
                      <li>Разгледайте възможност за намаляване на количеството на най-скъпите съставки</li>
                      <li>Потърсете алтернативни доставчици с по-конкурентни цени</li>
                      <li>Обмислете увеличение на продажната цена с {(((selectedRecipe.food_cost_percentage - selectedRecipe.target_cost_percentage) / 100 * selectedRecipe.selling_price) || 0).toFixed(2)} лв</li>
                      <li>Проверете за сезонни алтернативи на съставките</li>
                    </ul>
                  </div>
                )}

                <div className="flex gap-3">
                  <button className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
                    Редактирай рецептата
                  </button>
                  <button className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg">
                    Симулирай промени
                  </button>
                  <button className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg">
                    Виж история
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        {/* Import Modal */}
        {showImportModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-2xl mx-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">Импорт на рецепти от CSV</h2>
                <button
                  onClick={() => { setShowImportModal(false); setImportData(''); setImportResult(null); }}
                  className="p-2 hover:bg-gray-700 rounded-lg text-gray-400"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-4">
                <p className="text-blue-400 text-sm mb-2 font-medium">CSV формат (първи ред = заглавия):</p>
                <code className="text-xs text-blue-300 block bg-blue-500/10 p-3 rounded-lg font-mono">
                  recipe_name,pos_item_id,pos_item_name,product_barcode,qty,unit<br/>
                  Chicken Soup,POS001,Soup,5012345678901,0.5,kg<br/>
                  Chicken Soup,POS001,Soup,5098765432101,1,l
                </code>
              </div>

              <div className="mb-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleImportFile}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full py-4 border-2 border-dashed border-gray-600 rounded-xl text-gray-400 hover:border-blue-500 hover:text-blue-400 transition-colors"
                >
                  Изберете CSV файл
                </button>
              </div>

              <textarea
                value={importData}
                onChange={(e) => setImportData(e.target.value)}
                placeholder="Или поставете CSV данни тук..."
                className="w-full h-32 px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl mb-4 font-mono text-sm text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />

              {importResult && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 mb-4">
                  <p className="text-green-400 font-medium">
                    Създадени рецепти: {importResult.recipes_created} | Добавени редове: {importResult.lines_added}
                  </p>
                  {importResult.errors?.length > 0 && (
                    <p className="text-red-400 text-sm mt-2">
                      Грешки: {importResult.errors.join(', ')}
                    </p>
                  )}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => { setShowImportModal(false); setImportData(''); setImportResult(null); }}
                  className="flex-1 py-3 bg-gray-700 text-gray-300 rounded-xl hover:bg-gray-600 transition-colors"
                >
                  Затвори
                </button>
                <button
                  onClick={handleImportRecipes}
                  disabled={!importData}
                  className="flex-1 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  Импортирай
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}

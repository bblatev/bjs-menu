'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

// ============ TYPES ============

interface Ingredient {
  id: number;
  name: string;
  amount: string;
  unit: string;
  cost: number;
}

interface Recipe {
  id: number;
  name: string;
  category: string;
  description: string;
  image_emoji: string;
  ingredients: Ingredient[];
  garnish: string;
  glass_type: string;
  preparation: string[];
  total_cost: number;
  sell_price: number;
  pour_cost_percentage: number;
  profit_margin: number;
  prep_time_seconds: number;
  difficulty: 'easy' | 'medium' | 'hard';
  is_signature: boolean;
  is_seasonal: boolean;
  allergens: string[];
  sold_today: number;
  avg_rating: number;
  spirit_base: string;
}

interface RecipeListResponse {
  recipes: Recipe[];
  total: number;
  spirits: string[];
}

// ============ CONSTANTS ============

const SPIRIT_FILTERS = [
  { value: 'all', label: 'All Spirits' },
  { value: 'vodka', label: 'Vodka' },
  { value: 'gin', label: 'Gin' },
  { value: 'rum', label: 'Rum' },
  { value: 'tequila', label: 'Tequila' },
  { value: 'whiskey', label: 'Whiskey' },
  { value: 'bourbon', label: 'Bourbon' },
  { value: 'brandy', label: 'Brandy' },
  { value: 'non-alcoholic', label: 'Non-Alcoholic' },
];

// ============ COMPONENT ============

export default function BarRecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [_spirits, setSpirits] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [spiritFilter, setSpiritFilter] = useState('all');
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [_detailLoading, setDetailLoading] = useState(false);

  const fetchRecipes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.set('search', searchQuery);
      if (spiritFilter !== 'all') params.set('spirit', spiritFilter);
      const result = await api.get<RecipeListResponse>(`/bar/recipes?${params.toString()}`);
      setRecipes(result.recipes || (Array.isArray(result) ? result as unknown as Recipe[] : []));
      if (result.spirits) setSpirits(result.spirits);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recipes');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, spiritFilter]);

  useEffect(() => {
    fetchRecipes();
  }, [fetchRecipes]);

  const openRecipeDetail = async (recipeId: number) => {
    setDetailLoading(true);
    try {
      const detail = await api.get<Recipe>(`/bar/recipes/${recipeId}`);
      setSelectedRecipe(detail);
    } catch {
      // Fallback to list data
      const found = recipes.find((r) => r.id === recipeId);
      if (found) setSelectedRecipe(found);
    } finally {
      setDetailLoading(false);
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-green-100 text-green-700';
      case 'medium': return 'bg-yellow-100 text-yellow-700';
      case 'hard': return 'bg-red-100 text-red-700';
      default: return 'bg-surface-100 text-surface-700';
    }
  };

  const getCostColor = (pct: number) => {
    if (pct <= 18) return 'text-green-600';
    if (pct <= 25) return 'text-yellow-600';
    return 'text-red-600';
  };

  const filteredRecipes = recipes.filter((recipe) => {
    const matchesSearch =
      !searchQuery ||
      recipe.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      recipe.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSpirit =
      spiritFilter === 'all' || recipe.spirit_base?.toLowerCase() === spiritFilter.toLowerCase();
    return matchesSearch && matchesSpirit;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading recipes...</p>
        </div>
      </div>
    );
  }

  if (error && recipes.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🍸</div>
          <h2 className="text-2xl font-bold text-surface-900 mb-2">Recipes Unavailable</h2>
          <p className="text-surface-600 mb-4">{error}</p>
          <button
            onClick={fetchRecipes}
            className="px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/bar" className="p-2 hover:bg-surface-100 rounded-lg transition-colors">
            <svg className="w-5 h-5 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Cocktail Recipe Library</h1>
            <p className="text-surface-500 mt-1">
              {filteredRecipes.length} recipe{filteredRecipes.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <input
          type="text"
          placeholder="Search recipes..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 w-64"
        />
        <div className="flex gap-2 flex-wrap">
          {SPIRIT_FILTERS.map((spirit) => (
            <button
              key={spirit.value}
              onClick={() => setSpiritFilter(spirit.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                spiritFilter === spirit.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
              }`}
            >
              {spirit.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">{error}</div>
      )}

      {/* Recipe Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredRecipes.map((recipe) => (
          <div
            key={recipe.id}
            onClick={() => openRecipeDetail(recipe.id)}
            className="bg-white rounded-xl border border-surface-200 shadow-sm hover:shadow-md transition-all cursor-pointer overflow-hidden group"
          >
            <div className={`h-32 flex items-center justify-center text-6xl relative ${
              recipe.is_signature ? 'bg-gradient-to-br from-amber-100 to-amber-200' :
              'bg-gradient-to-br from-purple-100 to-indigo-200'
            }`}>
              {recipe.image_emoji}
              {recipe.is_signature && (
                <span className="absolute top-2 right-2 px-2 py-0.5 bg-amber-500 text-white text-xs font-medium rounded-full">
                  Signature
                </span>
              )}
            </div>
            <div className="p-4">
              <div className="flex items-start justify-between mb-1">
                <h3 className="font-semibold text-surface-900 group-hover:text-primary-600 transition-colors">
                  {recipe.name}
                </h3>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getDifficultyColor(recipe.difficulty)}`}>
                  {recipe.difficulty}
                </span>
              </div>
              <p className="text-sm text-surface-500 mb-1">{recipe.glass_type}</p>
              <p className="text-sm text-surface-600 line-clamp-2 mb-3">{recipe.description}</p>

              <div className="grid grid-cols-3 gap-2 text-sm mb-3">
                <div>
                  <p className="text-surface-400 text-xs">Cost</p>
                  <p className="font-medium text-surface-900">${recipe.total_cost.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-surface-400 text-xs">Price</p>
                  <p className="font-medium text-green-600">${recipe.sell_price.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-surface-400 text-xs">Pour %</p>
                  <p className={`font-medium ${getCostColor(recipe.pour_cost_percentage)}`}>
                    {recipe.pour_cost_percentage.toFixed(1)}%
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-surface-100 text-sm">
                <div className="flex items-center gap-1 text-yellow-500">
                  <span>★</span>
                  <span className="text-surface-700 font-medium">{recipe.avg_rating.toFixed(1)}</span>
                </div>
                <span className="text-surface-500">{recipe.sold_today} sold today</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredRecipes.length === 0 && (
        <div className="text-center py-12 text-surface-500">
          <p className="text-lg">No recipes match your search</p>
          <p className="text-sm mt-1">Try a different filter or search term</p>
        </div>
      )}

      {/* Recipe Detail Modal */}
      {selectedRecipe && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className={`h-40 flex items-center justify-center text-8xl relative ${
              selectedRecipe.is_signature ? 'bg-gradient-to-br from-amber-100 to-amber-200' :
              'bg-gradient-to-br from-purple-100 to-indigo-200'
            }`}>
              {selectedRecipe.image_emoji}
              <button
                onClick={() => setSelectedRecipe(null)}
                className="absolute top-4 right-4 w-8 h-8 bg-white/80 rounded-full flex items-center justify-center hover:bg-white"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6">
              <div className="flex items-start justify-between mb-2">
                <h2 className="text-2xl font-bold text-surface-900">{selectedRecipe.name}</h2>
                <div className="flex gap-2">
                  {selectedRecipe.is_signature && (
                    <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-sm font-medium">Signature</span>
                  )}
                  {selectedRecipe.is_seasonal && (
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">Seasonal</span>
                  )}
                </div>
              </div>
              <p className="text-surface-600">{selectedRecipe.description}</p>

              {/* Stats */}
              <div className="grid grid-cols-4 gap-4 my-6">
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-xl font-bold text-surface-900">${selectedRecipe.total_cost.toFixed(2)}</p>
                  <p className="text-xs text-surface-500">Cost</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-xl font-bold text-green-600">${selectedRecipe.sell_price.toFixed(2)}</p>
                  <p className="text-xs text-surface-500">Price</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className={`text-xl font-bold ${getCostColor(selectedRecipe.pour_cost_percentage)}`}>
                    {selectedRecipe.pour_cost_percentage.toFixed(1)}%
                  </p>
                  <p className="text-xs text-surface-500">Pour Cost</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-xl font-bold text-primary-600">{selectedRecipe.profit_margin.toFixed(1)}%</p>
                  <p className="text-xs text-surface-500">Margin</p>
                </div>
              </div>

              {/* Ingredients */}
              <h3 className="font-semibold text-surface-900 mb-3">Ingredients</h3>
              <div className="bg-surface-50 rounded-lg overflow-hidden mb-6">
                <table className="w-full text-sm">
                  <thead className="bg-surface-100">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-surface-500 uppercase">Ingredient</th>
                      <th className="px-4 py-2 text-center text-xs font-medium text-surface-500 uppercase">Amount</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-surface-500 uppercase">Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-200">
                    {selectedRecipe.ingredients.map((ing) => (
                      <tr key={ing.id}>
                        <td className="px-4 py-2 font-medium text-surface-900">{ing.name}</td>
                        <td className="px-4 py-2 text-center text-surface-700">{ing.amount} {ing.unit}</td>
                        <td className="px-4 py-2 text-right text-surface-700">${ing.cost.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-surface-100">
                    <tr>
                      <td className="px-4 py-2 font-semibold">Total</td>
                      <td></td>
                      <td className="px-4 py-2 text-right font-semibold">${selectedRecipe.total_cost.toFixed(2)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* Preparation Steps */}
              <h3 className="font-semibold text-surface-900 mb-3">Preparation</h3>
              <ol className="space-y-2 mb-6">
                {selectedRecipe.preparation.map((step, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-surface-700">{step}</span>
                  </li>
                ))}
              </ol>

              {/* Details */}
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-xs text-surface-500 mb-0.5">Glass</p>
                  <p className="font-medium text-surface-900 text-sm">{selectedRecipe.glass_type}</p>
                </div>
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-xs text-surface-500 mb-0.5">Garnish</p>
                  <p className="font-medium text-surface-900 text-sm">{selectedRecipe.garnish}</p>
                </div>
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-xs text-surface-500 mb-0.5">Prep Time</p>
                  <p className="font-medium text-surface-900 text-sm">{selectedRecipe.prep_time_seconds}s</p>
                </div>
              </div>

              {selectedRecipe.allergens.length > 0 && (
                <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <p className="text-sm text-yellow-800">
                    <span className="font-medium">Allergens:</span> {selectedRecipe.allergens.join(', ')}
                  </p>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-surface-200 flex items-center justify-between">
              <div className="flex items-center gap-4 text-sm text-surface-500">
                <span className="flex items-center gap-1">
                  <span className="text-yellow-500">★</span> {selectedRecipe.avg_rating.toFixed(1)}
                </span>
                <span>{selectedRecipe.sold_today} sold today</span>
              </div>
              <button
                onClick={() => setSelectedRecipe(null)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

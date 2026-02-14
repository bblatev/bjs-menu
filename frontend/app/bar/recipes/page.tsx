'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_URL, getAuthHeaders } from '@/lib/api';

import { toast } from '@/lib/toast';
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
}

const CATEGORIES = [
  { value: 'classic', label: 'Classic Cocktails', icon: '🍸' },
  { value: 'tropical', label: 'Tropical', icon: '🏝️' },
  { value: 'shots', label: 'Shots', icon: '🥃' },
  { value: 'signature', label: 'Signature', icon: '⭐' },
  { value: 'mocktail', label: 'Mocktails', icon: '🍹' },
  { value: 'wine', label: 'Wine Based', icon: '🍷' },
  { value: 'beer', label: 'Beer Cocktails', icon: '🍺' },
];

const GLASS_TYPES = ['Martini', 'Highball', 'Old Fashioned', 'Collins', 'Coupe', 'Hurricane', 'Shot', 'Wine', 'Beer Mug', 'Copper Mug'];

export default function BarRecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [sortBy, setSortBy] = useState<'name' | 'profit' | 'sales' | 'rating'>('sales');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New recipe form state
  const [newRecipe, setNewRecipe] = useState({
    name: '',
    category: 'classic',
    description: '',
    image_emoji: '🍸',
    glass_type: 'Highball',
    garnish: '',
    sell_price: 10,
    difficulty: 'easy' as 'easy' | 'medium' | 'hard',
    is_signature: false,
    is_seasonal: false,
    prep_time_seconds: 60,
    ingredients: [{ name: '', amount: '', unit: 'ml', cost: 0 }],
    preparation: [''],
  });

  // Default recipes for fallback
  const defaultRecipes: Recipe[] = [
    {
      id: 1, name: 'Mojito', category: 'classic', description: 'Refreshing Cuban cocktail with rum, lime, mint and soda',
      image_emoji: '🍃', ingredients: [
        { id: 1, name: 'White Rum', amount: '60', unit: 'ml', cost: 1.20 },
        { id: 2, name: 'Fresh Lime Juice', amount: '30', unit: 'ml', cost: 0.25 },
        { id: 3, name: 'Simple Syrup', amount: '20', unit: 'ml', cost: 0.10 },
        { id: 4, name: 'Fresh Mint', amount: '8', unit: 'leaves', cost: 0.30 },
        { id: 5, name: 'Soda Water', amount: '60', unit: 'ml', cost: 0.15 },
      ],
      garnish: 'Mint sprig, lime wheel', glass_type: 'Highball',
      preparation: ['Muddle mint with lime juice and syrup', 'Add rum and ice', 'Top with soda', 'Stir gently'],
      total_cost: 2.00, sell_price: 10.00, pour_cost_percentage: 20.0, profit_margin: 80.0,
      prep_time_seconds: 90, difficulty: 'easy', is_signature: false, is_seasonal: true,
      allergens: [], sold_today: 42, avg_rating: 4.7
    },
    {
      id: 2, name: 'Margarita', category: 'classic', description: 'Mexican classic with tequila, lime and triple sec',
      image_emoji: '🍋', ingredients: [
        { id: 1, name: 'Tequila', amount: '45', unit: 'ml', cost: 1.50 },
        { id: 2, name: 'Triple Sec', amount: '30', unit: 'ml', cost: 0.40 },
        { id: 3, name: 'Fresh Lime Juice', amount: '30', unit: 'ml', cost: 0.25 },
      ],
      garnish: 'Salt rim, lime wedge', glass_type: 'Coupe',
      preparation: ['Rim glass with salt', 'Shake all ingredients with ice', 'Strain into glass'],
      total_cost: 2.15, sell_price: 10.00, pour_cost_percentage: 21.5, profit_margin: 78.5,
      prep_time_seconds: 60, difficulty: 'easy', is_signature: false, is_seasonal: false,
      allergens: [], sold_today: 38, avg_rating: 4.6
    },
    {
      id: 3, name: 'Old Fashioned', category: 'classic', description: 'Timeless whiskey cocktail with bitters and sugar',
      image_emoji: '🥃', ingredients: [
        { id: 1, name: 'Bourbon Whiskey', amount: '60', unit: 'ml', cost: 2.00 },
        { id: 2, name: 'Angostura Bitters', amount: '3', unit: 'dashes', cost: 0.15 },
        { id: 3, name: 'Sugar Cube', amount: '1', unit: 'piece', cost: 0.05 },
        { id: 4, name: 'Orange Peel', amount: '1', unit: 'piece', cost: 0.10 },
      ],
      garnish: 'Orange peel, luxardo cherry', glass_type: 'Old Fashioned',
      preparation: ['Muddle sugar with bitters', 'Add whiskey and ice', 'Stir well', 'Express orange peel'],
      total_cost: 2.30, sell_price: 12.00, pour_cost_percentage: 19.2, profit_margin: 80.8,
      prep_time_seconds: 60, difficulty: 'easy', is_signature: false, is_seasonal: false,
      allergens: [], sold_today: 25, avg_rating: 4.8
    },
  ];

  useEffect(() => {
    const fetchRecipes = async () => {
      setLoading(true);
      const headers = getAuthHeaders();

      try {
        const response = await fetch(
          `${API_URL}/bar/recipes?category=${selectedCategory !== 'all' ? selectedCategory : ''}&search=${searchQuery}&sort_by=${sortBy}`,
          { headers }
        );

        if (response.ok) {
          const data = await response.json();
          if (Array.isArray(data) && data.length > 0) {
            setRecipes(data);
          } else {
            setRecipes(defaultRecipes);
          }
        } else {
          setRecipes(defaultRecipes);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to fetch recipes:', err);
        setError('Failed to load recipes. Showing default values.');
        setRecipes(defaultRecipes);
      } finally {
        setLoading(false);
      }
    };

    fetchRecipes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory, searchQuery, sortBy]);

  const handleAddRecipe = async () => {
    if (!newRecipe.name.trim()) {
      toast.success('Please enter a recipe name');
      return;
    }

    const totalCost = newRecipe.ingredients.reduce((sum, ing) => sum + (ing.cost || 0), 0);

    try {
      const response = await fetch(`${API_URL}/bar/recipes`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: newRecipe.name,
          category: newRecipe.category,
          description: newRecipe.description,
          image_emoji: newRecipe.image_emoji,
          glass_type: newRecipe.glass_type,
          garnish: newRecipe.garnish,
          sell_price: newRecipe.sell_price,
          difficulty: newRecipe.difficulty,
          is_signature: newRecipe.is_signature,
          is_seasonal: newRecipe.is_seasonal,
          prep_time_seconds: newRecipe.prep_time_seconds,
          ingredients: newRecipe.ingredients.filter(i => i.name.trim()),
          preparation: newRecipe.preparation.filter(s => s.trim()),
          total_cost: totalCost,
          pour_cost_percentage: newRecipe.sell_price > 0 ? (totalCost / newRecipe.sell_price) * 100 : 0,
        }),
      });

      if (response.ok) {
        setShowAddModal(false);
        setNewRecipe({
          name: '', category: 'classic', description: '', image_emoji: '🍸',
          glass_type: 'Highball', garnish: '', sell_price: 10, difficulty: 'easy',
          is_signature: false, is_seasonal: false, prep_time_seconds: 60,
          ingredients: [{ name: '', amount: '', unit: 'ml', cost: 0 }],
          preparation: [''],
        });
        // Refresh recipes
        const refreshResponse = await fetch(
          `${API_URL}/bar/recipes?category=${selectedCategory !== 'all' ? selectedCategory : ''}&search=${searchQuery}&sort_by=${sortBy}`,
          { headers: getAuthHeaders() }
        );
        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          if (Array.isArray(data) && data.length > 0) {
            setRecipes(data);
          }
        }
      } else {
        const err = await response.json();
        toast.error(err.detail || 'Failed to add recipe');
      }
    } catch (err) {
      toast.error('Error adding recipe');
    }
  };

  const addIngredient = () => {
    setNewRecipe(prev => ({
      ...prev,
      ingredients: [...prev.ingredients, { name: '', amount: '', unit: 'ml', cost: 0 }]
    }));
  };

  const removeIngredient = (index: number) => {
    setNewRecipe(prev => ({
      ...prev,
      ingredients: prev.ingredients.filter((_, i) => i !== index)
    }));
  };

  const updateIngredient = (index: number, field: string, value: string | number) => {
    setNewRecipe(prev => ({
      ...prev,
      ingredients: prev.ingredients.map((ing, i) => i === index ? { ...ing, [field]: value } : ing)
    }));
  };

  const addPreparationStep = () => {
    setNewRecipe(prev => ({
      ...prev,
      preparation: [...prev.preparation, '']
    }));
  };

  const updatePreparationStep = (index: number, value: string) => {
    setNewRecipe(prev => ({
      ...prev,
      preparation: prev.preparation.map((step, i) => i === index ? value : step)
    }));
  };

  const filteredRecipes = recipes
    .filter(recipe => selectedCategory === 'all' || recipe.category === selectedCategory)
    .filter(recipe =>
      recipe.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      recipe.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'name': return a.name.localeCompare(b.name);
        case 'profit': return b.profit_margin - a.profit_margin;
        case 'sales': return b.sold_today - a.sold_today;
        case 'rating': return b.avg_rating - a.avg_rating;
        default: return 0;
      }
    });

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-success-100 text-success-700';
      case 'medium': return 'bg-warning-100 text-warning-700';
      case 'hard': return 'bg-error-100 text-error-700';
      default: return 'bg-surface-100 text-surface-700';
    }
  };

  const totalRecipes = recipes.length;
  const avgPourCost = totalRecipes > 0 ? recipes.reduce((sum, r) => sum + r.pour_cost_percentage, 0) / totalRecipes : 0;
  const totalSoldToday = recipes.reduce((sum, r) => sum + r.sold_today, 0);
  const signatureCount = recipes.filter(r => r.is_signature).length;

  // Loading state
  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-surface-600">Loading recipes...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-4 bg-warning-50 border border-warning-200 rounded-lg text-warning-800">
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link
            href="/bar"
            className="p-2 hover:bg-surface-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-surface-900">Cocktail Recipes</h1>
            <p className="text-surface-600 mt-1">Recipes, costs & preparation guides</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 border border-surface-300 text-surface-700 rounded-lg hover:bg-surface-50 flex items-center gap-2" aria-label="Close">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Print Cards
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Recipe
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Total Recipes</p>
          <p className="text-2xl font-bold text-surface-900">{totalRecipes}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Avg Pour Cost</p>
          <p className="text-2xl font-bold text-primary-600">{avgPourCost.toFixed(1)}%</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Sold Today</p>
          <p className="text-2xl font-bold text-success-600">{totalSoldToday}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-surface-200 shadow-sm">
          <p className="text-sm text-surface-500">Signature Drinks</p>
          <p className="text-2xl font-bold text-warning-600">{signatureCount}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === 'all'
                ? 'bg-primary-600 text-white'
                : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
            }`}
          >
            All
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                selectedCategory === cat.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
              }`}
            >
              <span>{cat.icon}</span>
              {cat.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <input
          type="text"
          placeholder="Search recipes..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 w-64"
        />
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          className="px-4 py-2 border border-surface-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        >
          <option value="sales">Most Sold</option>
          <option value="rating">Highest Rated</option>
          <option value="profit">Best Margin</option>
          <option value="name">Name A-Z</option>
        </select>
      </div>

      {/* Recipe Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredRecipes.map((recipe) => (
          <div
            key={recipe.id}
            onClick={() => setSelectedRecipe(recipe)}
            className="bg-white rounded-xl border border-surface-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer overflow-hidden group"
          >
            <div className={`h-32 flex items-center justify-center text-6xl ${
              recipe.is_signature ? 'bg-gradient-to-br from-amber-100 to-amber-200' :
              recipe.category === 'tropical' ? 'bg-gradient-to-br from-cyan-100 to-teal-200' :
              recipe.category === 'mocktail' ? 'bg-gradient-to-br from-green-100 to-emerald-200' :
              'bg-gradient-to-br from-purple-100 to-indigo-200'
            }`}>
              {recipe.image_emoji}
              {recipe.is_signature && (
                <span className="absolute top-2 right-2 text-2xl">⭐</span>
              )}
            </div>
            <div className="p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold text-surface-900 group-hover:text-primary-600 transition-colors">
                    {recipe.name}
                  </h3>
                  <p className="text-sm text-surface-500">{recipe.glass_type}</p>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getDifficultyColor(recipe.difficulty)}`}>
                  {recipe.difficulty}
                </span>
              </div>

              <p className="text-sm text-surface-600 line-clamp-2 mb-3">{recipe.description}</p>

              <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                <div>
                  <p className="text-surface-500">Cost</p>
                  <p className="font-medium">${recipe.total_cost.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-surface-500">Sell</p>
                  <p className="font-medium text-success-600">${recipe.sell_price.toFixed(2)}</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-surface-100">
                <div className="flex items-center gap-1">
                  <span className="text-yellow-500">★</span>
                  <span className="text-sm font-medium">{recipe.avg_rating}</span>
                </div>
                <div className="text-sm text-surface-500">
                  {recipe.sold_today} sold today
                </div>
                <div className={`text-sm font-medium ${
                  recipe.pour_cost_percentage <= 20 ? 'text-success-600' :
                  recipe.pour_cost_percentage <= 25 ? 'text-primary-600' :
                  'text-warning-600'
                }`}>
                  {recipe.pour_cost_percentage}%
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recipe Detail Modal */}
      {selectedRecipe && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className={`h-40 flex items-center justify-center text-8xl relative ${
              selectedRecipe.is_signature ? 'bg-gradient-to-br from-amber-100 to-amber-200' :
              selectedRecipe.category === 'tropical' ? 'bg-gradient-to-br from-cyan-100 to-teal-200' :
              selectedRecipe.category === 'mocktail' ? 'bg-gradient-to-br from-green-100 to-emerald-200' :
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
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-surface-900">{selectedRecipe.name}</h2>
                  <p className="text-surface-600 mt-1">{selectedRecipe.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  {selectedRecipe.is_signature && (
                    <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-sm font-medium">
                      Signature
                    </span>
                  )}
                  {selectedRecipe.is_seasonal && (
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                      Seasonal
                    </span>
                  )}
                </div>
              </div>

              {/* Quick Stats */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-2xl font-bold text-surface-900">${selectedRecipe.total_cost.toFixed(2)}</p>
                  <p className="text-sm text-surface-500">Cost</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-2xl font-bold text-success-600">${selectedRecipe.sell_price.toFixed(2)}</p>
                  <p className="text-sm text-surface-500">Price</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className={`text-2xl font-bold ${
                    selectedRecipe.pour_cost_percentage <= 20 ? 'text-success-600' :
                    selectedRecipe.pour_cost_percentage <= 25 ? 'text-primary-600' :
                    'text-warning-600'
                  }`}>
                    {selectedRecipe.pour_cost_percentage}%
                  </p>
                  <p className="text-sm text-surface-500">Pour Cost</p>
                </div>
                <div className="text-center p-3 bg-surface-50 rounded-lg">
                  <p className="text-2xl font-bold text-primary-600">{selectedRecipe.profit_margin}%</p>
                  <p className="text-sm text-surface-500">Margin</p>
                </div>
              </div>

              {/* Ingredients */}
              <div className="mb-6">
                <h3 className="font-semibold text-surface-900 mb-3">Ingredients</h3>
                <div className="bg-surface-50 rounded-lg overflow-hidden">
                  <table className="w-full">
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
                        <td className="px-4 py-2 font-semibold text-surface-900">Total</td>
                        <td></td>
                        <td className="px-4 py-2 text-right font-semibold text-surface-900">
                          ${selectedRecipe.total_cost.toFixed(2)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Preparation */}
              <div className="mb-6">
                <h3 className="font-semibold text-surface-900 mb-3">Preparation</h3>
                <ol className="space-y-2">
                  {selectedRecipe.preparation.map((step, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <span className="w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0">
                        {index + 1}
                      </span>
                      <span className="text-surface-700">{step}</span>
                    </li>
                  ))}
                </ol>
              </div>

              {/* Details */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500 mb-1">Glass Type</p>
                  <p className="font-medium text-surface-900">{selectedRecipe.glass_type}</p>
                </div>
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500 mb-1">Garnish</p>
                  <p className="font-medium text-surface-900">{selectedRecipe.garnish}</p>
                </div>
                <div className="p-3 bg-surface-50 rounded-lg">
                  <p className="text-sm text-surface-500 mb-1">Prep Time</p>
                  <p className="font-medium text-surface-900">{selectedRecipe.prep_time_seconds}s</p>
                </div>
              </div>

              {selectedRecipe.allergens.length > 0 && (
                <div className="mt-4 p-3 bg-warning-50 rounded-lg border border-warning-200">
                  <p className="text-sm font-medium text-warning-800">
                    Allergens: {selectedRecipe.allergens.join(', ')}
                  </p>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-surface-200 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1">
                  <span className="text-yellow-500 text-xl">★</span>
                  <span className="font-semibold">{selectedRecipe.avg_rating}</span>
                </div>
                <span className="text-surface-500">{selectedRecipe.sold_today} sold today</span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedRecipe(null)}
                  className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
                >
                  Close
                </button>
                <button className="px-4 py-2 bg-primary-600 text-gray-900 rounded-lg hover:bg-primary-700">
                  Edit Recipe
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Recipe Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-surface-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-surface-900">Add New Cocktail Recipe</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-2 hover:bg-surface-100 rounded-lg"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Cocktail Name *</label>
                  <input
                    type="text"
                    value={newRecipe.name}
                    onChange={e => setNewRecipe(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    placeholder="e.g., Moscow Mule"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Category</label>
                  <select
                    value={newRecipe.category}
                    onChange={e => setNewRecipe(prev => ({ ...prev, category: e.target.value }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    {CATEGORIES.map(cat => (
                      <option key={cat.value} value={cat.value}>{cat.icon} {cat.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-surface-700 mb-1">Description</label>
                <textarea
                  value={newRecipe.description}
                  onChange={e => setNewRecipe(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-4 py-2 border border-surface-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  rows={2}
                  placeholder="Brief description of the cocktail..."
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Emoji</label>
                  <input
                    type="text"
                    value={newRecipe.image_emoji}
                    onChange={e => setNewRecipe(prev => ({ ...prev, image_emoji: e.target.value }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg text-2xl text-center"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Glass Type</label>
                  <select
                    value={newRecipe.glass_type}
                    onChange={e => setNewRecipe(prev => ({ ...prev, glass_type: e.target.value }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg"
                  >
                    {GLASS_TYPES.map(glass => (
                      <option key={glass} value={glass}>{glass}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Sell Price ($)</label>
                  <input
                    type="number"
                    value={newRecipe.sell_price}
                    onChange={e => setNewRecipe(prev => ({ ...prev, sell_price: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg"
                    step="0.5"
                    min="0"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Difficulty</label>
                  <select
                    value={newRecipe.difficulty}
                    onChange={e => setNewRecipe(prev => ({ ...prev, difficulty: e.target.value as 'easy' | 'medium' | 'hard' }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Prep Time (sec)</label>
                  <input
                    type="number"
                    value={newRecipe.prep_time_seconds}
                    onChange={e => setNewRecipe(prev => ({ ...prev, prep_time_seconds: parseInt(e.target.value) || 60 }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg"
                    min="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-surface-700 mb-1">Garnish</label>
                  <input
                    type="text"
                    value={newRecipe.garnish}
                    onChange={e => setNewRecipe(prev => ({ ...prev, garnish: e.target.value }))}
                    className="w-full px-4 py-2 border border-surface-300 rounded-lg"
                    placeholder="e.g., Lime wedge"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newRecipe.is_signature}
                    onChange={e => setNewRecipe(prev => ({ ...prev, is_signature: e.target.checked }))}
                    className="w-4 h-4 rounded text-primary-600"
                  />
                  <span className="text-sm">Signature Cocktail</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newRecipe.is_seasonal}
                    onChange={e => setNewRecipe(prev => ({ ...prev, is_seasonal: e.target.checked }))}
                    className="w-4 h-4 rounded text-primary-600"
                  />
                  <span className="text-sm">Seasonal</span>
                </label>
              </div>

              {/* Ingredients */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-surface-700">Ingredients</label>
                  <button
                    type="button"
                    onClick={addIngredient}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    + Add Ingredient
                  </button>
                </div>
                <div className="space-y-2">
                  {newRecipe.ingredients.map((ing, index) => (
                    <div key={index} className="flex gap-2 items-center">
                      <input
                        type="text"
                        value={ing.name}
                        onChange={e => updateIngredient(index, 'name', e.target.value)}
                        className="flex-1 px-3 py-2 border border-surface-300 rounded-lg text-sm"
                        placeholder="Ingredient name"
                      />
                      <input
                        type="text"
                        value={ing.amount}
                        onChange={e => updateIngredient(index, 'amount', e.target.value)}
                        className="w-20 px-3 py-2 border border-surface-300 rounded-lg text-sm"
                        placeholder="Amt"
                      />
                      <select
                        value={ing.unit}
                        onChange={e => updateIngredient(index, 'unit', e.target.value)}
                        className="w-20 px-2 py-2 border border-surface-300 rounded-lg text-sm"
                      >
                        <option value="ml">ml</option>
                        <option value="oz">oz</option>
                        <option value="dash">dash</option>
                        <option value="piece">pc</option>
                        <option value="leaves">leaves</option>
                      </select>
                      <input
                        type="number"
                        value={ing.cost}
                        onChange={e => updateIngredient(index, 'cost', parseFloat(e.target.value) || 0)}
                        className="w-20 px-3 py-2 border border-surface-300 rounded-lg text-sm"
                        placeholder="Cost"
                        step="0.1"
                        min="0"
                      />
                      {newRecipe.ingredients.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeIngredient(index)}
                          className="p-2 text-error-500 hover:bg-error-50 rounded"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Preparation Steps */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-surface-700">Preparation Steps</label>
                  <button
                    type="button"
                    onClick={addPreparationStep}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    + Add Step
                  </button>
                </div>
                <div className="space-y-2">
                  {newRecipe.preparation.map((step, index) => (
                    <div key={index} className="flex gap-2 items-center">
                      <span className="w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0">
                        {index + 1}
                      </span>
                      <input
                        type="text"
                        value={step}
                        onChange={e => updatePreparationStep(index, e.target.value)}
                        className="flex-1 px-3 py-2 border border-surface-300 rounded-lg text-sm"
                        placeholder="Preparation step..."
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Cost Summary */}
              <div className="p-4 bg-surface-50 rounded-lg">
                <div className="flex justify-between text-sm">
                  <span className="text-surface-600">Total Cost:</span>
                  <span className="font-medium">${newRecipe.ingredients.reduce((sum, i) => sum + (i.cost || 0), 0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm mt-1">
                  <span className="text-surface-600">Pour Cost %:</span>
                  <span className={`font-medium ${
                    newRecipe.sell_price > 0 ?
                      ((newRecipe.ingredients.reduce((sum, i) => sum + (i.cost || 0), 0) / newRecipe.sell_price) * 100 <= 20 ? 'text-success-600' :
                       (newRecipe.ingredients.reduce((sum, i) => sum + (i.cost || 0), 0) / newRecipe.sell_price) * 100 <= 25 ? 'text-primary-600' :
                       'text-warning-600')
                    : 'text-surface-600'
                  }`}>
                    {newRecipe.sell_price > 0
                      ? ((newRecipe.ingredients.reduce((sum, i) => sum + (i.cost || 0), 0) / newRecipe.sell_price) * 100).toFixed(1)
                      : 0}%
                  </span>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-surface-200 flex justify-end gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-surface-700 hover:bg-surface-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleAddRecipe}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Add Recipe
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

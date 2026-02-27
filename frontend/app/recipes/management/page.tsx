"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";

interface Recipe {
  id: number;
  name: { bg: string; en: string };
  description?: { bg: string; en: string };
  yield_quantity: number;
  yield_unit: string;
  prep_time_minutes?: number;
  cook_time_minutes?: number;
  difficulty_level?: string;
  total_cost?: number;
  cost_per_portion?: number;
}

interface RecipeIngredient {
  id: number;
  recipe_id: number;
  ingredient_id: number;
  ingredient_name?: string;
  quantity: number;
  unit: string;
  unit_cost?: number;
  total_cost?: number;
}

interface RecipeVersion {
  id: number;
  recipe_id: number;
  version_number: number;
  change_type: string;
  change_notes?: string;
  created_at: string;
}

interface RecipeCostHistory {
  id: number;
  recipe_id: number;
  calculated_at: string;
  ingredient_cost: number;
  labor_cost: number;
  total_cost: number;
  cost_per_portion: number;
}

type TabType = "list" | "details" | "ingredients" | "costing" | "scaling" | "versions";


export default function RecipeManagementPage() {
  const [activeTab, setActiveTab] = useState<TabType>("list");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Data
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [ingredients, setIngredients] = useState<RecipeIngredient[]>([]);
  const [versions, setVersions] = useState<RecipeVersion[]>([]);
  const [costHistory, setCostHistory] = useState<RecipeCostHistory[]>([]);
  const [currentCost, setCurrentCost] = useState<any>(null);
  const [scaledRecipe, setScaledRecipe] = useState<any>(null);

  // Scale form
  const [scaleForm, setScaleForm] = useState({
    target_yield: 1,
    target_unit: "portion"
  });

  // Modals
  const [showRecipeModal, setShowRecipeModal] = useState(false);
  const [, setShowIngredientModal] = useState(false);

  // Recipe form
  const [recipeForm, setRecipeForm] = useState({
    name_bg: "",
    name_en: "",
    description_bg: "",
    description_en: "",
    yield_quantity: 1,
    yield_unit: "portion",
    prep_time_minutes: 0,
    cook_time_minutes: 0,
    difficulty_level: "medium"
  });

  useEffect(() => {
    fetchRecipes();
  }, []);

  useEffect(() => {
    if (selectedRecipe) {
      fetchRecipeDetails(selectedRecipe.id);
    }
  }, [selectedRecipe]);

  const fetchRecipes = async () => {
    try {
      const data = await api.get('/recipes?venue_id=1');
      const list = Array.isArray(data) ? data : ((data as Record<string, unknown>).items || (data as Record<string, unknown>).recipes || []);
      setRecipes(list as Recipe[]);
      if ((list as Recipe[]).length > 0) setSelectedRecipe((list as Recipe[])[0]);
    } catch (error) {
      console.error("Error fetching recipes:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecipeDetails = async (recipeId: number) => {
    try {
      // Fetch full recipe with ingredients
      try {
        const data = await api.get<{ ingredients?: RecipeIngredient[] }>(`/recipes/${recipeId}`);
        if (data.ingredients) setIngredients(data.ingredients);
      } catch {
        // Recipe detail may not be available
      }

      // Fetch versions
      try {
        const versionsData = await api.get<RecipeVersion[]>(`/recipes/${recipeId}/versions`);
        setVersions(versionsData);
      } catch {
        // Versions may not be available
      }

      // Fetch current cost
      try {
        const costData = await api.get(`/recipes/${recipeId}/cost`);
        setCurrentCost(costData);
      } catch {
        // Cost data may not be available
      }

      // Fetch cost history
      try {
        const historyData = await api.get<RecipeCostHistory[]>(`/recipes/${recipeId}/cost-history`);
        setCostHistory(historyData);
      } catch {
        // Cost history may not be available
      }

    } catch (error) {
      console.error("Error fetching recipe details:", error);
    }
  };

  const handleScaleRecipe = async () => {
    if (!selectedRecipe) return;
    setSaving(true);

    try {
      const data = await api.post('/recipes/scale', {
        recipe_id: selectedRecipe.id,
        target_yield: scaleForm.target_yield,
        target_unit: scaleForm.target_unit
      });
      setScaledRecipe(data);
    } catch (error) {
      console.error("Error scaling recipe:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateRecipe = async () => {
    setSaving(true);
    try {
      await api.post('/recipes?venue_id=1', {
        name: { bg: recipeForm.name_bg, en: recipeForm.name_en },
        description: { bg: recipeForm.description_bg, en: recipeForm.description_en },
        yield_quantity: recipeForm.yield_quantity,
        yield_unit: recipeForm.yield_unit,
        prep_time_minutes: recipeForm.prep_time_minutes,
        cook_time_minutes: recipeForm.cook_time_minutes,
        difficulty_level: recipeForm.difficulty_level
      });
      setShowRecipeModal(false);
      fetchRecipes();
    } catch (error) {
      console.error("Error creating recipe:", error);
    } finally {
      setSaving(false);
    }
  };

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: "list", label: "All Recipes", icon: "📋" },
    { id: "details", label: "Details", icon: "📝" },
    { id: "ingredients", label: "Ingredients", icon: "🥕" },
    { id: "costing", label: "Costing", icon: "💰" },
    { id: "scaling", label: "Scaling", icon: "📐" },
    { id: "versions", label: "Versions", icon: "📜" }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white min-h-screen text-gray-900">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Recipe Management</h1>
          <p className="text-gray-400 mt-1">Recipe costing, scaling, versioning, and ingredients</p>
        </div>
        <button
          onClick={() => setShowRecipeModal(true)}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2"
        >
          + New Recipe
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Total Recipes</div>
          <div className="text-2xl font-bold">{recipes.length}</div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Avg Cost/Portion</div>
          <div className="text-2xl font-bold text-orange-400">
            {recipes.length > 0 && recipes[0].cost_per_portion
              ? `${(recipes[0].cost_per_portion || 0).toFixed(2)} лв`
              : "N/A"}
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Selected Recipe</div>
          <div className="text-lg font-bold truncate">
            {selectedRecipe?.name.bg || selectedRecipe?.name.en || "None"}
          </div>
        </div>
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-gray-400 text-sm">Ingredients</div>
          <div className="text-2xl font-bold">{ingredients.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Recipe List Sidebar */}
        <div className="col-span-3 bg-gray-50 rounded-xl p-4 max-h-[70vh] overflow-y-auto">
          <h2 className="text-lg font-semibold mb-4">Recipes</h2>
          <div className="space-y-2">
            {recipes.map((recipe) => (
              <button
                key={recipe.id}
                onClick={() => {
                  setSelectedRecipe(recipe);
                  setActiveTab("details");
                }}
                className={`w-full text-left p-3 rounded-lg transition ${
                  selectedRecipe?.id === recipe.id
                    ? "bg-orange-600"
                    : "bg-gray-100 hover:bg-gray-600"
                }`}
              >
                <div className="font-medium">{recipe.name.bg || recipe.name.en}</div>
                <div className="text-sm text-gray-300 flex justify-between">
                  <span>{recipe.yield_quantity} {recipe.yield_unit}</span>
                  {recipe.cost_per_portion && (
                    <span className="text-orange-300">{(recipe.cost_per_portion || 0).toFixed(2)} лв</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="col-span-9">
          {/* Tabs */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg whitespace-nowrap transition ${
                  activeTab === tab.id
                    ? "bg-orange-600"
                    : "bg-gray-50 hover:bg-gray-100"
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="bg-gray-50 rounded-xl p-6">
            {activeTab === "list" && (
              <div>
                <h3 className="text-xl font-semibold mb-4">All Recipes</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-gray-400 border-b border-gray-300">
                        <th className="pb-3">Name</th>
                        <th className="pb-3">Yield</th>
                        <th className="pb-3">Prep Time</th>
                        <th className="pb-3">Cook Time</th>
                        <th className="pb-3">Cost/Portion</th>
                        <th className="pb-3">Difficulty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recipes.map((recipe) => (
                        <tr
                          key={recipe.id}
                          className="border-b border-gray-300 cursor-pointer hover:bg-gray-100"
                          onClick={() => {
                            setSelectedRecipe(recipe);
                            setActiveTab("details");
                          }}
                        >
                          <td className="py-3 font-medium">{recipe.name.bg || recipe.name.en}</td>
                          <td className="py-3">{recipe.yield_quantity} {recipe.yield_unit}</td>
                          <td className="py-3">{recipe.prep_time_minutes || "-"} min</td>
                          <td className="py-3">{recipe.cook_time_minutes || "-"} min</td>
                          <td className="py-3 text-orange-400">
                            {(recipe.cost_per_portion || 0).toFixed(2) || "-"} лв
                          </td>
                          <td className="py-3 capitalize">{recipe.difficulty_level || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === "details" && selectedRecipe && (
              <div>
                <h3 className="text-xl font-semibold mb-4">{selectedRecipe.name.bg || selectedRecipe.name.en}</h3>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <span className="text-gray-400 text-sm">Description (BG)</span>
                    <p className="mt-1">{selectedRecipe.description?.bg || "No description"}</p>
                  </div>
                  <div>
                    <span className="text-gray-400 text-sm">Description (EN)</span>
                    <p className="mt-1">{selectedRecipe.description?.en || "No description"}</p>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-4 mt-6">
                  <div className="bg-gray-100 rounded-lg p-4">
                    <div className="text-gray-400 text-sm">Yield</div>
                    <div className="text-xl font-semibold">{selectedRecipe.yield_quantity} {selectedRecipe.yield_unit}</div>
                  </div>
                  <div className="bg-gray-100 rounded-lg p-4">
                    <div className="text-gray-400 text-sm">Prep Time</div>
                    <div className="text-xl font-semibold">{selectedRecipe.prep_time_minutes || 0} min</div>
                  </div>
                  <div className="bg-gray-100 rounded-lg p-4">
                    <div className="text-gray-400 text-sm">Cook Time</div>
                    <div className="text-xl font-semibold">{selectedRecipe.cook_time_minutes || 0} min</div>
                  </div>
                  <div className="bg-gray-100 rounded-lg p-4">
                    <div className="text-gray-400 text-sm">Difficulty</div>
                    <div className="text-xl font-semibold capitalize">{selectedRecipe.difficulty_level || "N/A"}</div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "ingredients" && selectedRecipe && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-semibold">Ingredients</h3>
                  <button
                    onClick={() => setShowIngredientModal(true)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
                  >
                    + Add Ingredient
                  </button>
                </div>
                {ingredients.length === 0 ? (
                  <p className="text-gray-400">No ingredients added yet</p>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-gray-400 border-b border-gray-300">
                        <th className="pb-3">Ingredient</th>
                        <th className="pb-3">Quantity</th>
                        <th className="pb-3">Unit</th>
                        <th className="pb-3">Unit Cost</th>
                        <th className="pb-3">Total Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ingredients.map((ing) => (
                        <tr key={ing.id} className="border-b border-gray-300">
                          <td className="py-3">{ing.ingredient_name || `Item #${ing.ingredient_id}`}</td>
                          <td className="py-3">{ing.quantity}</td>
                          <td className="py-3">{ing.unit}</td>
                          <td className="py-3">{(ing.unit_cost || 0).toFixed(2) || "-"} лв</td>
                          <td className="py-3 text-orange-400">{(ing.total_cost || 0).toFixed(2) || "-"} лв</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            {activeTab === "costing" && selectedRecipe && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Recipe Costing</h3>
                {currentCost ? (
                  <>
                    <div className="grid grid-cols-4 gap-4 mb-6">
                      <div className="bg-gray-100 rounded-lg p-4 text-center">
                        <div className="text-gray-400 text-sm">Ingredient Cost</div>
                        <div className="text-2xl font-bold">{(currentCost.ingredient_cost || 0).toFixed(2)} лв</div>
                      </div>
                      <div className="bg-gray-100 rounded-lg p-4 text-center">
                        <div className="text-gray-400 text-sm">Labor Cost</div>
                        <div className="text-2xl font-bold">{(currentCost.labor_cost || 0).toFixed(2) || "0.00"} лв</div>
                      </div>
                      <div className="bg-gray-100 rounded-lg p-4 text-center">
                        <div className="text-gray-400 text-sm">Total Cost</div>
                        <div className="text-2xl font-bold text-orange-400">{(currentCost.total_cost || 0).toFixed(2)} лв</div>
                      </div>
                      <div className="bg-gray-100 rounded-lg p-4 text-center">
                        <div className="text-gray-400 text-sm">Cost/Portion</div>
                        <div className="text-2xl font-bold text-green-400">{(currentCost.cost_per_portion || 0).toFixed(2)} лв</div>
                      </div>
                    </div>
                    <h4 className="font-semibold mb-3">Cost History</h4>
                    <div className="space-y-2">
                      {costHistory.map((history) => (
                        <div key={history.id} className="bg-gray-100 rounded-lg p-3 flex justify-between items-center">
                          <span>{new Date(history.calculated_at).toLocaleDateString()}</span>
                          <span className="text-orange-400">{(history.cost_per_portion || 0).toFixed(2)} лв/portion</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-gray-400">No costing data available</p>
                )}
              </div>
            )}

            {activeTab === "scaling" && selectedRecipe && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Scale Recipe</h3>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Target Yield
                    <input
                      type="number"
                      value={scaleForm.target_yield}
                      onChange={(e) => setScaleForm({ ...scaleForm, target_yield: parseFloat(e.target.value) })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                      min={0.1}
                      step={0.5}
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Unit
                    <select
                      value={scaleForm.target_unit}
                      onChange={(e) => setScaleForm({ ...scaleForm, target_unit: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    >
                      <option value="portion">Portion</option>
                      <option value="kg">Kilogram</option>
                      <option value="l">Liter</option>
                    </select>
                    </label>
                  </div>
                </div>
                <button
                  onClick={handleScaleRecipe}
                  disabled={saving}
                  className="px-6 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Scaling..." : "Scale Recipe"}
                </button>

                {scaledRecipe && (
                  <div className="mt-6">
                    <h4 className="font-semibold mb-3">Scaled Ingredients</h4>
                    <div className="bg-gray-100 rounded-lg p-4">
                      <div className="text-sm text-gray-400 mb-2">
                        Scaling factor: {(scaledRecipe.scaling_factor || 0).toFixed(2)}x
                      </div>
                      {scaledRecipe.scaled_ingredients?.map((ing: any, i: number) => (
                        <div key={i} className="flex justify-between py-2 border-b border-gray-200">
                          <span>{ing.name}</span>
                          <span className="text-orange-400">{(ing.scaled_quantity || 0).toFixed(2)} {ing.unit}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "versions" && selectedRecipe && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Version History</h3>
                {versions.length === 0 ? (
                  <p className="text-gray-400">No version history</p>
                ) : (
                  <div className="space-y-3">
                    {versions.map((version) => (
                      <div key={version.id} className="bg-gray-100 rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <span className="font-semibold">Version {version.version_number}</span>
                            <span className="ml-2 px-2 py-1 bg-blue-600 rounded text-xs">
                              {version.change_type}
                            </span>
                          </div>
                          <span className="text-sm text-gray-400">
                            {new Date(version.created_at).toLocaleString()}
                          </span>
                        </div>
                        {version.change_notes && (
                          <p className="text-sm text-gray-300 mt-2">{version.change_notes}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recipe Modal */}
      <AnimatePresence>
        {showRecipeModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowRecipeModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4">New Recipe</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Name (BG)
                    <input
                      type="text"
                      value={recipeForm.name_bg}
                      onChange={(e) => setRecipeForm({ ...recipeForm, name_bg: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Name (EN)
                    <input
                      type="text"
                      value={recipeForm.name_en}
                      onChange={(e) => setRecipeForm({ ...recipeForm, name_en: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                    </label>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Yield Quantity
                    <input
                      type="number"
                      value={recipeForm.yield_quantity}
                      onChange={(e) => setRecipeForm({ ...recipeForm, yield_quantity: parseFloat(e.target.value) })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Yield Unit
                    <select
                      value={recipeForm.yield_unit}
                      onChange={(e) => setRecipeForm({ ...recipeForm, yield_unit: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    >
                      <option value="portion">Portion</option>
                      <option value="kg">Kilogram</option>
                      <option value="l">Liter</option>
                      <option value="pcs">Pieces</option>
                    </select>
                    </label>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Prep Time (min)
                    <input
                      type="number"
                      value={recipeForm.prep_time_minutes}
                      onChange={(e) => setRecipeForm({ ...recipeForm, prep_time_minutes: parseInt(e.target.value) })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Cook Time (min)
                    <input
                      type="number"
                      value={recipeForm.cook_time_minutes}
                      onChange={(e) => setRecipeForm({ ...recipeForm, cook_time_minutes: parseInt(e.target.value) })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    />
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Difficulty
                    <select
                      value={recipeForm.difficulty_level}
                      onChange={(e) => setRecipeForm({ ...recipeForm, difficulty_level: e.target.value })}
                      className="w-full p-2 bg-gray-100 rounded-lg"
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                    </label>
                  </div>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowRecipeModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-600 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateRecipe}
                  disabled={saving || !recipeForm.name_bg}
                  className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
                >
                  {saving ? "Creating..." : "Create Recipe"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

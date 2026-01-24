"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Ingredient {
  name: string;
  quantity: number;
  unit: string;
  stock_item_id?: number;
}

interface Recipe {
  ingredients: Ingredient[];
  steps: string[];
  prep_time_minutes: number;
  cook_time_minutes: number;
  portions: number;
  kcal: number;
  notes: string;
}

interface MenuItem {
  id: number;
  name: { bg: string; en?: string };
  price: number;
  recipe?: Recipe;
}

interface StockItem {
  id: number;
  name: string;
  unit: string;
  cost_per_unit?: number;
}

export default function RecipesPage() {
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [showEditor, setShowEditor] = useState(false);
  const [costAnalysis, setCostAnalysis] = useState<any>(null);

  const [recipe, setRecipe] = useState<Recipe>({
    ingredients: [],
    steps: [],
    prep_time_minutes: 0,
    cook_time_minutes: 0,
    portions: 1,
    kcal: 0,
    notes: "",
  });

  const [newIngredient, setNewIngredient] = useState<Ingredient>({
    name: "",
    quantity: 0,
    unit: "g",
  });

  const [newStep, setNewStep] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const token = localStorage.getItem("access_token");

    try {
      // Load recipes
      const recipesRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu/recipes/all`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (recipesRes.ok) {
        const data = await recipesRes.json();
        setMenuItems(data.recipes || []);
      }

      // Load stock items for linking
      const stockRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/stock`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (stockRes.ok) {
        setStockItems(await stockRes.json());
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadRecipe = async (itemId: number) => {
    const token = localStorage.getItem("access_token");

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu/items/${itemId}/recipe`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.ok) {
        const data = await res.json();
        setRecipe(data.recipe);
        setSelectedItem({ id: itemId, name: data.item_name, price: 0 });
        setShowEditor(true);
      }
    } catch (error) {
      alert("Error loading recipe");
    }
  };

  const saveRecipe = async () => {
    if (!selectedItem) return;

    const token = localStorage.getItem("access_token");

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu/items/${selectedItem.id}/recipe`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(recipe),
        }
      );

      if (res.ok) {
        alert("Recipe saved!");
        setShowEditor(false);
        loadData();
      }
    } catch (error) {
      alert("Error saving recipe");
    }
  };

  const calculateCost = async () => {
    if (!selectedItem) return;

    const token = localStorage.getItem("access_token");

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/menu/recipes/calculate-cost/${selectedItem.id}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (res.ok) {
        setCostAnalysis(await res.json());
      }
    } catch (error) {
      alert("Error calculating cost");
    }
  };

  const addIngredient = () => {
    if (!newIngredient.name || newIngredient.quantity <= 0) return;

    setRecipe({
      ...recipe,
      ingredients: [...recipe.ingredients, { ...newIngredient }],
    });
    setNewIngredient({ name: "", quantity: 0, unit: "g" });
  };

  const removeIngredient = (index: number) => {
    setRecipe({
      ...recipe,
      ingredients: recipe.ingredients.filter((_, i) => i !== index),
    });
  };

  const addStep = () => {
    if (!newStep.trim()) return;

    setRecipe({
      ...recipe,
      steps: [...recipe.steps, newStep.trim()],
    });
    setNewStep("");
  };

  const removeStep = (index: number) => {
    setRecipe({
      ...recipe,
      steps: recipe.steps.filter((_, i) => i !== index),
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Recipe Management</h1>
            <p className="text-gray-600">Manage recipes and calculate costs</p>
          </div>
          <button
            onClick={() => window.location.href = '/recipes/management'}
            className="px-4 py-2 bg-blue-600 text-gray-900 rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <span>📊</span>
            <span>Advanced (Costing, Scaling, Versions)</span>
          </button>
        </div>

        {/* Items with Recipes */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {menuItems.map((item) => (
            <motion.div
              key={item.id}
              whileHover={{ scale: 1.02 }}
              className="bg-gray-100 rounded-xl p-4 cursor-pointer"
              onClick={() => loadRecipe(item.id)}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-gray-900 font-semibold">
                  {item.name?.bg || item.name?.en || "Item"}
                </h3>
                <span className="text-orange-400 font-bold">{item.price?.toFixed(2)} €</span>
              </div>

              {item.recipe && (
                <div className="text-gray-600 text-sm">
                  <p>📝 {item.recipe.ingredients?.length || 0} ingredients</p>
                  <p>⏱️ {(item.recipe.prep_time_minutes || 0) + (item.recipe.cook_time_minutes || 0)} min</p>
                  <p>🔥 {item.recipe.kcal || 0} kcal</p>
                </div>
              )}

              <button className="mt-3 w-full py-2 bg-orange-500/20 text-orange-400 rounded-lg text-sm hover:bg-orange-500/30">
                Edit Recipe
              </button>
            </motion.div>
          ))}

          {menuItems.length === 0 && (
            <div className="col-span-full text-center py-12 text-gray-500">
              No items with recipes yet. Add recipes to menu items to see them here.
            </div>
          )}
        </div>

        {/* Enter Item ID manually */}
        <div className="mt-8 bg-gray-100 rounded-xl p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Add Recipe to Item</h2>
          <div className="flex gap-4">
            <input
              type="number"
              placeholder="Menu Item ID"
              className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-xl"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  const id = parseInt((e.target as HTMLInputElement).value);
                  if (id) loadRecipe(id);
                }
              }}
            />
            <button
              onClick={() => {
                const input = document.querySelector('input[placeholder="Menu Item ID"]') as HTMLInputElement;
                const id = parseInt(input?.value);
                if (id) loadRecipe(id);
              }}
              className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl"
            >
              Load Recipe
            </button>
          </div>
        </div>
      </div>

      {/* Recipe Editor Modal */}
      <AnimatePresence>
        {showEditor && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-white/70 flex items-center justify-center z-50 p-4 overflow-y-auto"
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  📖 Recipe: {selectedItem?.name?.bg || selectedItem?.name?.en || "Item"}
                </h2>
                <button
                  onClick={() => setShowEditor(false)}
                  className="text-gray-600 text-2xl hover:text-gray-900"
                >
                  ✕
                </button>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                {/* Left Column - Ingredients */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">🥗 Ingredients</h3>

                  <div className="space-y-2 mb-4">
                    {recipe.ingredients.map((ing, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 bg-gray-50 p-3 rounded-lg"
                      >
                        <span className="text-gray-900 flex-1">
                          {ing.quantity} {ing.unit} - {ing.name}
                        </span>
                        {ing.stock_item_id && (
                          <span className="text-green-400 text-xs">🔗 Linked</span>
                        )}
                        <button
                          onClick={() => removeIngredient(idx)}
                          className="text-red-400 hover:text-red-300"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="bg-gray-50 p-4 rounded-xl">
                    <div className="grid grid-cols-3 gap-2 mb-2">
                      <input
                        type="number"
                        placeholder="Qty"
                        value={newIngredient.quantity || ""}
                        onChange={(e) =>
                          setNewIngredient({ ...newIngredient, quantity: Number(e.target.value) })
                        }
                        className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm"
                      />
                      <select
                        value={newIngredient.unit}
                        onChange={(e) =>
                          setNewIngredient({ ...newIngredient, unit: e.target.value })
                        }
                        className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm"
                      >
                        <option value="g">g</option>
                        <option value="kg">kg</option>
                        <option value="ml">ml</option>
                        <option value="l">l</option>
                        <option value="pcs">pcs</option>
                        <option value="tbsp">tbsp</option>
                        <option value="tsp">tsp</option>
                      </select>
                      <select
                        value={newIngredient.stock_item_id || ""}
                        onChange={(e) =>
                          setNewIngredient({
                            ...newIngredient,
                            stock_item_id: e.target.value ? Number(e.target.value) : undefined,
                            name: stockItems.find((s) => s.id === Number(e.target.value))?.name || newIngredient.name,
                          })
                        }
                        className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm"
                      >
                        <option value="">Link Stock</option>
                        {stockItems.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <input
                      type="text"
                      placeholder="Ingredient name"
                      value={newIngredient.name}
                      onChange={(e) =>
                        setNewIngredient({ ...newIngredient, name: e.target.value })
                      }
                      className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm mb-2"
                    />
                    <button
                      onClick={addIngredient}
                      className="w-full py-2 bg-green-500/20 text-green-400 rounded-lg text-sm"
                    >
                      + Add Ingredient
                    </button>
                  </div>
                </div>

                {/* Right Column - Steps & Info */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">👨‍🍳 Steps</h3>

                  <div className="space-y-2 mb-4">
                    {recipe.steps.map((step, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 bg-gray-50 p-3 rounded-lg"
                      >
                        <span className="text-orange-400 font-bold">{idx + 1}.</span>
                        <span className="text-gray-900 flex-1">{step}</span>
                        <button
                          onClick={() => removeStep(idx)}
                          className="text-red-400 hover:text-red-300"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="bg-gray-50 p-4 rounded-xl mb-4">
                    <textarea
                      placeholder="Add a step..."
                      value={newStep}
                      onChange={(e) => setNewStep(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg text-sm mb-2 resize-none h-20"
                    />
                    <button
                      onClick={addStep}
                      className="w-full py-2 bg-blue-500/20 text-blue-400 rounded-lg text-sm"
                    >
                      + Add Step
                    </button>
                  </div>

                  {/* Timing & Nutrition */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-gray-600 text-sm">Prep Time (min)</label>
                      <input
                        type="number"
                        value={recipe.prep_time_minutes}
                        onChange={(e) =>
                          setRecipe({ ...recipe, prep_time_minutes: Number(e.target.value) })
                        }
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="text-gray-600 text-sm">Cook Time (min)</label>
                      <input
                        type="number"
                        value={recipe.cook_time_minutes}
                        onChange={(e) =>
                          setRecipe({ ...recipe, cook_time_minutes: Number(e.target.value) })
                        }
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="text-gray-600 text-sm">Portions</label>
                      <input
                        type="number"
                        value={recipe.portions}
                        onChange={(e) =>
                          setRecipe({ ...recipe, portions: Number(e.target.value) })
                        }
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="text-gray-600 text-sm">Calories (kcal)</label>
                      <input
                        type="number"
                        value={recipe.kcal}
                        onChange={(e) =>
                          setRecipe({ ...recipe, kcal: Number(e.target.value) })
                        }
                        className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg"
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="text-gray-600 text-sm">Notes</label>
                    <textarea
                      value={recipe.notes}
                      onChange={(e) => setRecipe({ ...recipe, notes: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-100 text-gray-900 rounded-lg resize-none h-20"
                      placeholder="Special instructions, tips..."
                    />
                  </div>
                </div>
              </div>

              {/* Cost Analysis */}
              {costAnalysis && (
                <div className="mt-6 bg-green-500/10 border border-green-500/30 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-green-400 mb-3">💰 Cost Analysis</h3>
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div>
                      <div className="text-gray-600 text-sm">Selling Price</div>
                      <div className="text-gray-900 text-xl font-bold">{costAnalysis.selling_price?.toFixed(2)} €</div>
                    </div>
                    <div>
                      <div className="text-gray-600 text-sm">Total Cost</div>
                      <div className="text-red-400 text-xl font-bold">{costAnalysis.total_cost?.toFixed(2)} €</div>
                    </div>
                    <div>
                      <div className="text-gray-600 text-sm">Profit</div>
                      <div className="text-green-400 text-xl font-bold">{costAnalysis.profit_margin?.toFixed(2)} €</div>
                    </div>
                    <div>
                      <div className="text-gray-600 text-sm">Margin</div>
                      <div className="text-green-400 text-xl font-bold">{costAnalysis.profit_percentage?.toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="mt-6 flex gap-4">
                <button
                  onClick={() => setShowEditor(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  onClick={calculateCost}
                  className="flex-1 py-3 bg-blue-500 text-gray-900 rounded-xl"
                >
                  💰 Calculate Cost
                </button>
                <button
                  onClick={saveRecipe}
                  className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl"
                >
                  💾 Save Recipe
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

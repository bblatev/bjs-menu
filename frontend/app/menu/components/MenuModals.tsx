"use client";

import { AnimatePresence, motion } from "framer-motion";
import type {
  Category, MenuItem, Station, ModifierGroup, ModifierOption,
  ItemFormData, CategoryFormData, ModifierGroupFormData, OptionFormData,
} from "./types";

interface MenuModalsProps {
  // Item modal
  showItemModal: boolean;
  setShowItemModal: (v: boolean) => void;
  editingItem: MenuItem | null;
  setEditingItem: (v: MenuItem | null) => void;
  itemForm: ItemFormData;
  setItemForm: (v: ItemFormData) => void;
  handleCreateItem: (e: React.FormEvent) => void;
  handleUpdateItem: (e: React.FormEvent) => void;
  categories: Category[];
  stations: Station[];
  // Category modal
  showCategoryModal: boolean;
  setShowCategoryModal: (v: boolean) => void;
  editingCategory: Category | null;
  setEditingCategory: (v: Category | null) => void;
  categoryForm: CategoryFormData;
  setCategoryForm: (v: CategoryFormData) => void;
  handleCreateCategory: (e: React.FormEvent) => void;
  handleUpdateCategory: (e: React.FormEvent) => void;
  // Modifier Group modal
  showModifierGroupModal: boolean;
  setShowModifierGroupModal: (v: boolean) => void;
  editingModifierGroup: ModifierGroup | null;
  setEditingModifierGroup: (v: ModifierGroup | null) => void;
  modifierGroupForm: ModifierGroupFormData;
  setModifierGroupForm: (v: ModifierGroupFormData) => void;
  handleCreateModifierGroup: (e: React.FormEvent) => void;
  handleUpdateModifierGroup: (e: React.FormEvent) => void;
  // Option modal
  showOptionModal: boolean;
  setShowOptionModal: (v: boolean) => void;
  editingOption: ModifierOption | null;
  setEditingOption: (v: ModifierOption | null) => void;
  optionForm: OptionFormData;
  setOptionForm: (v: OptionFormData) => void;
  handleCreateOption: (e: React.FormEvent) => void;
  handleUpdateOption: (e: React.FormEvent) => void;
}

export default function MenuModals(props: MenuModalsProps) {
  const {
    showItemModal, setShowItemModal, editingItem, setEditingItem, itemForm, setItemForm,
    handleCreateItem, handleUpdateItem, categories, stations,
    showCategoryModal, setShowCategoryModal, editingCategory, setEditingCategory,
    categoryForm, setCategoryForm, handleCreateCategory, handleUpdateCategory,
    showModifierGroupModal, setShowModifierGroupModal, editingModifierGroup, setEditingModifierGroup,
    modifierGroupForm, setModifierGroupForm, handleCreateModifierGroup, handleUpdateModifierGroup,
    showOptionModal, setShowOptionModal, editingOption, setEditingOption,
    optionForm, setOptionForm, handleCreateOption, handleUpdateOption,
  } = props;

  return (
    <>
      {/* Item Modal */}
      <AnimatePresence>
        {showItemModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">{editingItem ? "Edit Item" : "Add New Item"}</h2>
              <form onSubmit={editingItem ? handleUpdateItem : handleCreateItem} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-700 text-sm">Name (EN)<input type="text" value={itemForm.name_en} onChange={(e) => setItemForm({ ...itemForm, name_en: e.target.value })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                  <div><label className="text-gray-700 text-sm">Name (BG)<input type="text" value={itemForm.name_bg} onChange={(e) => setItemForm({ ...itemForm, name_bg: e.target.value })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-700 text-sm">Description (EN)<textarea value={itemForm.description_en} onChange={(e) => setItemForm({ ...itemForm, description_en: e.target.value })} className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20" /></label></div>
                  <div><label className="text-gray-700 text-sm">Description (BG)<textarea value={itemForm.description_bg} onChange={(e) => setItemForm({ ...itemForm, description_bg: e.target.value })} className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20" /></label></div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div><label className="text-gray-700 text-sm">Price (lv)<input type="number" step="0.01" min="0" value={itemForm.price} onChange={(e) => setItemForm({ ...itemForm, price: parseFloat(e.target.value) || 0 })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                  <div><label className="text-gray-700 text-sm">Category<select value={itemForm.category_id} onChange={(e) => setItemForm({ ...itemForm, category_id: parseInt(e.target.value) })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"><option value="">Select...</option>{categories.map((cat) => <option key={cat.id} value={cat.id}>{cat.name.en || cat.name.bg}</option>)}</select></label></div>
                  <div><label className="text-gray-700 text-sm">Station<select value={itemForm.station_id} onChange={(e) => setItemForm({ ...itemForm, station_id: parseInt(e.target.value) })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"><option value="">Select...</option>{stations.map((station) => <option key={station.id} value={station.id}>{station.name.en || station.name.bg}</option>)}</select></label></div>
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" id="available" checked={itemForm.available} onChange={(e) => setItemForm({ ...itemForm, available: e.target.checked })} className="w-5 h-5" />
                  <span className="text-gray-900">Available for ordering</span>
                </div>
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={() => { setShowItemModal(false); setEditingItem(null); }} className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200">Cancel</button>
                  <button type="submit" className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600">{editingItem ? "Save Changes" : "Create Item"}</button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Category Modal */}
      <AnimatePresence>
        {showCategoryModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">{editingCategory ? "Edit Category" : "New Category"}</h2>
              <form onSubmit={editingCategory ? handleUpdateCategory : handleCreateCategory} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-700 text-sm">Name (EN)<input type="text" value={categoryForm.name_en} onChange={(e) => setCategoryForm({ ...categoryForm, name_en: e.target.value })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                  <div><label className="text-gray-700 text-sm">Name (BG)<input type="text" value={categoryForm.name_bg} onChange={(e) => setCategoryForm({ ...categoryForm, name_bg: e.target.value })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                </div>
                <div><label className="text-gray-700 text-sm">Description (EN)<textarea value={categoryForm.description_en} onChange={(e) => setCategoryForm({ ...categoryForm, description_en: e.target.value })} className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1 h-20" /></label></div>
                <div><label className="text-gray-700 text-sm">Sort Order<input type="number" value={categoryForm.sort_order} onChange={(e) => setCategoryForm({ ...categoryForm, sort_order: parseInt(e.target.value) || 0 })} className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={() => { setShowCategoryModal(false); setEditingCategory(null); }} className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200">Cancel</button>
                  <button type="submit" className="flex-1 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600">{editingCategory ? "Save" : "Create"}</button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modifier Group Modal */}
      <AnimatePresence>
        {showModifierGroupModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">{editingModifierGroup ? "Edit Modifier Group" : "New Modifier Group"}</h2>
              <form onSubmit={editingModifierGroup ? handleUpdateModifierGroup : handleCreateModifierGroup} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-700 text-sm">Name (EN)<input type="text" value={modifierGroupForm.name_en} onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, name_en: e.target.value })} required placeholder="e.g. Size, Sauce, Extras" className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                  <div><label className="text-gray-700 text-sm">Name (BG)<input type="text" value={modifierGroupForm.name_bg} onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, name_bg: e.target.value })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" id="required" checked={modifierGroupForm.required} onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, required: e.target.checked })} className="w-5 h-5" />
                  <span className="text-gray-900">Required (customer must select)</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-700 text-sm">Min Selections<input type="number" min="0" value={modifierGroupForm.min_selections} onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, min_selections: parseInt(e.target.value) || 0 })} className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                  <div><label className="text-gray-700 text-sm">Max Selections<input type="number" min="1" value={modifierGroupForm.max_selections} onChange={(e) => setModifierGroupForm({ ...modifierGroupForm, max_selections: parseInt(e.target.value) || 1 })} className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                </div>
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={() => { setShowModifierGroupModal(false); setEditingModifierGroup(null); }} className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200">Cancel</button>
                  <button type="submit" className="flex-1 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600">{editingModifierGroup ? "Save" : "Create"}</button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Option Modal */}
      <AnimatePresence>
        {showOptionModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">{editingOption ? "Edit Option" : "Add Option"}</h2>
              <form onSubmit={editingOption ? handleUpdateOption : handleCreateOption} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="text-gray-700 text-sm">Name (EN)<input type="text" value={optionForm.name_en} onChange={(e) => setOptionForm({ ...optionForm, name_en: e.target.value })} required placeholder="e.g. Small, Medium, Large" className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                  <div><label className="text-gray-700 text-sm">Name (BG)<input type="text" value={optionForm.name_bg} onChange={(e) => setOptionForm({ ...optionForm, name_bg: e.target.value })} required className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" /></label></div>
                </div>
                <div>
                  <span className="text-gray-700 text-sm">Price Adjustment (lv)
                    <input type="number" step="0.01" value={optionForm.price_delta} onChange={(e) => setOptionForm({ ...optionForm, price_delta: parseFloat(e.target.value) || 0 })} className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1" placeholder="0 for no change, +2.00 for extra, -1.00 for discount" />
                  </span>
                  <p className="text-gray-500 text-xs mt-1">Use positive for extra cost, negative for discount</p>
                </div>
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={() => { setShowOptionModal(false); setEditingOption(null); }} className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl hover:bg-gray-200">Cancel</button>
                  <button type="submit" className="flex-1 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600">{editingOption ? "Save" : "Create"}</button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}

"use client";

import { motion } from "framer-motion";
import type { MenuItem, ModifierGroup, ModifierOption } from "./types";

interface ModifiersTabProps {
  selectedItemForModifiers: MenuItem;
  modifierGroups: ModifierGroup[];
  openCreateModifierGroupModal: () => void;
  openAddOptionModal: (groupId: number) => void;
  openEditModifierGroupModal: (group: ModifierGroup) => void;
  handleDeleteModifierGroup: (groupId: number) => void;
  openEditOptionModal: (option: ModifierOption) => void;
  handleDeleteOption: (optionId: number) => void;
}

export default function ModifiersTab({
  selectedItemForModifiers, modifierGroups,
  openCreateModifierGroupModal, openAddOptionModal,
  openEditModifierGroupModal, handleDeleteModifierGroup,
  openEditOptionModal, handleDeleteOption,
}: ModifiersTabProps) {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            Modifiers for: {selectedItemForModifiers.name.en || selectedItemForModifiers.name.bg}
          </h2>
          <p className="text-gray-500">{modifierGroups.length} modifier groups</p>
        </div>
        <button onClick={openCreateModifierGroupModal}
          className="px-4 py-2 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600">
          + Add Modifier Group
        </button>
      </div>

      {modifierGroups.length === 0 ? (
        <div className="text-center py-16 bg-gray-50 rounded-2xl">
          <div className="text-6xl mb-4">🎛️</div>
          <p className="text-gray-900 text-xl mb-2">No modifiers configured</p>
          <p className="text-gray-500 mb-6">Add modifier groups like &quot;Size&quot;, &quot;Extras&quot;, &quot;Sauce&quot;, etc.</p>
          <button onClick={openCreateModifierGroupModal}
            className="px-6 py-3 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600">
            Add First Modifier Group
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {modifierGroups.map((group) => (
            <motion.div key={group.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              className="bg-gray-100 rounded-2xl p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-gray-900 font-bold text-lg">{group.name.en || group.name.bg}</h3>
                  <div className="flex gap-2 mt-1">
                    {group.required && <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">Required</span>}
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
                      Select {group.min_selections}-{group.max_selections}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => openAddOptionModal(group.id)}
                    className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 text-sm">+ Option</button>
                  <button onClick={() => openEditModifierGroupModal(group)}
                    className="px-3 py-1.5 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 text-sm">Edit</button>
                  <button onClick={() => handleDeleteModifierGroup(group.id)}
                    className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm">Delete</button>
                </div>
              </div>

              {group.options.length === 0 ? (
                <p className="text-gray-500 text-sm italic">No options yet</p>
              ) : (
                <div className="space-y-2">
                  {group.options.map((option) => (
                    <div key={option.id}
                      className={`flex items-center justify-between p-3 bg-gray-50 rounded-xl ${!option.available ? "opacity-50" : ""}`}>
                      <div>
                        <span className="text-gray-900">{option.name.en || option.name.bg}</span>
                        {option.price_delta !== 0 && (
                          <span className={`ml-2 text-sm ${option.price_delta > 0 ? "text-green-400" : "text-red-400"}`}>
                            {option.price_delta > 0 ? "+" : ""}{(option.price_delta || 0).toFixed(2)} lv
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => openEditOptionModal(option)}
                          className="px-2 py-1 bg-gray-100 text-gray-900 rounded text-xs hover:bg-gray-200">Edit</button>
                        <button onClick={() => handleDeleteOption(option.id)}
                          className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/30">Delete</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import type { Table, MenuItem, CartItem, Check, Course } from "./types";
import { COURSES } from "./types";

interface MenuScreenProps {
  table: Table | null;
  cart: CartItem[];
  check: Check | null;
  menu: MenuItem[];
  category: string;
  categories: string[];
  filteredMenu: MenuItem[];
  currentSeat: number;
  currentCourse: Course;
  setCurrentSeat: (s: number) => void;
  setCurrentCourse: (c: Course) => void;
  setCategory: (c: string) => void;
  setScreen: (s: "tables" | "menu" | "cart" | "check" | "payment") => void;
  addToCart: (item: MenuItem) => void;
}

export default function MenuScreen({
  table, cart, check, category, categories, filteredMenu,
  currentSeat, currentCourse, setCurrentSeat, setCurrentCourse,
  setCategory, setScreen, addToCart,
}: MenuScreenProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Seat & Course selector */}
      <div className="bg-white px-3 py-2 flex items-center gap-3 border-b border-gray-200 shadow-sm">
        <span className="text-gray-500 text-sm font-semibold">Seat:</span>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5, 6].slice(0, table?.guest_count || 4).map(s => (
            <button key={s} onClick={() => setCurrentSeat(s)}
              className={`w-10 h-10 rounded-xl text-lg font-black ${currentSeat === s ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}>
              {s}
            </button>
          ))}
        </div>
        <span className="text-gray-500 text-sm font-semibold ml-2">Course:</span>
        <div className="flex gap-2">
          {COURSES.map(c => (
            <button key={c.id} onClick={() => setCurrentCourse(c.id)}
              className={`px-3 py-2 rounded-xl text-sm font-bold text-white ${currentCourse === c.id ? c.color : "bg-gray-400"}`}>
              {c.label.slice(0, 4)}
            </button>
          ))}
        </div>
      </div>

      {/* Categories */}
      <div className="px-3 py-2 flex gap-2 overflow-x-auto bg-gray-50 border-b border-gray-200">
        {categories.map(c => (
          <button key={c} onClick={() => setCategory(c)}
            className={`px-4 py-2 rounded-xl text-base font-bold whitespace-nowrap ${
              category === c ? "bg-blue-600 text-white" : "bg-white text-gray-700 border border-gray-200"
            }`}>
            {c === "all" ? "All" : c}
          </button>
        ))}
      </div>

      {/* Menu Grid */}
      <div className="flex-1 overflow-auto p-3">
        <div className="grid grid-cols-2 gap-3">
          {filteredMenu.map(item => {
            const inCart = cart.filter(c => c.menu_item_id === item.id).reduce((s, c) => s + c.quantity, 0);
            return (
              <button key={item.id} onClick={() => addToCart(item)}
                className={`relative rounded-xl text-left active:scale-95 shadow-md border overflow-hidden ${inCart ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-900 border-gray-200"}`}>
                {inCart > 0 && (
                  <div className="absolute top-2 right-2 w-8 h-8 bg-red-500 text-white rounded-full text-lg font-black flex items-center justify-center shadow-lg z-10">
                    {inCart}
                  </div>
                )}
                {item.image ? (
                  <div className="w-full h-24 bg-gray-100 relative">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={item.image}
                      alt={item.name}
                      className="w-full h-full object-cover"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  </div>
                ) : (
                  <div className={`w-full h-16 flex items-center justify-center ${inCart ? "bg-blue-500" : "bg-gradient-to-br from-gray-100 to-gray-200"}`}>
                    <svg className={`w-8 h-8 ${inCart ? "text-blue-300" : "text-gray-400"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}
                <div className="p-3">
                  <div className="text-base font-bold leading-tight line-clamp-2">{item.name}</div>
                  <div className="flex justify-between items-center mt-1">
                    <div className={`text-xs font-medium ${inCart ? "text-blue-100" : "text-gray-500"}`}>{item.category}</div>
                    <div className="font-black text-lg">${(item.price || 0).toFixed(2)}</div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Check info bar */}
      {check && check.items.length > 0 && (
        <div className="bg-white px-3 py-2 border-t border-gray-200 flex items-center justify-between shadow-sm">
          <span className="text-gray-500 text-sm">Check: ${(check.subtotal || 0).toFixed(2)}</span>
          <button onClick={() => setScreen("check")} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium">
            View Check
          </button>
        </div>
      )}
    </div>
  );
}

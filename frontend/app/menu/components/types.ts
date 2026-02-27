export interface MultiLang {
  bg: string;
  en: string;
  de?: string;
  ru?: string;
}

export interface Category {
  id: number;
  name: MultiLang;
  description?: MultiLang;
  sort_order: number;
  active: boolean;
}

export interface Station {
  id: number;
  name: MultiLang;
  station_type: string;
  active: boolean;
}

export interface ModifierOption {
  id: number;
  group_id: number;
  name: MultiLang;
  price_delta: number;
  sort_order: number;
  available: boolean;
}

export interface ModifierGroup {
  id: number;
  item_id: number;
  name: MultiLang;
  required: boolean;
  min_selections: number;
  max_selections: number;
  sort_order: number;
  options: ModifierOption[];
}

export interface MenuItem {
  id: number;
  category_id: number;
  station_id: number;
  name: MultiLang;
  description?: MultiLang;
  price: number;
  sort_order: number;
  available: boolean;
  allergens?: string[];
}

export type TabType = "items" | "categories" | "modifiers";

export interface ItemFormData {
  name_bg: string;
  name_en: string;
  description_bg: string;
  description_en: string;
  price: number;
  category_id: number;
  station_id: number;
  available: boolean;
}

export interface CategoryFormData {
  name_bg: string;
  name_en: string;
  description_bg: string;
  description_en: string;
  sort_order: number;
}

export interface ModifierGroupFormData {
  name_bg: string;
  name_en: string;
  required: boolean;
  min_selections: number;
  max_selections: number;
}

export interface OptionFormData {
  name_bg: string;
  name_en: string;
  price_delta: number;
}

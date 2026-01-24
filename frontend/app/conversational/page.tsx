'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ConversationSession {
  session_id: string;
  customer_name: string;
  language: string;
  order_type: 'dine_in' | 'takeaway' | 'delivery' | 'kiosk';
  status: 'active' | 'ordering' | 'checkout' | 'completed' | 'abandoned';
  items: OrderItem[];
  total: number;
  started_at: string;
  last_interaction: string;
  messages: ConversationMessage[];
  context: ConversationContext;
}

interface OrderItem {
  id: number;
  name: string;
  quantity: number;
  price: number;
  modifiers?: string[];
}

interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  intent?: string;
  entities?: Entity[];
  confidence?: number;
}

interface Entity {
  type: string;
  value: string;
  start: number;
  end: number;
}

interface ConversationContext {
  current_intent: string;
  slot_values: Record<string, any>;
  awaiting_confirmation: boolean;
  last_entity_type?: string;
}

interface Intent {
  name: string;
  description: string;
  examples: string[];
  slots: string[];
  response_templates: string[];
}

interface TrainingExample {
  id: number;
  text: string;
  intent: string;
  entities: Entity[];
  verified: boolean;
  added_at: string;
}

interface LanguageStats {
  code: string;
  name: string;
  flag: string;
  sessions: number;
  accuracy: number;
}

export default function ConversationalOrderingPage() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'sessions' | 'intents' | 'training' | 'testing' | 'analytics'>('dashboard');
  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ConversationSession | null>(null);
  const [intents, setIntents] = useState<Intent[]>([]);
  const [trainingExamples, setTrainingExamples] = useState<TrainingExample[]>([]);
  const [loading, setLoading] = useState(true);

  // Test console state
  const [testInput, setTestInput] = useState('');
  const [testLanguage, setTestLanguage] = useState('en');
  const [testMessages, setTestMessages] = useState<ConversationMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showIntentModal, setShowIntentModal] = useState(false);
  const [showTrainingModal, setShowTrainingModal] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // New intent form
  const [newIntent, setNewIntent] = useState({
    name: '',
    description: '',
    examples: [''],
    slots: [''],
    response_templates: [''],
  });

  // New training example
  const [newExample, setNewExample] = useState({
    text: '',
    intent: '',
    entities: [] as Entity[],
  });

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [testMessages]);

  const loadData = async () => {
    setLoading(true);
    try {
      // In real app, fetch from API
      setSessions(getMockSessions());
      setIntents(getMockIntents());
      setTrainingExamples(getMockTrainingExamples());
    } finally {
      setLoading(false);
    }
  };

  const getMockSessions = (): ConversationSession[] => [
    {
      session_id: 'conv-001',
      customer_name: 'Table 5',
      language: 'en',
      order_type: 'dine_in',
      status: 'active',
      items: [
        { id: 1, name: 'Margherita Pizza', quantity: 1, price: 12.50 },
        { id: 2, name: 'Caesar Salad', quantity: 1, price: 8.00 },
        { id: 3, name: 'Sprite', quantity: 2, price: 5.00 },
      ],
      total: 25.50,
      started_at: new Date(Date.now() - 300000).toISOString(),
      last_interaction: new Date(Date.now() - 30000).toISOString(),
      messages: [
        { id: 1, role: 'assistant', content: 'Welcome! What would you like to order today?', timestamp: new Date(Date.now() - 300000).toISOString() },
        { id: 2, role: 'user', content: 'Can I get a pizza please?', timestamp: new Date(Date.now() - 280000).toISOString(), intent: 'order_item', entities: [{ type: 'menu_item', value: 'pizza', start: 14, end: 19 }], confidence: 0.95 },
        { id: 3, role: 'assistant', content: 'Great choice! Which pizza would you like? We have Margherita, Pepperoni, and Hawaiian.', timestamp: new Date(Date.now() - 275000).toISOString() },
        { id: 4, role: 'user', content: 'Margherita and a salad', timestamp: new Date(Date.now() - 250000).toISOString(), intent: 'order_item', entities: [{ type: 'menu_item', value: 'Margherita', start: 0, end: 10 }, { type: 'menu_item', value: 'salad', start: 17, end: 22 }], confidence: 0.92 },
        { id: 5, role: 'assistant', content: 'I\'ve added Margherita Pizza (12.50 лв) and Caesar Salad (8.00 лв) to your order. Anything else?', timestamp: new Date(Date.now() - 245000).toISOString() },
        { id: 6, role: 'user', content: 'Two sprites', timestamp: new Date(Date.now() - 200000).toISOString(), intent: 'order_item', entities: [{ type: 'quantity', value: '2', start: 0, end: 3 }, { type: 'menu_item', value: 'sprites', start: 4, end: 11 }], confidence: 0.88 },
        { id: 7, role: 'assistant', content: 'Added 2x Sprite (5.00 лв). Your current total is 25.50 лв. Would you like anything else?', timestamp: new Date(Date.now() - 195000).toISOString() },
      ],
      context: {
        current_intent: 'ordering',
        slot_values: { table_number: 5, items: 3 },
        awaiting_confirmation: false,
      },
    },
    {
      session_id: 'conv-002',
      customer_name: 'Kiosk 3',
      language: 'bg',
      order_type: 'kiosk',
      status: 'ordering',
      items: [
        { id: 1, name: 'Бургер Класик', quantity: 1, price: 9.50 },
      ],
      total: 9.50,
      started_at: new Date(Date.now() - 120000).toISOString(),
      last_interaction: new Date(Date.now() - 10000).toISOString(),
      messages: [
        { id: 1, role: 'assistant', content: 'Добре дошли! Какво бихте желали да поръчате?', timestamp: new Date(Date.now() - 120000).toISOString() },
        { id: 2, role: 'user', content: 'Искам бургер', timestamp: new Date(Date.now() - 100000).toISOString(), intent: 'order_item', entities: [{ type: 'menu_item', value: 'бургер', start: 6, end: 12 }], confidence: 0.91 },
        { id: 3, role: 'assistant', content: 'Добър избор! Какъв бургер бихте предпочели?', timestamp: new Date(Date.now() - 95000).toISOString() },
      ],
      context: {
        current_intent: 'clarify_item',
        slot_values: { order_type: 'kiosk' },
        awaiting_confirmation: true,
        last_entity_type: 'menu_item',
      },
    },
    {
      session_id: 'conv-003',
      customer_name: 'Delivery - Maria',
      language: 'en',
      order_type: 'delivery',
      status: 'checkout',
      items: [
        { id: 1, name: 'Family Pizza', quantity: 1, price: 22.00 },
        { id: 2, name: 'Garlic Bread', quantity: 2, price: 6.00 },
        { id: 3, name: 'Tiramisu', quantity: 1, price: 7.50 },
      ],
      total: 35.50,
      started_at: new Date(Date.now() - 600000).toISOString(),
      last_interaction: new Date(Date.now() - 60000).toISOString(),
      messages: [
        { id: 1, role: 'assistant', content: 'Your order total is 35.50 лв. Please confirm your delivery address.', timestamp: new Date(Date.now() - 65000).toISOString() },
        { id: 2, role: 'user', content: 'Yes, deliver to ul. Vitosha 45', timestamp: new Date(Date.now() - 60000).toISOString(), intent: 'confirm_address', entities: [{ type: 'address', value: 'ul. Vitosha 45', start: 17, end: 31 }], confidence: 0.97 },
      ],
      context: {
        current_intent: 'payment',
        slot_values: { address: 'ul. Vitosha 45', phone: '+359888123456' },
        awaiting_confirmation: true,
      },
    },
  ];

  const getMockIntents = (): Intent[] => [
    {
      name: 'order_item',
      description: 'Customer wants to add an item to their order',
      examples: ['I want a pizza', 'Can I get two beers', 'Add nachos to my order', 'Give me the burger'],
      slots: ['menu_item', 'quantity', 'size', 'modifiers'],
      response_templates: [
        'Added {quantity}x {menu_item} to your order.',
        'Great choice! I\'ve added {menu_item} for you.',
      ],
    },
    {
      name: 'remove_item',
      description: 'Customer wants to remove an item from their order',
      examples: ['Remove the pizza', 'Take off the salad', 'Cancel the beer', 'I don\'t want the burger anymore'],
      slots: ['menu_item'],
      response_templates: ['Removed {menu_item} from your order.', 'No problem, I\'ve removed {menu_item}.'],
    },
    {
      name: 'modify_item',
      description: 'Customer wants to modify an existing item',
      examples: ['Make it extra spicy', 'No onions please', 'Add cheese', 'With extra sauce'],
      slots: ['menu_item', 'modifier', 'modifier_action'],
      response_templates: ['I\'ve updated your order: {modifier} for {menu_item}.'],
    },
    {
      name: 'view_order',
      description: 'Customer wants to see their current order',
      examples: ['What\'s in my order?', 'Show me my order', 'What have I ordered?', 'Review my cart'],
      slots: [],
      response_templates: ['Here\'s your current order: {order_summary}. Total: {total}.'],
    },
    {
      name: 'checkout',
      description: 'Customer wants to complete their order and pay',
      examples: ['I\'m ready to pay', 'That\'s all', 'Checkout please', 'I want to complete my order'],
      slots: ['payment_method'],
      response_templates: ['Your total is {total}. How would you like to pay?'],
    },
    {
      name: 'view_menu',
      description: 'Customer wants to see the menu or recommendations',
      examples: ['What do you have?', 'Show me the menu', 'What\'s popular?', 'Any recommendations?'],
      slots: ['category'],
      response_templates: ['Here are our popular items: {menu_items}. Would you like to order any of these?'],
    },
    {
      name: 'ask_price',
      description: 'Customer asks about the price of an item',
      examples: ['How much is the pizza?', 'What\'s the price of beer?', 'Cost of salad?'],
      slots: ['menu_item'],
      response_templates: ['{menu_item} costs {price}. Would you like to add it?'],
    },
    {
      name: 'dietary_info',
      description: 'Customer asks about dietary information',
      examples: ['Is it vegan?', 'Does it contain nuts?', 'Gluten free options?', 'What\'s vegetarian?'],
      slots: ['menu_item', 'dietary_restriction'],
      response_templates: ['{menu_item} {dietary_info}. Would you like alternatives?'],
    },
  ];

  const getMockTrainingExamples = (): TrainingExample[] => [
    { id: 1, text: 'I would like a large pepperoni pizza', intent: 'order_item', entities: [{ type: 'size', value: 'large', start: 15, end: 20 }, { type: 'menu_item', value: 'pepperoni pizza', start: 21, end: 36 }], verified: true, added_at: '2024-12-20' },
    { id: 2, text: 'Can you add two beers to my order?', intent: 'order_item', entities: [{ type: 'quantity', value: '2', start: 12, end: 15 }, { type: 'menu_item', value: 'beers', start: 16, end: 21 }], verified: true, added_at: '2024-12-20' },
    { id: 3, text: 'Actually, remove the nachos', intent: 'remove_item', entities: [{ type: 'menu_item', value: 'nachos', start: 20, end: 26 }], verified: true, added_at: '2024-12-21' },
    { id: 4, text: 'Make the burger without pickles', intent: 'modify_item', entities: [{ type: 'menu_item', value: 'burger', start: 9, end: 15 }, { type: 'modifier', value: 'without pickles', start: 16, end: 31 }], verified: true, added_at: '2024-12-21' },
    { id: 5, text: 'What vegetarian options do you have?', intent: 'dietary_info', entities: [{ type: 'dietary_restriction', value: 'vegetarian', start: 5, end: 15 }], verified: false, added_at: '2024-12-22' },
    { id: 6, text: 'I\'m done, let me pay', intent: 'checkout', entities: [], verified: true, added_at: '2024-12-22' },
  ];

  const languageStats: LanguageStats[] = [
    { code: 'en', name: 'English', flag: '🇬🇧', sessions: 245, accuracy: 96.2 },
    { code: 'bg', name: 'Bulgarian', flag: '🇧🇬', sessions: 189, accuracy: 94.8 },
    { code: 'de', name: 'German', flag: '🇩🇪', sessions: 45, accuracy: 91.5 },
    { code: 'ru', name: 'Russian', flag: '🇷🇺', sessions: 32, accuracy: 89.3 },
  ];

  const handleTestInput = async () => {
    if (!testInput.trim()) return;

    setIsProcessing(true);

    // Add user message
    const userMessage: ConversationMessage = {
      id: testMessages.length + 1,
      role: 'user',
      content: testInput,
      timestamp: new Date().toISOString(),
    };
    setTestMessages([...testMessages, userMessage]);
    setTestInput('');

    // Simulate NLU processing
    await new Promise(resolve => setTimeout(resolve, 500));

    // Detect intent and entities (simulated)
    const { intent, entities, confidence, response } = simulateNLU(testInput, testLanguage);

    // Add detected metadata to user message
    userMessage.intent = intent;
    userMessage.entities = entities;
    userMessage.confidence = confidence;

    // Add assistant response
    const assistantMessage: ConversationMessage = {
      id: testMessages.length + 2,
      role: 'assistant',
      content: response,
      timestamp: new Date().toISOString(),
    };

    setTestMessages(prev => [...prev.slice(0, -1), userMessage, assistantMessage]);
    setIsProcessing(false);
  };

  const simulateNLU = (input: string, lang: string) => {
    const lowerInput = input.toLowerCase();

    if (lowerInput.includes('pizza') || lowerInput.includes('burger') || lowerInput.includes('beer') || lowerInput.includes('бургер')) {
      const itemMatch = lowerInput.match(/(pizza|burger|beer|salad|nachos|бургер|бира)/);
      const quantityMatch = lowerInput.match(/(\d+|two|three|four|five)/);
      return {
        intent: 'order_item',
        entities: [
          { type: 'menu_item', value: itemMatch?.[1] || 'item', start: 0, end: 5 },
          ...(quantityMatch ? [{ type: 'quantity', value: quantityMatch[1], start: 0, end: 3 }] : []),
        ],
        confidence: 0.94,
        response: lang === 'bg'
          ? `Добавих ${itemMatch?.[1] || 'артикула'} към вашата поръчка. Нещо друго?`
          : `I've added ${itemMatch?.[1] || 'the item'} to your order. Anything else?`,
      };
    }

    if (lowerInput.includes('menu') || lowerInput.includes('what do you have') || lowerInput.includes('меню')) {
      return {
        intent: 'view_menu',
        entities: [],
        confidence: 0.97,
        response: lang === 'bg'
          ? 'Предлагаме пици, бургери, салати и напитки. Какво бихте желали?'
          : 'We have pizzas, burgers, salads, and drinks. What would you like?',
      };
    }

    if (lowerInput.includes('pay') || lowerInput.includes('checkout') || lowerInput.includes('done') || lowerInput.includes('плащам')) {
      return {
        intent: 'checkout',
        entities: [],
        confidence: 0.96,
        response: lang === 'bg'
          ? 'Вашата поръчка е готова. Как бихте желали да платите?'
          : 'Your order is ready. How would you like to pay?',
      };
    }

    if (lowerInput.includes('remove') || lowerInput.includes('cancel') || lowerInput.includes('махни')) {
      return {
        intent: 'remove_item',
        entities: [],
        confidence: 0.89,
        response: lang === 'bg'
          ? 'Кой артикул бихте желали да премахна?'
          : 'Which item would you like me to remove?',
      };
    }

    return {
      intent: 'unknown',
      entities: [],
      confidence: 0.45,
      response: lang === 'bg'
        ? 'Съжалявам, не разбрах. Можете да кажете какво искате да поръчате.'
        : 'I\'m sorry, I didn\'t understand that. Could you tell me what you\'d like to order?',
    };
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-500',
      ordering: 'bg-blue-500',
      checkout: 'bg-yellow-500',
      completed: 'bg-gray-500',
      abandoned: 'bg-red-500',
    };
    return colors[status] || 'bg-gray-500';
  };

  const getLanguageFlag = (lang: string) => {
    const flags: Record<string, string> = {
      en: '🇬🇧',
      bg: '🇧🇬',
      de: '🇩🇪',
      ru: '🇷🇺',
      fr: '🇫🇷',
      es: '🇪🇸',
    };
    return flags[lang] || '🌐';
  };

  const stats = {
    activeSessions: sessions.filter(s => s.status === 'active' || s.status === 'ordering').length,
    totalToday: 156,
    avgResponseTime: '0.8s',
    successRate: 94.2,
    intentAccuracy: 92.5,
    entityAccuracy: 89.8,
    completedOrders: 142,
    abandonedRate: 8.9,
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading NLU Engine...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Conversational Ordering</h1>
            <p className="text-gray-600 mt-1">NLU-powered natural language ordering system</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowIntentModal(true)}
              className="px-4 py-2 bg-purple-500 text-gray-900 rounded-xl hover:bg-purple-600"
            >
              + New Intent
            </button>
            <button
              onClick={() => setShowTrainingModal(true)}
              className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600"
            >
              + Add Training Data
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Active Sessions</div>
            <div className="text-2xl font-bold text-green-400">{stats.activeSessions}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Today Total</div>
            <div className="text-2xl font-bold text-gray-900">{stats.totalToday}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Response Time</div>
            <div className="text-2xl font-bold text-blue-400">{stats.avgResponseTime}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Success Rate</div>
            <div className="text-2xl font-bold text-green-400">{stats.successRate}%</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Intent Accuracy</div>
            <div className="text-2xl font-bold text-purple-400">{stats.intentAccuracy}%</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Entity Accuracy</div>
            <div className="text-2xl font-bold text-cyan-400">{stats.entityAccuracy}%</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Completed</div>
            <div className="text-2xl font-bold text-emerald-400">{stats.completedOrders}</div>
          </div>
          <div className="bg-gray-100 rounded-xl p-4">
            <div className="text-gray-600 text-xs">Abandoned</div>
            <div className="text-2xl font-bold text-red-400">{stats.abandonedRate}%</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: '📊' },
            { id: 'sessions', label: 'Active Sessions', icon: '💬' },
            { id: 'intents', label: 'Intent Library', icon: '🎯' },
            { id: 'training', label: 'Training Data', icon: '🧠' },
            { id: 'testing', label: 'Test Console', icon: '🧪' },
            { id: 'analytics', label: 'Analytics', icon: '📈' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-xl whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' && (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Recent Sessions */}
                <div className="lg:col-span-2 bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Conversations</h2>
                  <div className="space-y-3">
                    {sessions.slice(0, 5).map(session => (
                      <div
                        key={session.session_id}
                        className="bg-gray-50 rounded-xl p-4 cursor-pointer hover:bg-gray-100 transition-all"
                        onClick={() => setSelectedSession(session)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{getLanguageFlag(session.language)}</span>
                            <span className="text-gray-900 font-semibold">{session.customer_name}</span>
                            <span className={`px-2 py-0.5 rounded-full text-xs ${getStatusColor(session.status)} text-white`}>
                              {session.status}
                            </span>
                          </div>
                          <span className="text-white/40 text-sm">
                            {new Date(session.last_interaction).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="text-gray-600 text-sm mb-2">
                          {session.messages[session.messages.length - 1]?.content.slice(0, 60)}...
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-500 text-xs">{session.items.length} items</span>
                          <span className="text-green-400 font-semibold">{session.total.toFixed(2)} лв</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Language Stats */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Language Performance</h2>
                  <div className="space-y-4">
                    {languageStats.map(lang => (
                      <div key={lang.code} className="bg-gray-50 rounded-xl p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">{lang.flag}</span>
                            <span className="text-gray-900 font-semibold">{lang.name}</span>
                          </div>
                          <span className="text-gray-500 text-sm">{lang.sessions} sessions</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-green-500 to-emerald-400"
                              style={{ width: `${lang.accuracy}%` }}
                            ></div>
                          </div>
                          <span className="text-green-400 text-sm font-semibold">{lang.accuracy}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Intent Performance */}
              <div className="mt-6 bg-gray-100 rounded-2xl p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Intent Recognition Performance</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {intents.slice(0, 4).map(intent => (
                    <div key={intent.name} className="bg-gray-50 rounded-xl p-4">
                      <div className="text-gray-900 font-semibold mb-1">{intent.name.replace('_', ' ')}</div>
                      <div className="text-gray-500 text-xs mb-2">{intent.examples.length} examples</div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
                            style={{ width: `${85 + Math.random() * 12}%` }}
                          ></div>
                        </div>
                        <span className="text-purple-400 text-xs">{(85 + Math.random() * 12).toFixed(1)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'sessions' && (
            <motion.div
              key="sessions"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="grid grid-cols-1 lg:grid-cols-2 gap-6"
            >
              {/* Sessions List */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Active Sessions</h2>
                <div className="space-y-3">
                  {sessions.map(session => (
                    <div
                      key={session.session_id}
                      className={`rounded-xl p-4 cursor-pointer transition-all ${
                        selectedSession?.session_id === session.session_id
                          ? 'bg-orange-500/20 border border-orange-500'
                          : 'bg-gray-50 hover:bg-white/10'
                      }`}
                      onClick={() => setSelectedSession(session)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{getLanguageFlag(session.language)}</span>
                          <span className="text-gray-900 font-semibold">{session.customer_name}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${getStatusColor(session.status)} text-white`}>
                          {session.status}
                        </span>
                      </div>
                      <div className="text-gray-500 text-sm">{session.order_type} • {session.items.length} items</div>
                      <div className="text-green-400 font-semibold mt-1">{session.total.toFixed(2)} лв</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Session Detail */}
              {selectedSession ? (
                <div className="bg-gray-100 rounded-2xl p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold text-gray-900">Conversation</h2>
                    <button
                      onClick={() => setSelectedSession(null)}
                      className="text-gray-600 hover:text-gray-900"
                    >
                      ×
                    </button>
                  </div>

                  {/* Messages */}
                  <div className="h-96 overflow-y-auto space-y-3 mb-4">
                    {selectedSession.messages.map(msg => (
                      <div
                        key={msg.id}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-[80%] rounded-2xl p-3 ${
                          msg.role === 'user'
                            ? 'bg-orange-500 text-white'
                            : 'bg-gray-100 text-gray-900'
                        }`}>
                          <div>{msg.content}</div>
                          {msg.intent && (
                            <div className="mt-2 pt-2 border-t border-gray-300 text-xs">
                              <span className="bg-purple-500/50 px-2 py-0.5 rounded">{msg.intent}</span>
                              {msg.confidence && (
                                <span className="ml-2 text-gray-600">{(msg.confidence * 100).toFixed(0)}%</span>
                              )}
                              {msg.entities && msg.entities.length > 0 && (
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {msg.entities.map((e, i) => (
                                    <span key={i} className="bg-cyan-500/50 px-2 py-0.5 rounded">
                                      {e.type}: {e.value}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Order Summary */}
                  <div className="bg-gray-50 rounded-xl p-4">
                    <h3 className="text-gray-900 font-semibold mb-2">Current Order</h3>
                    <div className="space-y-2">
                      {selectedSession.items.map(item => (
                        <div key={item.id} className="flex justify-between text-sm">
                          <span className="text-gray-900">{item.quantity}x {item.name}</span>
                          <span className="text-gray-700">{item.price.toFixed(2)} лв</span>
                        </div>
                      ))}
                      <div className="border-t border-gray-200 pt-2 flex justify-between font-semibold">
                        <span className="text-gray-900">Total</span>
                        <span className="text-green-400">{selectedSession.total.toFixed(2)} лв</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-gray-100 rounded-2xl p-6 flex items-center justify-center">
                  <p className="text-white/40">Select a session to view details</p>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'intents' && (
            <motion.div
              key="intents"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {intents.map(intent => (
                  <div key={intent.name} className="bg-gray-100 rounded-2xl p-6">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">{intent.name.replace('_', ' ')}</h3>
                        <p className="text-gray-600 text-sm">{intent.description}</p>
                      </div>
                      <button className="text-orange-400 hover:text-orange-300 text-sm">Edit</button>
                    </div>

                    <div className="mb-3">
                      <div className="text-gray-500 text-xs mb-1">Example phrases:</div>
                      <div className="flex flex-wrap gap-1">
                        {intent.examples.slice(0, 3).map((ex, i) => (
                          <span key={i} className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
                            &quot;{ex}&quot;
                          </span>
                        ))}
                        {intent.examples.length > 3 && (
                          <span className="px-2 py-1 text-gray-500 text-xs">
                            +{intent.examples.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="mb-3">
                      <div className="text-gray-500 text-xs mb-1">Required slots:</div>
                      <div className="flex flex-wrap gap-1">
                        {intent.slots.map((slot, i) => (
                          <span key={i} className="px-2 py-1 bg-purple-500/30 text-purple-300 rounded text-xs">
                            {slot}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="text-gray-500 text-xs mb-1">Response template:</div>
                      <div className="text-gray-700 text-sm italic">
                        &quot;{intent.response_templates[0]}&quot;
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === 'training' && (
            <motion.div
              key="training"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="bg-gray-100 rounded-2xl overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-4 text-left text-gray-900">Example Text</th>
                      <th className="px-6 py-4 text-left text-gray-900">Intent</th>
                      <th className="px-6 py-4 text-left text-gray-900">Entities</th>
                      <th className="px-6 py-4 text-center text-gray-900">Verified</th>
                      <th className="px-6 py-4 text-center text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trainingExamples.map(example => (
                      <tr key={example.id} className="border-t border-gray-200">
                        <td className="px-6 py-4 text-gray-900">{example.text}</td>
                        <td className="px-6 py-4">
                          <span className="px-2 py-1 bg-purple-500/30 text-purple-300 rounded text-sm">
                            {example.intent}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap gap-1">
                            {example.entities.map((e, i) => (
                              <span key={i} className="px-2 py-1 bg-cyan-500/30 text-cyan-300 rounded text-xs">
                                {e.type}: {e.value}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-center">
                          {example.verified ? (
                            <span className="text-green-400">✓</span>
                          ) : (
                            <span className="text-yellow-400">○</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex justify-center gap-2">
                            <button className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded text-sm hover:bg-blue-500/30">
                              Edit
                            </button>
                            <button className="px-3 py-1 bg-red-500/20 text-red-400 rounded text-sm hover:bg-red-500/30">
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-6 flex justify-between items-center">
                <div className="text-gray-600">
                  {trainingExamples.length} examples • {trainingExamples.filter(e => e.verified).length} verified
                </div>
                <div className="flex gap-3">
                  <button className="px-4 py-2 bg-blue-500 text-gray-900 rounded-xl hover:bg-blue-600">
                    Import from CSV
                  </button>
                  <button className="px-4 py-2 bg-green-500 text-gray-900 rounded-xl hover:bg-green-600">
                    Train Model
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'testing' && (
            <motion.div
              key="testing"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="grid grid-cols-1 lg:grid-cols-2 gap-6"
            >
              {/* Test Console */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold text-gray-900">Test Console</h2>
                  <select
                    value={testLanguage}
                    onChange={(e) => setTestLanguage(e.target.value)}
                    className="px-3 py-2 bg-gray-100 text-gray-900 rounded-lg"
                  >
                    <option value="en">🇬🇧 English</option>
                    <option value="bg">🇧🇬 Bulgarian</option>
                    <option value="de">🇩🇪 German</option>
                    <option value="ru">🇷🇺 Russian</option>
                  </select>
                </div>

                {/* Chat Window */}
                <div className="h-96 bg-gray-50 rounded-xl p-4 overflow-y-auto mb-4">
                  {testMessages.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-white/40">
                      Start a test conversation...
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {testMessages.map(msg => (
                        <div
                          key={msg.id}
                          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div className={`max-w-[80%] rounded-2xl p-3 ${
                            msg.role === 'user'
                              ? 'bg-orange-500 text-white'
                              : 'bg-gray-100 text-gray-900'
                          }`}>
                            <div>{msg.content}</div>
                            {msg.intent && (
                              <div className="mt-2 pt-2 border-t border-gray-300 text-xs">
                                <span className={`px-2 py-0.5 rounded ${
                                  msg.intent === 'unknown' ? 'bg-red-500/50' : 'bg-purple-500/50'
                                }`}>
                                  {msg.intent}
                                </span>
                                {msg.confidence && (
                                  <span className={`ml-2 ${
                                    msg.confidence > 0.8 ? 'text-green-400' : msg.confidence > 0.5 ? 'text-yellow-400' : 'text-red-400'
                                  }`}>
                                    {(msg.confidence * 100).toFixed(0)}% confidence
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                      {isProcessing && (
                        <div className="flex justify-start">
                          <div className="bg-gray-100 rounded-2xl p-3 text-gray-600">
                            Thinking...
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </div>
                  )}
                </div>

                {/* Input */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={testInput}
                    onChange={(e) => setTestInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleTestInput()}
                    placeholder="Type a message..."
                    className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-xl focus:ring-2 focus:ring-orange-500"
                  />
                  <button
                    onClick={handleTestInput}
                    disabled={isProcessing}
                    className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600 disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>

                <button
                  onClick={() => setTestMessages([])}
                  className="mt-2 text-gray-500 text-sm hover:text-gray-700"
                >
                  Clear conversation
                </button>
              </div>

              {/* Sample Phrases */}
              <div className="bg-gray-100 rounded-2xl p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Sample Phrases</h2>
                <div className="space-y-3">
                  {[
                    { lang: 'en', phrases: ['I want a large pizza', 'Two beers please', 'What do you have?', 'Remove the salad', 'I want to pay'] },
                    { lang: 'bg', phrases: ['Искам голяма пица', 'Две бири моля', 'Какво имате?', 'Махни салатата', 'Искам да платя'] },
                  ].map(group => (
                    <div key={group.lang} className="bg-gray-50 rounded-xl p-4">
                      <div className="text-gray-900 font-semibold mb-2">{getLanguageFlag(group.lang)} {group.lang.toUpperCase()}</div>
                      <div className="space-y-2">
                        {group.phrases.map((phrase, i) => (
                          <button
                            key={i}
                            onClick={() => {
                              setTestInput(phrase);
                              setTestLanguage(group.lang);
                            }}
                            className="block w-full text-left px-3 py-2 bg-gray-100 text-gray-800 rounded hover:bg-gray-200 text-sm"
                          >
                            &quot;{phrase}&quot;
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'analytics' && (
            <motion.div
              key="analytics"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Intent Distribution */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Intent Distribution</h3>
                  <div className="space-y-3">
                    {[
                      { intent: 'order_item', count: 856, color: 'bg-green-500' },
                      { intent: 'view_menu', count: 234, color: 'bg-blue-500' },
                      { intent: 'checkout', count: 198, color: 'bg-purple-500' },
                      { intent: 'modify_item', count: 145, color: 'bg-yellow-500' },
                      { intent: 'remove_item', count: 89, color: 'bg-red-500' },
                    ].map(item => (
                      <div key={item.intent}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-900">{item.intent.replace('_', ' ')}</span>
                          <span className="text-gray-700">{item.count}</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.color}`}
                            style={{ width: `${(item.count / 856) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Hourly Activity */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Hourly Activity</h3>
                  <div className="flex items-end justify-between h-40">
                    {Array.from({ length: 12 }, (_, i) => {
                      const hour = i + 10;
                      const height = [20, 35, 55, 80, 65, 90, 95, 75, 85, 60, 40, 25][i];
                      return (
                        <div key={i} className="flex flex-col items-center">
                          <div
                            className="w-5 bg-gradient-to-t from-orange-500 to-yellow-400 rounded-t"
                            style={{ height: `${height}%` }}
                          ></div>
                          <div className="text-gray-500 text-xs mt-1">{hour}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Entity Extraction */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Entity Types</h3>
                  <div className="space-y-3">
                    {[
                      { type: 'menu_item', accuracy: 94.5, color: 'from-green-500 to-emerald-400' },
                      { type: 'quantity', accuracy: 97.2, color: 'from-blue-500 to-cyan-400' },
                      { type: 'modifier', accuracy: 88.3, color: 'from-purple-500 to-pink-400' },
                      { type: 'size', accuracy: 92.1, color: 'from-yellow-500 to-orange-400' },
                    ].map(entity => (
                      <div key={entity.type} className="flex items-center gap-3">
                        <div className="flex-1">
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-900">{entity.type}</span>
                            <span className="text-green-400">{entity.accuracy}%</span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full bg-gradient-to-r ${entity.color}`}
                              style={{ width: `${entity.accuracy}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Error Analysis */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Common Errors</h3>
                  <div className="space-y-3">
                    {[
                      { error: 'Unclear quantity', count: 23, example: '"Give me some beers"' },
                      { error: 'Ambiguous item', count: 18, example: '"I want the special"' },
                      { error: 'Unknown modifier', count: 12, example: '"Make it Bulgarian style"' },
                      { error: 'Mixed language', count: 8, example: '"Искам pizza"' },
                    ].map((err, i) => (
                      <div key={i} className="bg-gray-50 rounded-xl p-3">
                        <div className="flex justify-between mb-1">
                          <span className="text-gray-900 text-sm">{err.error}</span>
                          <span className="text-red-400 text-sm">{err.count} times</span>
                        </div>
                        <div className="text-gray-500 text-xs italic">{err.example}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Response Time Distribution */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Response Time</h3>
                  <div className="text-center mb-4">
                    <div className="text-4xl font-bold text-green-400">0.8s</div>
                    <div className="text-gray-500">Average</div>
                  </div>
                  <div className="space-y-2">
                    {[
                      { range: '< 0.5s', percent: 45 },
                      { range: '0.5 - 1s', percent: 38 },
                      { range: '1 - 2s', percent: 12 },
                      { range: '> 2s', percent: 5 },
                    ].map(item => (
                      <div key={item.range}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-700">{item.range}</span>
                          <span className="text-gray-900">{item.percent}%</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-cyan-500 to-blue-400"
                            style={{ width: `${item.percent}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Conversation Outcomes */}
                <div className="bg-gray-100 rounded-2xl p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">Conversation Outcomes</h3>
                  <div className="flex items-center justify-center">
                    <div className="relative w-40 h-40">
                      <svg className="w-full h-full" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="12" />
                        <circle
                          cx="50"
                          cy="50"
                          r="40"
                          fill="none"
                          stroke="url(#gradient)"
                          strokeWidth="12"
                          strokeDasharray={`${91.1 * 2.51} ${100 * 2.51}`}
                          strokeLinecap="round"
                          transform="rotate(-90 50 50)"
                        />
                        <defs>
                          <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#22c55e" />
                            <stop offset="100%" stopColor="#10b981" />
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-bold text-gray-900">91.1%</span>
                        <span className="text-gray-500 text-xs">Success</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-center text-sm">
                    <div className="bg-green-500/20 rounded-lg p-2">
                      <div className="text-green-400 font-bold">142</div>
                      <div className="text-gray-500">Completed</div>
                    </div>
                    <div className="bg-red-500/20 rounded-lg p-2">
                      <div className="text-red-400 font-bold">14</div>
                      <div className="text-gray-500">Abandoned</div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* New Intent Modal */}
        {showIntentModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Create New Intent</h2>
                <button onClick={() => setShowIntentModal(false)} className="text-gray-600 hover:text-gray-900 text-2xl">×</button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-600 text-sm">Intent Name</label>
                  <input
                    type="text"
                    value={newIntent.name}
                    onChange={(e) => setNewIntent({ ...newIntent, name: e.target.value })}
                    placeholder="e.g., ask_allergy"
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                  />
                </div>

                <div>
                  <label className="text-gray-600 text-sm">Description</label>
                  <input
                    type="text"
                    value={newIntent.description}
                    onChange={(e) => setNewIntent({ ...newIntent, description: e.target.value })}
                    placeholder="What does this intent represent?"
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                  />
                </div>

                <div>
                  <label className="text-gray-600 text-sm">Example Phrases</label>
                  {newIntent.examples.map((ex, i) => (
                    <div key={i} className="flex gap-2 mt-1">
                      <input
                        type="text"
                        value={ex}
                        onChange={(e) => {
                          const examples = [...newIntent.examples];
                          examples[i] = e.target.value;
                          setNewIntent({ ...newIntent, examples });
                        }}
                        placeholder="Example phrase..."
                        className="flex-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      />
                      {i === newIntent.examples.length - 1 && (
                        <button
                          onClick={() => setNewIntent({ ...newIntent, examples: [...newIntent.examples, ''] })}
                          className="px-4 py-2 bg-green-500/20 text-green-400 rounded-xl"
                        >
                          +
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                <div>
                  <label className="text-gray-600 text-sm">Required Slots</label>
                  {newIntent.slots.map((slot, i) => (
                    <div key={i} className="flex gap-2 mt-1">
                      <input
                        type="text"
                        value={slot}
                        onChange={(e) => {
                          const slots = [...newIntent.slots];
                          slots[i] = e.target.value;
                          setNewIntent({ ...newIntent, slots });
                        }}
                        placeholder="Slot name..."
                        className="flex-1 px-4 py-2 bg-gray-100 text-gray-900 rounded-xl"
                      />
                      {i === newIntent.slots.length - 1 && (
                        <button
                          onClick={() => setNewIntent({ ...newIntent, slots: [...newIntent.slots, ''] })}
                          className="px-4 py-2 bg-purple-500/20 text-purple-400 rounded-xl"
                        >
                          +
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setShowIntentModal(false)}
                    className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      setIntents([...intents, { ...newIntent, response_templates: [] }]);
                      setShowIntentModal(false);
                      setNewIntent({ name: '', description: '', examples: [''], slots: [''], response_templates: [''] });
                    }}
                    className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl"
                  >
                    Create Intent
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {/* Training Data Modal */}
        {showTrainingModal && (
          <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-gray-50 rounded-2xl p-6 max-w-xl w-full"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Add Training Example</h2>
                <button onClick={() => setShowTrainingModal(false)} className="text-gray-600 hover:text-gray-900 text-2xl">×</button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-gray-600 text-sm">Example Text</label>
                  <input
                    type="text"
                    value={newExample.text}
                    onChange={(e) => setNewExample({ ...newExample, text: e.target.value })}
                    placeholder="Enter a sample user phrase..."
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                  />
                </div>

                <div>
                  <label className="text-gray-600 text-sm">Intent</label>
                  <select
                    value={newExample.intent}
                    onChange={(e) => setNewExample({ ...newExample, intent: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-100 text-gray-900 rounded-xl mt-1"
                  >
                    <option value="">Select intent...</option>
                    {intents.map(intent => (
                      <option key={intent.name} value={intent.name}>{intent.name}</option>
                    ))}
                  </select>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setShowTrainingModal(false)}
                    className="flex-1 py-3 bg-gray-100 text-gray-900 rounded-xl"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      setTrainingExamples([
                        ...trainingExamples,
                        {
                          id: trainingExamples.length + 1,
                          text: newExample.text,
                          intent: newExample.intent,
                          entities: [],
                          verified: false,
                          added_at: new Date().toISOString().split('T')[0],
                        },
                      ]);
                      setShowTrainingModal(false);
                      setNewExample({ text: '', intent: '', entities: [] });
                    }}
                    className="flex-1 py-3 bg-green-500 text-gray-900 rounded-xl"
                  >
                    Add Example
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}

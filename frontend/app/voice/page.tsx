"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { api, isAuthenticated } from "@/lib/api";

interface VoiceCommand {
  id: number;
  text: string;
  intent: string;
  confidence: number;
  response: string;
  timestamp: Date;
  status: "success" | "error" | "pending";
}

interface VoiceIntent {
  intent: string;
  examples: string[];
  description: string;
  icon: string;
}

export default function VoiceAssistantPage() {
  const router = useRouter();
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [commands, setCommands] = useState<VoiceCommand[]>([]);
  const [currentResponse, setCurrentResponse] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [language] = useState("en-US");
  const [showHelp, setShowHelp] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  const recognitionRef = useRef<any>(null);

  // Check authentication on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    setAuthChecked(true);
  }, [router]);

  const voiceIntents: VoiceIntent[] = [
    {
      intent: "check_order_status",
      examples: ["What's the status of order 5?", "Check order 12"],
      description: "Check order status",
      icon: "📋",
    },
    {
      intent: "mark_order_ready",
      examples: ["Order 7 is ready", "Mark order 3 as ready"],
      description: "Mark order as ready",
      icon: "✅",
    },
    {
      intent: "call_waiter",
      examples: ["Call waiter to table 5", "Waiter to table 8"],
      description: "Call waiter to table",
      icon: "🙋",
    },
    {
      intent: "check_stock",
      examples: ["How much beer do we have?", "Check stock for potatoes"],
      description: "Check stock levels",
      icon: "📦",
    },
    {
      intent: "low_stock_alert",
      examples: ["What items are running low?", "Show low stock"],
      description: "Show low stock items",
      icon: "⚠️",
    },
    {
      intent: "today_summary",
      examples: ["Summary for today", "How many orders today?"],
      description: "Today's summary",
      icon: "📊",
    },
    {
      intent: "pending_orders",
      examples: ["How many pending orders?", "Show new orders"],
      description: "Show pending orders",
      icon: "⏳",
    },
    {
      intent: "table_status",
      examples: ["Status of table 3", "What's on table 7?"],
      description: "Check table status",
      icon: "🪑",
    },
    {
      intent: "cancel_order",
      examples: ["Cancel order 9", "Delete order 4"],
      description: "Cancel an order",
      icon: "❌",
    },
    {
      intent: "tips_today",
      examples: ["How much tips today?", "Show today's tips"],
      description: "Show today's tips",
      icon: "💰",
    },
    {
      intent: "help",
      examples: ["Help", "What can you do?"],
      description: "Get help",
      icon: "❓",
    },
  ];

  useEffect(() => {
    // Initialize speech recognition
    if (typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = language;

      recognitionRef.current.onresult = (event: any) => {
        let finalTranscript = "";
        let interimTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        setTranscript(interimTranscript || finalTranscript);

        if (finalTranscript) {
          processCommand(finalTranscript);
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        if (isListening) {
          recognitionRef.current.start();
        }
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
      setTranscript("");
    }
  };

  const processCommand = async (text: string) => {
    setIsProcessing(true);
    setTranscript("");

    const newCommand: VoiceCommand = {
      id: Date.now(),
      text,
      intent: "",
      confidence: 0,
      response: "",
      timestamp: new Date(),
      status: "pending",
    };

    setCommands((prev) => [newCommand, ...prev]);

    try {
      const data = await api.post<{ intent: string; confidence: number; response: string }>(
        '/voice/command',
        { command_text: text, language }
      );

      updateCommand(newCommand.id, {
        intent: data.intent,
        confidence: data.confidence,
        response: data.response,
        status: "success",
      });
      setCurrentResponse(data.response);
      speak(data.response);
    } catch (error) {
      console.error("Voice command error:", error);
      const errorMessage = "Sorry, I couldn't process that command. Please try again.";
      updateCommand(newCommand.id, {
        intent: "error",
        confidence: 0,
        response: errorMessage,
        status: "error",
      });
      setCurrentResponse(errorMessage);
      speak(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  const updateCommand = (id: number, updates: Partial<VoiceCommand>) => {
    setCommands((prev) =>
      prev.map((cmd) => (cmd.id === id ? { ...cmd, ...updates } : cmd))
    );
  };

  const speak = (text: string) => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = language;
      utterance.rate = 1;
      speechSynthesis.speak(utterance);
    }
  };

  const handleTextCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (transcript.trim()) {
      processCommand(transcript);
    }
  };

  // Show loading until auth is checked
  if (!authChecked) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-900 text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            <a href="/dashboard" className="text-gray-600 hover:text-gray-900 text-2xl">←</a>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">🎤 Voice Assistant</h1>
              <p className="text-gray-600 mt-1">Hands-free kitchen & bar control</p>
            </div>
          </div>
          <button
            onClick={() => setShowHelp(!showHelp)}
            className="px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200"
          >
            ❓ Help
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Voice Interface */}
          <div className="lg:col-span-2 space-y-6">
            {/* Voice Control */}
            <motion.div
              className={`rounded-3xl p-8 text-center transition-all ${
                isListening
                  ? "bg-gradient-to-br from-green-500/20 to-emerald-600/20 border-2 border-green-500"
                  : "bg-gray-50 border border-gray-200"
              }`}
            >
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleListening}
                className={`w-32 h-32 rounded-full flex items-center justify-center text-5xl mx-auto mb-6 transition-all ${
                  isListening
                    ? "bg-green-500 animate-pulse shadow-lg shadow-green-500/50"
                    : "bg-orange-500 hover:bg-orange-600"
                }`}
              >
                {isListening ? "🎤" : "🎙️"}
              </motion.button>

              <div className="text-gray-900 text-xl mb-2">
                {isListening ? "Listening..." : "Tap to start"}
              </div>

              {transcript && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 bg-gray-100 rounded-xl text-gray-900"
                >
                  &quot;{transcript}&quot;
                </motion.div>
              )}

              {isProcessing && (
                <div className="mt-4 flex items-center justify-center gap-2 text-gray-700">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Processing...
                </div>
              )}

              {currentResponse && !isProcessing && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 bg-blue-500/20 rounded-xl text-blue-300 border border-blue-500/30"
                >
                  🤖 {currentResponse}
                </motion.div>
              )}

              {/* Text input fallback */}
              <form onSubmit={handleTextCommand} className="mt-6">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    placeholder="Or type a command..."
                    className="flex-1 px-4 py-3 bg-gray-100 text-gray-900 rounded-xl border border-gray-300 focus:border-orange-500 focus:outline-none"
                  />
                  <button
                    type="submit"
                    className="px-6 py-3 bg-orange-500 text-gray-900 rounded-xl hover:bg-orange-600"
                  >
                    Send
                  </button>
                </div>
              </form>
            </motion.div>

            {/* Command History */}
            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 mb-4">📝 Command History</h2>
              
              {commands.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No commands yet. Start speaking or type a command!
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  <AnimatePresence>
                    {commands.map((cmd) => (
                      <motion.div
                        key={cmd.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        className="p-4 bg-gray-50 rounded-xl"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-2">
                            <span
                              className={`w-2 h-2 rounded-full ${
                                cmd.status === "success"
                                  ? "bg-green-500"
                                  : cmd.status === "error"
                                  ? "bg-red-500"
                                  : "bg-yellow-500"
                              }`}
                            />
                            <span className="text-gray-900 font-medium">
                              &quot;{cmd.text}&quot;
                            </span>
                          </div>
                          <span className="text-white/40 text-xs">
                            {cmd.timestamp.toLocaleTimeString()}
                          </span>
                        </div>
                        
                        {cmd.intent && (
                          <div className="flex items-center gap-2 mb-2">
                            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                              {cmd.intent}
                            </span>
                            <span className="text-gray-500 text-xs">
                              {((cmd.confidence * 100) || 0).toFixed(0)}% confidence
                            </span>
                          </div>
                        )}
                        
                        {cmd.response && (
                          <div className="text-gray-700 text-sm">
                            🤖 {cmd.response}
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </div>
          </div>

          {/* Help Panel */}
          <div className="space-y-6">
            <AnimatePresence>
              {showHelp && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-gray-50 rounded-2xl p-6 border border-gray-200"
                >
                  <h2 className="text-xl font-bold text-gray-900 mb-4">
                    🎯 Available Commands
                  </h2>
                  <div className="space-y-3 max-h-[500px] overflow-y-auto">
                    {voiceIntents.map((intent) => (
                      <div
                        key={intent.intent}
                        className="p-3 bg-gray-50 rounded-xl"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xl">{intent.icon}</span>
                          <span className="text-gray-900 font-medium">
                            {intent.description}
                          </span>
                        </div>
                        <div className="text-gray-500 text-sm">
                          {intent.examples[0]}
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Quick Actions */}
            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 mb-4">⚡ Quick Actions</h2>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { text: "Today's summary", icon: "📊" },
                  { text: "Pending orders", icon: "⏳" },
                  { text: "Today's tips", icon: "💰" },
                  { text: "Low stock", icon: "⚠️" },
                ].map((action) => (
                  <button
                    key={action.text}
                    onClick={() => processCommand(action.text)}
                    className="p-3 bg-gray-50 hover:bg-gray-100 rounded-xl text-left transition-all"
                  >
                    <span className="text-2xl">{action.icon}</span>
                    <div className="text-gray-900 text-sm mt-1">{action.text}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Status */}
            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 mb-4">📡 Status</h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">Speech Recognition</span>
                  <span
                    className={`px-2 py-1 rounded text-xs ${
                      "webkitSpeechRecognition" in window
                        ? "bg-green-500/20 text-green-400"
                        : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {"webkitSpeechRecognition" in window ? "Available" : "Unavailable"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">Text-to-Speech</span>
                  <span
                    className={`px-2 py-1 rounded text-xs ${
                      "speechSynthesis" in window
                        ? "bg-green-500/20 text-green-400"
                        : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {"speechSynthesis" in window ? "Available" : "Unavailable"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">Language</span>
                  <span className="text-gray-500">🇺🇸 English</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-700">Commands Today</span>
                  <span className="text-gray-900">{commands.length}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

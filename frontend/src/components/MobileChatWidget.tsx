'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Send, Bot, Loader2, ChevronDown } from 'lucide-react'
import { createClient } from '@/utils/supabase/client'
import { chatCoach } from '@/utils/api'

interface Message {
    role: 'user' | 'assistant'
    content: string
}

interface MobileChatWidgetProps {
    isOpen: boolean
    onClose: () => void
    contextText?: string
}

export default function MobileChatWidget({ isOpen, onClose, contextText }: MobileChatWidgetProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const supabase = createClient()

    useEffect(() => {
        if (isOpen) {
            if (messages.length === 0) {
                setMessages([
                    { role: 'assistant', content: `Hello! I've analyzed your plan. Ask me anything about the exercises, sets, or technique!` }
                ])
            }
        }
    }, [isOpen])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const handleSend = async () => {
        if (!input.trim()) return

        const userMsg = input
        setInput('')
        setMessages(prev => [...prev, { role: 'user', content: userMsg }])
        setLoading(true)

        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) return

            const response = await chatCoach(session.access_token, userMsg, {}, contextText)

            setMessages(prev => [...prev, { role: 'assistant', content: response.answer }])
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: "I'm having trouble connecting. Please try again." }])
        } finally {
            setLoading(false)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-end justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Bottom Sheet */}
            <div className="relative w-full h-[90vh] bg-zinc-900 rounded-t-3xl flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-300">
                {/* Handle Bar */}
                <div className="w-full flex justify-center pt-3 pb-1" onClick={onClose}>
                    <div className="w-12 h-1.5 bg-zinc-700 rounded-full" />
                </div>

                {/* Header */}
                <div className="px-4 py-3 border-b border-zinc-800 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
                            <Bot className="text-white" size={24} />
                        </div>
                        <div>
                            <h3 className="font-bold text-white">Coach Mike</h3>
                            <div className="flex items-center gap-1.5">
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                <p className="text-xs text-green-400 font-medium">Online</p>
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 bg-zinc-800 hover:bg-zinc-700 rounded-full transition-colors"
                    >
                        <ChevronDown size={24} className="text-gray-400" />
                    </button>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-zinc-900">
                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] p-4 rounded-2xl shadow-sm ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-tr-none'
                                    : 'bg-zinc-800 text-gray-100 rounded-tl-none border border-zinc-700'
                                    }`}
                            >
                                <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{msg.content}</p>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-zinc-800 p-4 rounded-2xl rounded-tl-none border border-zinc-700 flex items-center gap-2">
                                <Loader2 className="animate-spin text-blue-500" size={18} />
                                <span className="text-sm text-gray-400">Thinking...</span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 bg-zinc-900 border-t border-zinc-800 pb-8">
                    <div className="flex gap-2 items-end">
                        <div className="flex-1 bg-zinc-800 rounded-2xl border border-zinc-700 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault()
                                        handleSend()
                                    }
                                }}
                                placeholder="Ask about your plan..."
                                className="w-full bg-transparent border-none px-4 py-3 text-white placeholder-gray-500 focus:ring-0 resize-none max-h-32 min-h-[50px]"
                                rows={1}
                            />
                        </div>
                        <button
                            onClick={handleSend}
                            disabled={loading || !input.trim()}
                            className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 transition-all shadow-lg active:scale-95"
                        >
                            <Send size={20} className={input.trim() ? "ml-0.5" : ""} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

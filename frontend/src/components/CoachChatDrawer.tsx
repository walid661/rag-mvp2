'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Send, User, Bot, Loader2 } from 'lucide-react'
import { createClient } from '@/utils/supabase/client'
import { chatCoach } from '@/utils/api'

interface Message {
    role: 'user' | 'assistant'
    content: string
}

interface CoachChatDrawerProps {
    isOpen: boolean
    onClose: () => void
    exerciseName?: string
    contextText?: string
}

export default function CoachChatDrawer({ isOpen, onClose, exerciseName, contextText }: CoachChatDrawerProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const supabase = createClient()

    useEffect(() => {
        if (isOpen) {
            // Reset messages or keep history? For now, let's keep it simple.
            // If we wanted to persist chat, we'd need a backend endpoint for that.
            if (messages.length === 0) {
                setMessages([
                    { role: 'assistant', content: `Hello Champion! I'm ready to help you with this plan. What's on your mind?` }
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

            const response = await chatCoach(session.access_token, userMsg, { exercise: exerciseName }, contextText)

            setMessages(prev => [...prev, { role: 'assistant', content: response.answer }])
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I'm having trouble connecting to the gym wifi. Try again?" }])
        } finally {
            setLoading(false)
        }
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-end justify-center pointer-events-none">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 pointer-events-auto backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Drawer */}
            <div className="bg-zinc-900 w-full max-w-md h-[80vh] rounded-t-3xl flex flex-col pointer-events-auto border-t border-zinc-800 shadow-2xl transform transition-transform duration-300 ease-out">
                {/* Header */}
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
                            <Bot className="text-black" size={24} />
                        </div>
                        <div>
                            <h3 className="font-bold">Coach Mike</h3>
                            <p className="text-xs text-green-400">Online</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-full">
                        <X size={24} />
                    </button>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[80%] p-4 rounded-2xl ${msg.role === 'user'
                                    ? 'bg-white text-black rounded-tr-none'
                                    : 'bg-zinc-800 text-white rounded-tl-none'
                                    }`}
                            >
                                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-zinc-800 p-4 rounded-2xl rounded-tl-none">
                                <Loader2 className="animate-spin" size={20} />
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="p-4 border-t border-zinc-800 bg-zinc-900 pb-8">
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Ask about form, sets, or alternatives..."
                            className="flex-1 bg-zinc-800 border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-white outline-none"
                        />
                        <button
                            onClick={handleSend}
                            disabled={loading || !input.trim()}
                            className="bg-white text-black p-3 rounded-xl hover:bg-gray-200 disabled:opacity-50"
                        >
                            <Send size={20} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

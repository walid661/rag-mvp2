'use client'

import { useState, useEffect, use } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import { ArrowLeft, MessageCircle, Loader2, Calendar } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import MobileChatWidget from '@/components/MobileChatWidget'

export default function ProgramDetailsPage({ params }: { params: Promise<{ id: string }> }) {
    const [program, setProgram] = useState<any>(null)
    const [content, setContent] = useState<string>('')
    const [loading, setLoading] = useState(true)
    const [chatOpen, setChatOpen] = useState(false)
    const [resolvedParams, setResolvedParams] = useState<{ id: string } | null>(null)

    const router = useRouter()
    const supabase = createClient()

    useEffect(() => {
        params.then(setResolvedParams)
    }, [params])

    useEffect(() => {
        if (!resolvedParams) return

        const fetchProgram = async () => {
            const { data: { user } } = await supabase.auth.getUser()
            if (!user) {
                router.push('/login')
                return
            }

            try {
                const { data, error } = await supabase
                    .from('saved_programs')
                    .select('*')
                    .eq('id', resolvedParams.id)
                    .eq('user_id', user.id)
                    .single()

                if (error) throw error

                if (data) {
                    setProgram(data)
                    // Handle both structure types (old JSON vs new JSONB with text)
                    const textContent = data.program_data?.text || JSON.stringify(data.program_data, null, 2)
                    setContent(textContent)
                }
            } catch (error) {
                console.error("Failed to fetch program", error)
                router.push('/dashboard')
            } finally {
                setLoading(false)
            }
        }

        fetchProgram()
    }, [resolvedParams, router])

    if (loading) return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
            <Loader2 className="animate-spin" />
        </div>
    )

    if (!program) return null

    return (
        <div className="min-h-screen bg-black text-white flex flex-col">
            {/* Header */}
            <div className="p-4 flex items-center gap-4 bg-zinc-900/80 backdrop-blur-md sticky top-0 z-10 border-b border-zinc-800">
                <button
                    onClick={() => router.back()}
                    className="p-2 hover:bg-zinc-800 rounded-full transition-colors active:scale-95"
                >
                    <ArrowLeft size={24} />
                </button>
                <div className="flex-1 min-w-0">
                    <h1 className="text-lg font-bold truncate">{program.title}</h1>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                        <Calendar size={12} />
                        {new Date(program.created_at).toLocaleDateString()}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 p-4 pb-32 max-w-3xl mx-auto w-full">
                <div className="prose prose-invert prose-lg max-w-none">
                    <ReactMarkdown>{content}</ReactMarkdown>
                </div>
            </div>

            {/* Floating Action Button (FAB) */}
            <div className="fixed bottom-6 right-6 z-40">
                <button
                    onClick={() => setChatOpen(true)}
                    className="w-14 h-14 bg-blue-600 text-white rounded-full flex items-center justify-center shadow-2xl hover:bg-blue-500 transition-all active:scale-90 animate-in zoom-in duration-300"
                >
                    <MessageCircle size={28} />
                </button>
            </div>

            {/* Chat Widget */}
            <MobileChatWidget
                isOpen={chatOpen}
                onClose={() => setChatOpen(false)}
                contextText={content}
            />
        </div>
    )
}

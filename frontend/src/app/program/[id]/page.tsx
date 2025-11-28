'use client'

import { useState, useEffect, use } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import { ArrowLeft, MessageCircle, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import CoachChatDrawer from '@/components/CoachChatDrawer'

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
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) {
                router.push('/login')
                return
            }

            try {
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/programs/${resolvedParams.id}`, {
                    headers: {
                        'Authorization': `Bearer ${session.access_token}`
                    }
                })

                if (res.ok) {
                    const data = await res.json()
                    setProgram(data.data)
                    setContent(data.content)
                } else {
                    router.push('/dashboard')
                }
            } catch (error) {
                console.error("Failed to fetch program", error)
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
            <div className="p-6 flex justify-between items-center bg-zinc-900/50 backdrop-blur-md sticky top-0 z-10 border-b border-zinc-800">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.back()}
                        className="p-2 hover:bg-zinc-800 rounded-full transition-colors"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="text-xl font-bold truncate max-w-[200px] md:max-w-md">{program.title}</h1>
                        <p className="text-gray-400 text-xs">
                            {new Date(program.created_at).toLocaleDateString()}
                        </p>
                    </div>
                </div>
                <button
                    onClick={() => setChatOpen(true)}
                    className="w-10 h-10 bg-white text-black rounded-full flex items-center justify-center hover:bg-gray-200 transition-colors shadow-lg shadow-white/10"
                >
                    <MessageCircle size={20} />
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 p-4 md:p-8 max-w-4xl mx-auto w-full">
                <div className="bg-zinc-900/30 border border-zinc-800 rounded-3xl p-6 md:p-10 shadow-xl">
                    <article className="prose prose-invert prose-lg max-w-none">
                        <ReactMarkdown>{content}</ReactMarkdown>
                    </article>
                </div>
            </div>

            {/* Chat Drawer */}
            <CoachChatDrawer
                isOpen={chatOpen}
                onClose={() => setChatOpen(false)}
                contextText={content}
            />
        </div>
    )
}

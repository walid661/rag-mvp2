'use client'

import { useState, useEffect, use } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import { ArrowLeft, MessageCircle, Loader2, Calendar } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import MobileChatWidget from '@/components/MobileChatWidget'

interface ParsedSection {
    title: string
    content: string
}

export default function ProgramDetailsPage({ params }: { params: Promise<{ id: string }> }) {
    const [program, setProgram] = useState<any>(null)
    const [content, setContent] = useState<string>('')
    const [parsedSections, setParsedSections] = useState<ParsedSection[]>([])
    const [activeTab, setActiveTab] = useState(0)
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

                    // Parse the content for tabs
                    const sections = parseProgramText(textContent)
                    setParsedSections(sections)

                    // Default to Day 1 (index 1 usually, if Overview exists) or index 0
                    // If we have Overview + Day 1, maybe we want to show Overview first?
                    // Let's default to 0.
                    setActiveTab(0)
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

    const parseProgramText = (text: string): ParsedSection[] => {
        // Regex to split by "## Day X" or "### Day X"
        // We use a lookahead to keep the delimiter in the split array (if we used capturing group)
        // But split with lookahead keeps the delimiter in the *next* token usually?
        // Actually split(regex) where regex has capturing group includes the captures.
        // Lookahead `(?=...)` splits *at* the position, keeping the text in the next part.

        const dayRegex = /(?=#{2,3}\s*Day\s*\d+)/i
        const parts = text.split(dayRegex)

        const sections: ParsedSection[] = []

        parts.forEach(part => {
            const trimmed = part.trim()
            if (!trimmed) return

            // Check if this part starts with Day X
            const titleMatch = trimmed.match(/#{2,3}\s*(Day\s*\d+)/i)

            if (titleMatch) {
                sections.push({
                    title: titleMatch[1], // "Day 1"
                    content: trimmed
                })
            } else {
                // This is likely the Intro/Overview
                sections.push({
                    title: "Overview",
                    content: trimmed
                })
            }
        })

        return sections
    }

    if (loading) return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
            <Loader2 className="animate-spin" />
        </div>
    )

    if (!program) return null

    const showTabs = parsedSections.length > 1

    return (
        <div className="min-h-screen bg-black text-white flex flex-col">
            {/* Header */}
            <div className="p-4 flex items-center gap-4 bg-zinc-900/80 backdrop-blur-md sticky top-0 z-20 border-b border-zinc-800">
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

            {/* Tabs */}
            {showTabs && (
                <div className="sticky top-[73px] z-10 bg-black/95 border-b border-zinc-800 overflow-x-auto">
                    <div className="flex p-2 gap-2 min-w-max">
                        {parsedSections.map((section, index) => (
                            <button
                                key={index}
                                onClick={() => setActiveTab(index)}
                                className={`px-4 py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap ${activeTab === index
                                        ? 'bg-white text-black shadow-lg scale-105'
                                        : 'bg-zinc-900 text-gray-400 hover:bg-zinc-800'
                                    }`}
                            >
                                {section.title}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="flex-1 p-4 pb-32 max-w-3xl mx-auto w-full">
                <div className="prose prose-invert prose-lg max-w-none">
                    <ReactMarkdown>
                        {showTabs ? parsedSections[activeTab].content : content}
                    </ReactMarkdown>
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
                contextText={showTabs ? parsedSections[activeTab].content : content}
            />
        </div>
    )
}

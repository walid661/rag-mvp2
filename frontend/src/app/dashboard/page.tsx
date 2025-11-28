'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import {
    Home, Calendar, User, MessageCircle, Edit
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import CoachChatDrawer from '@/components/CoachChatDrawer'

export default function DashboardPage() {
    const [program, setProgram] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState('home')
    const [chatOpen, setChatOpen] = useState(false)

    const router = useRouter()
    const supabase = createClient()

    useEffect(() => {
        const fetchProgram = async () => {
            const { data: { user } } = await supabase.auth.getUser()
            if (!user) {
                router.push('/login')
                return
            }

            const { data, error } = await supabase
                .from('saved_programs')
                .select('*')
                .eq('user_id', user.id)
                .eq('status', 'active')
                .order('created_at', { ascending: false })
                .limit(1)
                .single()

            if (data) {
                setProgram(data.program_data)
            }
            setLoading(false)
        }

        fetchProgram()
    }, [])

    if (loading) return <div className="min-h-screen bg-black text-white flex items-center justify-center">Loading...</div>

    if (!program) {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6 text-center">
                <h2 className="text-2xl font-bold mb-4">No Active Plan</h2>
                <p className="text-gray-400 mb-8">You haven't started a training block yet.</p>
                <button
                    onClick={() => router.push('/generator')}
                    className="px-8 py-4 bg-white text-black font-bold rounded-2xl"
                >
                    Create New Plan
                </button>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-black text-white flex flex-col pb-24">
            {/* Header */}
            <div className="p-6 flex justify-between items-center bg-zinc-900/50 backdrop-blur-md sticky top-0 z-10 border-b border-zinc-800">
                <div>
                    <h1 className="text-2xl font-bold">Current Plan</h1>
                    <p className="text-gray-400 text-sm">Week 1</p>
                </div>
                <button
                    onClick={() => setChatOpen(true)}
                    className="w-10 h-10 bg-zinc-800 rounded-full flex items-center justify-center hover:bg-zinc-700 transition-colors"
                >
                    <MessageCircle size={20} />
                </button>
            </div>

            {/* Main Content */}
            <div className="p-4 md:p-6">
                <div className="bg-zinc-900/30 border border-zinc-800 rounded-3xl p-6 shadow-xl">
                    <article className="prose prose-invert prose-lg max-w-none">
                        <ReactMarkdown>{program.text || "**No plan text found.**"}</ReactMarkdown>
                    </article>
                </div>
            </div>

            {/* Bottom Nav */}
            <div className="fixed bottom-0 left-0 right-0 bg-black/90 backdrop-blur-lg border-t border-zinc-800 p-4 flex justify-around items-center z-40">
                <button
                    onClick={() => setActiveTab('home')}
                    className={`flex flex-col items-center gap-1 ${activeTab === 'home' ? 'text-white' : 'text-gray-600'}`}
                >
                    <Home size={24} />
                    <span className="text-[10px] font-bold">Home</span>
                </button>
                <button
                    onClick={() => router.push('/generator')}
                    className={`flex flex-col items-center gap-1 ${activeTab === 'calendar' ? 'text-white' : 'text-gray-600'}`}
                >
                    <Edit size={24} />
                    <span className="text-[10px] font-bold">New Plan</span>
                </button>
                <button
                    onClick={() => setActiveTab('profile')}
                    className={`flex flex-col items-center gap-1 ${activeTab === 'profile' ? 'text-white' : 'text-gray-600'}`}
                >
                    <User size={24} />
                    <span className="text-[10px] font-bold">Profile</span>
                </button>
            </div>

            {/* Chat Drawer */}
            <CoachChatDrawer
                isOpen={chatOpen}
                onClose={() => setChatOpen(false)}
                exerciseName={undefined}
            />
        </div>
    )
}

'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import {
    Home, Calendar, User, Dumbbell,
    MessageCircle, Clock, Flame, ChevronRight
} from 'lucide-react'
import CoachChatDrawer from '@/components/CoachChatDrawer'

export default function DashboardPage() {
    const [program, setProgram] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState('home')
    const [chatOpen, setChatOpen] = useState(false)
    const [selectedExercise, setSelectedExercise] = useState<string | undefined>(undefined)

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

    const handleOpenChat = (exercise?: string) => {
        setSelectedExercise(exercise)
        setChatOpen(true)
    }

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

    // Get Today's Session (Mock logic: Day 1)
    const todaySession = program.sessions[0]

    return (
        <div className="min-h-screen bg-black text-white flex flex-col pb-24">
            {/* Header */}
            <div className="p-6 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold">Today's Workout</h1>
                    <p className="text-gray-400 text-sm">{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</p>
                </div>
                <div className="w-10 h-10 bg-zinc-800 rounded-full flex items-center justify-center">
                    <User size={20} />
                </div>
            </div>

            {/* Main Card */}
            <div className="mx-6 p-6 bg-gradient-to-br from-zinc-800 to-zinc-900 rounded-3xl border border-zinc-700 relative overflow-hidden">
                <div className="relative z-10">
                    <div className="flex justify-between items-start mb-4">
                        <span className="px-3 py-1 bg-white/10 rounded-full text-xs font-bold uppercase tracking-wider">
                            {todaySession.theme}
                        </span>
                        <button onClick={() => handleOpenChat()} className="p-2 bg-white/10 rounded-full hover:bg-white/20">
                            <MessageCircle size={18} />
                        </button>
                    </div>

                    <h2 className="text-3xl font-bold mb-6">Upper Body Power</h2>

                    <div className="flex gap-6 text-sm text-gray-300">
                        <div className="flex items-center gap-2">
                            <Clock size={16} /> 45 min
                        </div>
                        <div className="flex items-center gap-2">
                            <Flame size={16} /> High Intensity
                        </div>
                    </div>
                </div>

                {/* Background Decoration */}
                <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-white/5 rounded-full blur-3xl"></div>
            </div>

            {/* Exercises */}
            <div className="p-6 space-y-4">
                <h3 className="font-bold text-gray-400 text-sm tracking-wider">EXERCISES</h3>

                {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="bg-zinc-900 p-4 rounded-2xl border border-zinc-800 flex items-center gap-4 group">
                        <div className="w-12 h-12 bg-zinc-800 rounded-xl flex items-center justify-center text-zinc-500 group-hover:bg-white group-hover:text-black transition-colors">
                            <Dumbbell size={24} />
                        </div>

                        <div className="flex-1">
                            <div className="font-bold">Exercise Name {i}</div>
                            <div className="text-sm text-gray-400">3 sets x 8-10 reps</div>
                        </div>

                        <button
                            onClick={() => handleOpenChat(`Exercise Name ${i}`)}
                            className="p-3 rounded-xl hover:bg-zinc-800 text-gray-500 hover:text-white transition-colors"
                        >
                            <MessageCircle size={20} />
                        </button>
                    </div>
                ))}
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
                    onClick={() => setActiveTab('calendar')}
                    className={`flex flex-col items-center gap-1 ${activeTab === 'calendar' ? 'text-white' : 'text-gray-600'}`}
                >
                    <Calendar size={24} />
                    <span className="text-[10px] font-bold">Schedule</span>
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
                exerciseName={selectedExercise}
            />
        </div>
    )
}

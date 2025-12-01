'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import {
    Plus, Calendar, ChevronRight, Loader2, Dumbbell, Trash2
} from 'lucide-react'

export default function DashboardPage() {
    const [programs, setPrograms] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const router = useRouter()
    const supabase = createClient()

    useEffect(() => {
        const fetchPrograms = async () => {
            const { data: { user } } = await supabase.auth.getUser()
            if (!user) {
                router.push('/login')
                return
            }

            try {
                const { data, error } = await supabase
                    .from('saved_programs')
                    .select('id, title, created_at, status')
                    .eq('user_id', user.id)
                    .order('created_at', { ascending: false })

                if (error) throw error

                setPrograms(data || [])
            } catch (error) {
                console.error("Failed to fetch programs", error)
            } finally {
                setLoading(false)
            }
        }

        fetchPrograms()
    }, [router])

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation() // Prevent navigation when clicking delete

        if (!window.confirm("Are you sure you want to delete this plan? This action cannot be undone.")) {
            return
        }

        // Optimistic update
        setPrograms(prev => prev.filter(p => p.id !== id))

        try {
            const { error } = await supabase
                .from('saved_programs')
                .delete()
                .eq('id', id)

            if (error) {
                throw error
            }
        } catch (error) {
            console.error("Failed to delete program", error)
            alert("Failed to delete program. Please refresh.")
            // Revert optimistic update if needed, but for MVP simple alert is okay
        }
    }

    if (loading) return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
            <Loader2 className="animate-spin" />
        </div>
    )

    return (
        <div className="min-h-screen bg-black text-white p-4 pb-24">
            {/* Header */}
            <div className="flex justify-between items-center mb-6 mt-2">
                <div>
                    <h1 className="text-2xl font-bold">My Programs</h1>
                    <p className="text-gray-400 text-sm">Your training history</p>
                </div>
                <button
                    onClick={() => router.push('/generator')}
                    className="w-12 h-12 bg-white text-black rounded-full flex items-center justify-center hover:bg-gray-200 transition-colors shadow-lg shadow-white/10 active:scale-95"
                >
                    <Plus size={24} />
                </button>
            </div>

            {/* Program List */}
            <div className="space-y-4">
                {programs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 bg-zinc-900/30 rounded-3xl border border-zinc-800/50">
                        <div className="w-16 h-16 bg-zinc-800 rounded-full flex items-center justify-center mb-4 text-gray-500">
                            <Dumbbell size={32} />
                        </div>
                        <h3 className="text-lg font-bold mb-2">No plans yet</h3>
                        <p className="text-gray-400 text-sm mb-6 text-center max-w-[200px]">
                            Start your journey by creating your first custom training plan.
                        </p>
                        <button
                            onClick={() => router.push('/generator')}
                            className="px-8 py-3 bg-white text-black rounded-full font-bold hover:bg-gray-200 transition-colors active:scale-95"
                        >
                            Create New Plan
                        </button>
                    </div>
                ) : (
                    programs.map((program) => (
                        <div
                            key={program.id}
                            onClick={() => router.push(`/program/${program.id}`)}
                            className="bg-zinc-900/50 border border-zinc-800 p-5 rounded-3xl flex items-center justify-between active:bg-zinc-800 transition-all cursor-pointer group touch-manipulation relative overflow-hidden"
                        >
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <h3 className="font-bold text-lg text-white group-hover:text-gray-200 transition-colors pr-8">
                                        {program.title}
                                    </h3>
                                    {program.status === 'active' && (
                                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-bold rounded-full uppercase tracking-wider">
                                            Active
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-2 text-xs text-gray-500">
                                    <Calendar size={12} />
                                    {new Date(program.created_at).toLocaleDateString(undefined, {
                                        year: 'numeric',
                                        month: 'short',
                                        day: 'numeric'
                                    })}
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                <button
                                    onClick={(e) => handleDelete(e, program.id)}
                                    className="w-10 h-10 flex items-center justify-center text-gray-500 hover:text-red-500 hover:bg-red-500/10 rounded-full transition-all z-10"
                                    title="Delete Program"
                                >
                                    <Trash2 size={18} />
                                </button>
                                <div className="w-8 h-8 bg-zinc-800 rounded-full flex items-center justify-center text-gray-400 group-hover:bg-white group-hover:text-black transition-all">
                                    <ChevronRight size={18} />
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}

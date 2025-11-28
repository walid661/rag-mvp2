'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import {
    Plus, Calendar, ChevronRight, Loader2
} from 'lucide-react'

export default function DashboardPage() {
    const [programs, setPrograms] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const router = useRouter()
    const supabase = createClient()

    useEffect(() => {
        const fetchPrograms = async () => {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) {
                router.push('/login')
                return
            }

            try {
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/programs`, {
                    headers: {
                        'Authorization': `Bearer ${session.access_token}`
                    }
                })

                if (res.ok) {
                    const data = await res.json()
                    setPrograms(data.data || [])
                }
            } catch (error) {
                console.error("Failed to fetch programs", error)
            } finally {
                setLoading(false)
            }
        }

        fetchPrograms()
    }, [router])

    if (loading) return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
            <Loader2 className="animate-spin" />
        </div>
    )

    return (
        <div className="min-h-screen bg-black text-white p-6 pb-24">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold">My Programs</h1>
                    <p className="text-gray-400">Your training history</p>
                </div>
                <button
                    onClick={() => router.push('/generator')}
                    className="w-12 h-12 bg-white text-black rounded-full flex items-center justify-center hover:bg-gray-200 transition-colors shadow-lg shadow-white/10"
                >
                    <Plus size={24} />
                </button>
            </div>

            {/* Program List */}
            <div className="space-y-4">
                {programs.length === 0 ? (
                    <div className="text-center py-12 bg-zinc-900/50 rounded-3xl border border-zinc-800">
                        <p className="text-gray-400 mb-4">No programs found.</p>
                        <button
                            onClick={() => router.push('/generator')}
                            className="px-6 py-2 bg-zinc-800 rounded-full text-sm font-bold hover:bg-zinc-700"
                        >
                            Create your first plan
                        </button>
                    </div>
                ) : (
                    programs.map((program) => (
                        <div
                            key={program.id}
                            onClick={() => router.push(`/program/${program.id}`)}
                            className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-3xl flex items-center justify-between hover:bg-zinc-900 transition-all cursor-pointer group"
                        >
                            <div>
                                <h3 className="font-bold text-lg mb-1 group-hover:text-white transition-colors">{program.title}</h3>
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                    <Calendar size={14} />
                                    {new Date(program.created_at).toLocaleDateString()}
                                </div>
                            </div>
                            <div className="w-10 h-10 bg-zinc-800 rounded-full flex items-center justify-center text-gray-400 group-hover:bg-white group-hover:text-black transition-all">
                                <ChevronRight size={20} />
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}

'use client'

import { useState } from 'react'
import { createClient } from '@/utils/supabase/client'
import { generateProgram } from '@/utils/api'
import { useRouter } from 'next/navigation'
import WeeklyView from '@/components/WeeklyView'
import { Loader2, Sparkles, Save } from 'lucide-react'

export default function GeneratorPage() {
    const [loading, setLoading] = useState(false)
    const [programData, setProgramData] = useState<any>(null)
    const router = useRouter()
    const supabase = createClient()

    const handleGenerate = async () => {
        setLoading(true)
        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) {
                router.push('/login')
                return
            }

            const data = await generateProgram(session.access_token)
            setProgramData(data)
        } catch (err) {
            alert('Error generating plan: ' + err)
        } finally {
            setLoading(false)
        }
    }

    const handleSave = async () => {
        if (!programData) return

        const { data: { user } } = await supabase.auth.getUser()
        if (!user) return

        const { error } = await supabase
            .from('saved_programs')
            .insert({
                user_id: user.id,
                title: `My ${programData.strategy.split_type} Plan`,
                program_data: programData,
                status: 'active'
            })

        if (error) {
            alert('Error saving: ' + error.message)
        } else {
            router.push('/dashboard')
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-8 text-center">
                <div className="relative">
                    <div className="absolute inset-0 bg-blue-500 blur-3xl opacity-20 animate-pulse"></div>
                    <Loader2 size={64} className="animate-spin text-white relative z-10" />
                </div>
                <h2 className="text-2xl font-bold mt-8 mb-2">Coach Mike is thinking...</h2>
                <p className="text-gray-400">Analyzing your profile & crafting the perfect split.</p>
            </div>
        )
    }

    if (programData) {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col">
                {/* Header */}
                <div className="p-6 pb-2">
                    <h1 className="text-2xl font-bold">Your Custom Plan</h1>
                    <p className="text-gray-400 text-sm">{programData.strategy.split_type}</p>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden">
                    <WeeklyView plan={programData} />
                </div>

                {/* Floating Action Button */}
                <div className="p-6 pt-2 bg-gradient-to-t from-black to-transparent">
                    <button
                        onClick={handleSave}
                        className="w-full py-4 bg-white text-black font-bold rounded-2xl shadow-lg shadow-white/10 flex items-center justify-center gap-2 hover:scale-[1.02] transition-transform"
                    >
                        <Save size={20} />
                        Save & Start Training
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6">
            <div className="text-center max-w-md space-y-8">
                <div className="w-24 h-24 bg-zinc-900 rounded-3xl mx-auto flex items-center justify-center border border-zinc-800">
                    <Sparkles size={40} />
                </div>

                <div>
                    <h1 className="text-4xl font-bold mb-4">Ready to Build?</h1>
                    <p className="text-gray-400">
                        Based on your profile, Coach Mike will generate a fully periodized training block.
                    </p>
                </div>

                <button
                    onClick={handleGenerate}
                    className="w-full py-5 bg-white text-black font-bold text-xl rounded-2xl hover:bg-gray-200 transition-all shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                >
                    Build My Plan
                </button>
            </div>
        </div>
    )
}

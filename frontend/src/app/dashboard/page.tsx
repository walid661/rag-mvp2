'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'
import { generateProgram } from '@/utils/api'
import { Loader2, Save, RefreshCw, X, Sparkles, History, User } from 'lucide-react'
import ProgramViewer from '@/components/ProgramViewer'

export default function DashboardHub() {
    const router = useRouter()

    // State for the "Welcome Hub" vs "Generating" vs "Result"
    const [viewState, setViewState] = useState<'hub' | 'generating' | 'result' | 'error'>('hub')

    const [planText, setPlanText] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [saving, setSaving] = useState(false)

    // Modal State
    const [showSaveModal, setShowSaveModal] = useState(false)
    const [programTitle, setProgramTitle] = useState('')

    const handleGenerate = async () => {
        setViewState('generating')
        setError(null)

        try {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()

            if (!session) {
                router.push('/login')
                return
            }

            // Call the new LLM-based generation endpoint
            const data = await generateProgram(session.access_token, {})

            if (data.plan_text) {
                setPlanText(data.plan_text)
                setProgramTitle(`Weekly Plan - ${new Date().toLocaleDateString()}`)
                setViewState('result')
            } else {
                throw new Error("Received empty plan from coach.")
            }
        } catch (err: any) {
            console.error("Generation error:", err)
            setError(err.message || "Failed to generate plan.")
            setViewState('error')
        }
    }

    const handleSaveClick = () => {
        if (!planText) return
        setShowSaveModal(true)
    }

    const confirmSave = async () => {
        if (!planText) return
        setSaving(true)
        try {
            const supabase = createClient()
            const { data: { user } } = await supabase.auth.getUser()

            if (!user) {
                alert("User not found. Please log in.")
                return
            }

            const { error } = await supabase
                .from('saved_programs')
                .insert({
                    user_id: user.id,
                    title: programTitle || `Weekly Plan - ${new Date().toLocaleDateString()}`,
                    program_data: { text: planText },
                    status: 'active'
                })

            if (error) throw error

            router.push('/my-programs')
        } catch (err: any) {
            console.error("Save error:", err)
            alert(`Failed to save plan: ${err.message || err}`)
            setSaving(false)
        }
    }

    // --- RENDER STATES ---

    if (viewState === 'generating') {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
                <Loader2 className="w-16 h-16 animate-spin text-white mb-6" />
                <h2 className="text-3xl font-bold mb-2">Coach Mike is thinking...</h2>
                <p className="text-gray-400 text-center max-w-md text-lg">
                    Analyzing your profile, checking 100+ training protocols, and building your custom plan.
                </p>
            </div>
        )
    }

    if (viewState === 'error') {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
                <div className="bg-red-500/10 border border-red-500/20 p-8 rounded-3xl max-w-md text-center">
                    <h2 className="text-2xl font-bold text-red-500 mb-4">Generation Failed</h2>
                    <p className="text-gray-300 mb-8">{error}</p>
                    <div className="flex gap-4 justify-center">
                        <button
                            onClick={() => setViewState('hub')}
                            className="px-6 py-3 rounded-full font-bold text-gray-400 hover:bg-zinc-800 transition-colors"
                        >
                            Back to Hub
                        </button>
                        <button
                            onClick={handleGenerate}
                            className="bg-white text-black px-6 py-3 rounded-full font-bold hover:bg-gray-200 transition-colors flex items-center gap-2"
                        >
                            <RefreshCw size={20} /> Try Again
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    if (viewState === 'result') {
        return (
            <div className="min-h-screen bg-black text-white p-4 md:p-8 relative">
                <div className="max-w-4xl mx-auto">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-8">
                        <button
                            onClick={() => setViewState('hub')}
                            className="px-4 py-2 rounded-full hover:bg-zinc-900 text-gray-400 transition-colors"
                        >
                            Discard
                        </button>
                        <h1 className="text-2xl font-bold hidden md:block">Your Custom Plan</h1>
                        <button
                            onClick={handleSaveClick}
                            disabled={saving}
                            className="bg-white text-black px-6 py-3 rounded-full font-bold hover:bg-gray-200 transition-colors flex items-center gap-2 disabled:opacity-50 shadow-lg shadow-white/10"
                        >
                            <Save size={20} />
                            Save & Start
                        </button>
                    </div>

                    {/* Markdown Content */}
                    <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl overflow-hidden shadow-2xl">
                        <ProgramViewer content={planText || ''} />
                    </div>
                </div>

                {/* Save Modal */}
                {showSaveModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
                        <div className="bg-zinc-900 border border-zinc-800 w-full max-w-md rounded-3xl p-6 shadow-2xl animate-in zoom-in-95 duration-200">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-xl font-bold">Name your program</h3>
                                <button
                                    onClick={() => setShowSaveModal(false)}
                                    className="p-2 hover:bg-zinc-800 rounded-full transition-colors"
                                >
                                    <X size={20} className="text-gray-400" />
                                </button>
                            </div>

                            <div className="mb-8">
                                <label className="block text-sm text-gray-400 mb-2">Program Title</label>
                                <input
                                    type="text"
                                    value={programTitle}
                                    onChange={(e) => setProgramTitle(e.target.value)}
                                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-white focus:border-transparent outline-none transition-all"
                                    placeholder="e.g. Summer Shred 2025"
                                    autoFocus
                                />
                            </div>

                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowSaveModal(false)}
                                    className="flex-1 py-3 rounded-xl font-bold text-gray-400 hover:bg-zinc-800 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmSave}
                                    disabled={saving || !programTitle.trim()}
                                    className="flex-1 bg-white text-black py-3 rounded-xl font-bold hover:bg-gray-200 transition-colors disabled:opacity-50 flex justify-center items-center gap-2"
                                >
                                    {saving && <Loader2 size={18} className="animate-spin" />}
                                    {saving ? 'Saving...' : 'Confirm Save'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        )
    }

    // --- DEFAULT HUB VIEW ---
    return (
        <div className="min-h-screen bg-black text-white flex flex-col relative overflow-hidden">

            {/* Background Elements */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px]" />
                <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[100px]" />
            </div>

            {/* Navbar */}
            <nav className="flex justify-between items-center p-6 z-10">
                <div className="text-xl font-bold tracking-tighter">COACH MIKE</div>
                <div className="flex gap-4">
                    <button
                        onClick={() => router.push('/my-programs')}
                        className="p-3 rounded-full bg-zinc-900 hover:bg-zinc-800 transition-colors text-gray-400 hover:text-white"
                        title="My Programs"
                    >
                        <History size={20} />
                    </button>
                    <button
                        onClick={() => router.push('/profile')}
                        className="p-3 rounded-full bg-zinc-900 hover:bg-zinc-800 transition-colors text-gray-400 hover:text-white"
                        title="Profile"
                    >
                        <User size={20} />
                    </button>
                </div>
            </nav>

            {/* Main Content */}
            <main className="flex-1 flex flex-col items-center justify-center p-6 z-10 text-center">
                <div className="mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight">
                        Ready to <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">Build?</span>
                    </h1>
                    <p className="text-xl text-gray-400 max-w-lg mx-auto leading-relaxed">
                        Your AI coach is ready to design your perfect training week based on your latest goals and recovery.
                    </p>
                </div>

                <button
                    onClick={handleGenerate}
                    className="group relative px-8 py-6 bg-white text-black rounded-full font-bold text-xl md:text-2xl hover:scale-105 transition-all duration-300 shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)] hover:shadow-[0_0_60px_-10px_rgba(255,255,255,0.5)] animate-in fade-in zoom-in duration-500 delay-200"
                >
                    <span className="flex items-center gap-3">
                        <Sparkles className="w-6 h-6 text-purple-600 group-hover:rotate-12 transition-transform" />
                        Generate My Plan
                    </span>
                </button>

                <div className="mt-12 flex gap-8 text-sm text-gray-500 animate-in fade-in duration-1000 delay-500">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full" />
                        Science-based
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full" />
                        Personalized
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-purple-500 rounded-full" />
                        Instant
                    </div>
                </div>
            </main>
        </div>
    )
}

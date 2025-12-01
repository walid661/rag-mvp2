'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'
import { generateProgram } from '@/utils/api'
import { Loader2, Save, RefreshCw, ArrowLeft, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

export default function GeneratorPage() {
    const router = useRouter()
    const [loading, setLoading] = useState(true)
    const [planText, setPlanText] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [saving, setSaving] = useState(false)

    // Modal State
    const [showSaveModal, setShowSaveModal] = useState(false)
    const [programTitle, setProgramTitle] = useState('')

    useEffect(() => {
        const fetchPlan = async () => {
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
                    // Set default title
                    setProgramTitle(`Weekly Plan - ${new Date().toLocaleDateString()}`)
                } else {
                    setError("Received empty plan from coach.")
                }
            } catch (err) {
                console.error("Generation error:", err)
                setError("Failed to generate plan. Please try again.")
            } finally {
                setLoading(false)
            }
        }

        fetchPlan()
    }, [router])

    const handleSaveClick = () => {
        if (!planText) return
        setShowSaveModal(true)
    }

    const confirmSave = async () => {
        if (!planText) return
        setSaving(true)
        try {
            // Step 1: Get the current user
            const supabase = createClient()
            const { data: { user } } = await supabase.auth.getUser()

            if (!user) {
                alert("User not found. Please log in.")
                return
            }

            // Step 2: Insert directly into the table
            console.log("Saving plan directly to Supabase...", { user_id: user.id, title: programTitle })

            const { error } = await supabase
                .from('saved_programs')
                .insert({
                    user_id: user.id,
                    title: programTitle || `Weekly Plan - ${new Date().toLocaleDateString()}`,
                    program_data: { text: planText },
                    status: 'active'
                })

            // Step 3: Handle Errors explicitly
            if (error) {
                console.error("Supabase Insert Error:", error)
                throw new Error(error.message || "Database insert failed")
            }

            // Step 4: Redirect ONLY if successful
            console.log("Save success")
            router.push('/dashboard')
        } catch (err: any) {
            console.error("Save error:", err)
            alert(`Failed to save plan: ${err.message || err}`)
            setSaving(false) // Only reset if error, success redirects
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
                <Loader2 className="w-12 h-12 animate-spin text-white mb-4" />
                <h2 className="text-2xl font-bold mb-2">Coach Mike is thinking...</h2>
                <p className="text-gray-400 text-center max-w-md">
                    Analyzing your profile, checking 100+ training protocols, and building your custom plan.
                </p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
                <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-2xl max-w-md text-center">
                    <h2 className="text-xl font-bold text-red-500 mb-2">Generation Failed</h2>
                    <p className="text-gray-400 mb-6">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="bg-white text-black px-6 py-3 rounded-full font-bold hover:bg-gray-200 transition-colors flex items-center gap-2 mx-auto"
                    >
                        <RefreshCw size={20} /> Try Again
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-black text-white p-4 md:p-8 relative">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <button
                        onClick={() => router.back()}
                        className="p-2 hover:bg-zinc-900 rounded-full transition-colors"
                    >
                        <ArrowLeft size={24} />
                    </button>
                    <h1 className="text-2xl font-bold">Your Custom Plan</h1>
                    <button
                        onClick={handleSaveClick}
                        disabled={saving}
                        className="bg-white text-black px-6 py-3 rounded-full font-bold hover:bg-gray-200 transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        <Save size={20} />
                        Save & Start
                    </button>
                </div>

                {/* Markdown Content */}
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6 md:p-10 shadow-2xl">
                    <article className="prose prose-invert prose-lg max-w-none">
                        <ReactMarkdown>{planText || ''}</ReactMarkdown>
                    </article>
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

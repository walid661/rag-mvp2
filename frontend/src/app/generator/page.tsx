'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'
import { generateProgram } from '@/utils/api'
import { Loader2, Save, RefreshCw, ArrowLeft } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

export default function GeneratorPage() {
    const router = useRouter()
    const [loading, setLoading] = useState(true)
    const [planText, setPlanText] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [saving, setSaving] = useState(false)

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

    const handleSave = async () => {
        if (!planText) return
        setSaving(true)
        try {
            const supabase = createClient()
            const { data: { user } } = await supabase.auth.getUser()

            if (!user) {
                alert("User not found. Please log in.")
                return
            }

            const payload = {
                user_id: user.id,
                title: `Weekly Plan - ${new Date().toLocaleDateString()}`,
                program_data: { text: planText }
            }

            console.log("Saving plan...", payload)

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/save_program`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`
                },
                body: JSON.stringify(payload)
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.detail || 'Failed to save')
            }

            console.log("Save success")
            alert("Plan saved successfully!")
            router.push('/dashboard')
        } catch (err) {
            console.error("Save error:", err)
            alert("Failed to save plan. Check console for details.")
        } finally {
            setSaving(false)
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
        <div className="min-h-screen bg-black text-white p-4 md:p-8">
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
                        onClick={handleSave}
                        disabled={saving}
                        className="bg-white text-black px-6 py-3 rounded-full font-bold hover:bg-gray-200 transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        {saving ? <Loader2 size={20} className="animate-spin" /> : <Save size={20} />}
                        {saving ? 'Saving...' : 'Save & Start'}
                    </button>
                </div>

                {/* Markdown Content */}
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6 md:p-10 shadow-2xl">
                    <article className="prose prose-invert prose-lg max-w-none">
                        <ReactMarkdown>{planText || ''}</ReactMarkdown>
                    </article>
                </div>
            </div>
        </div>
    )
}

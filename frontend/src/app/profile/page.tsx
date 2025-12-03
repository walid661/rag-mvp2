'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import { Check, Loader2, Save } from 'lucide-react'

const GOALS = [
    { id: 'Perte de poids', label: 'Lose Weight', desc: 'Burn fat & get lean' },
    { id: 'Renforcement', label: 'Build Muscle', desc: 'Hypertrophy focus' },
    { id: 'Force', label: 'Strength', desc: 'Powerlifting focus' },
    { id: 'Cardio', label: 'Endurance', desc: 'Stamina & Health' },
]

const LEVELS = [
    { id: 'beginner', label: 'Beginner', desc: '< 6 months exp' },
    { id: 'intermediate', label: 'Intermediate', desc: '6 months - 2 years' },
    { id: 'advanced', label: 'Advanced', desc: '2+ years exp' },
]

const FREQUENCY = [2, 3, 4, 5, 6]

const EQUIPMENT = [
    { id: 'bodyweight', label: 'Bodyweight' },
    { id: 'dumbbell', label: 'Dumbbells' },
    { id: 'barbell', label: 'Barbell' },
    { id: 'resistance_band', label: 'Bands' },
    { id: 'machine', label: 'Machines' },
]

export default function ProfilePage() {
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const router = useRouter()
    const supabase = createClient()

    const [formData, setFormData] = useState({
        goal: '',
        level: '',
        equipment: [] as string[],
        days_per_week: 3
    })

    useEffect(() => {
        const fetchProfile = async () => {
            const { data: { user } } = await supabase.auth.getUser()

            if (!user) {
                router.push('/login')
                return
            }

            const { data, error } = await supabase
                .from('user_profiles')
                .select('*')
                .eq('user_id', user.id)
                .single()

            if (error) {
                console.error('Error fetching profile:', error)
            } else if (data) {
                setFormData({
                    goal: data.goal || '',
                    level: data.level || '',
                    equipment: data.equipment || [],
                    days_per_week: data.days_per_week || 3
                })
            }
            setLoading(false)
        }

        fetchProfile()
    }, [router, supabase])

    const toggleEquipment = (id: string) => {
        setFormData(prev => ({
            ...prev,
            equipment: prev.equipment.includes(id)
                ? prev.equipment.filter(e => e !== id)
                : [...prev.equipment, id]
        }))
    }

    const handleSave = async () => {
        setSaving(true)
        const { data: { user } } = await supabase.auth.getUser()

        if (!user) return

        const { error } = await supabase
            .from('user_profiles')
            .update({
                goal: formData.goal,
                level: formData.level,
                equipment: formData.equipment,
                days_per_week: formData.days_per_week
            })
            .eq('user_id', user.id)

        if (error) {
            alert('Error updating profile: ' + error.message)
        } else {
            alert('Profile updated successfully!')
        }
        setSaving(false)
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-black text-white flex items-center justify-center">
                <Loader2 className="animate-spin" size={48} />
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-black text-white p-6">
            <div className="max-w-2xl mx-auto space-y-8">
                <div className="flex justify-between items-center">
                    <h1 className="text-3xl font-bold">Your Profile</h1>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-lg font-bold hover:bg-gray-200 disabled:opacity-50"
                    >
                        {saving ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
                        Save Changes
                    </button>
                </div>

                {/* GOAL SECTION */}
                <section className="space-y-4">
                    <h2 className="text-xl font-semibold text-gray-400">Goal</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {GOALS.map(option => (
                            <button
                                key={option.id}
                                onClick={() => setFormData({ ...formData, goal: option.id })}
                                className={`p-4 rounded-2xl border text-left transition-all ${formData.goal === option.id
                                    ? 'bg-zinc-800 border-white'
                                    : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <div className="font-bold">{option.label}</div>
                                <div className="text-sm text-gray-400">{option.desc}</div>
                            </button>
                        ))}
                    </div>
                </section>

                {/* LEVEL SECTION */}
                <section className="space-y-4">
                    <h2 className="text-xl font-semibold text-gray-400">Experience Level</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {LEVELS.map(option => (
                            <button
                                key={option.id}
                                onClick={() => setFormData({ ...formData, level: option.id })}
                                className={`p-4 rounded-2xl border text-left transition-all ${formData.level === option.id
                                    ? 'bg-zinc-800 border-white'
                                    : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <div className="font-bold">{option.label}</div>
                                <div className="text-sm text-gray-400">{option.desc}</div>
                            </button>
                        ))}
                    </div>
                </section>

                {/* FREQUENCY SECTION */}
                <section className="space-y-4">
                    <h2 className="text-xl font-semibold text-gray-400">Training Frequency (Days/Week)</h2>
                    <div className="flex gap-3 overflow-x-auto pb-2">
                        {FREQUENCY.map(days => (
                            <button
                                key={days}
                                onClick={() => setFormData({ ...formData, days_per_week: days })}
                                className={`flex-1 min-w-[60px] p-4 rounded-2xl border text-center transition-all ${formData.days_per_week === days
                                    ? 'bg-zinc-800 border-white'
                                    : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <div className="font-bold text-2xl">{days}</div>
                            </button>
                        ))}
                    </div>
                </section>

                {/* EQUIPMENT SECTION */}
                <section className="space-y-4">
                    <h2 className="text-xl font-semibold text-gray-400">Available Equipment</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {EQUIPMENT.map(option => (
                            <button
                                key={option.id}
                                onClick={() => toggleEquipment(option.id)}
                                className={`p-4 rounded-2xl border flex justify-between items-center transition-all ${formData.equipment.includes(option.id)
                                    ? 'bg-zinc-800 border-white'
                                    : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <span className="font-bold">{option.label}</span>
                                {formData.equipment.includes(option.id) && <Check size={20} />}
                            </button>
                        ))}
                    </div>
                </section>
            </div>
        </div>
    )
}

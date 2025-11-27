'use client'

import { useState } from 'react'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'
import { Check, ChevronRight, ChevronLeft, Loader2 } from 'lucide-react'

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

const EQUIPMENT = [
    { id: 'bodyweight', label: 'Bodyweight' },
    { id: 'dumbbell', label: 'Dumbbells' },
    { id: 'barbell', label: 'Barbell' },
    { id: 'resistance_band', label: 'Bands' },
    { id: 'machine', label: 'Machines' },
]

export default function SetupPage() {
    const [step, setStep] = useState(1)
    const [loading, setLoading] = useState(false)
    const router = useRouter()
    const supabase = createClient()

    const [formData, setFormData] = useState({
        goal: '',
        level: '',
        equipment: [] as string[],
        days_per_week: 3
    })

    const handleNext = async () => {
        if (step < 3) {
            setStep(step + 1)
        } else {
            await handleSubmit()
        }
    }

    const handleBack = () => {
        if (step > 1) setStep(step - 1)
    }

    const toggleEquipment = (id: string) => {
        setFormData(prev => ({
            ...prev,
            equipment: prev.equipment.includes(id)
                ? prev.equipment.filter(e => e !== id)
                : [...prev.equipment, id]
        }))
    }

    const handleSubmit = async () => {
        setLoading(true)

        const { data: { user } } = await supabase.auth.getUser()

        if (!user) {
            router.push('/login')
            return
        }

        const { error } = await supabase
            .from('user_profiles')
            .upsert({
                user_id: user.id,
                goal: formData.goal,
                level: formData.level,
                equipment: formData.equipment,
                days_per_week: formData.days_per_week
            })

        if (error) {
            alert('Error saving profile: ' + error.message)
            setLoading(false)
        } else {
            router.push('/generator')
        }
    }

    return (
        <div className="min-h-screen bg-black text-white flex flex-col">
            {/* Progress Bar */}
            <div className="w-full h-1 bg-zinc-900">
                <div
                    className="h-full bg-white transition-all duration-300"
                    style={{ width: `${(step / 3) * 100}%` }}
                />
            </div>

            <div className="flex-1 p-6 flex flex-col max-w-md mx-auto w-full">
                <div className="flex-1">
                    <h1 className="text-3xl font-bold mb-2">
                        {step === 1 && "What's your goal?"}
                        {step === 2 && "Experience level?"}
                        {step === 3 && "Equipment?"}
                    </h1>
                    <p className="text-gray-400 mb-8">
                        {step === 1 && "We'll tailor the intensity based on this."}
                        {step === 2 && "Be honest, we want to avoid injury."}
                        {step === 3 && "Select all that apply."}
                    </p>

                    <div className="space-y-3">
                        {/* STEP 1: GOAL */}
                        {step === 1 && GOALS.map(option => (
                            <button
                                key={option.id}
                                onClick={() => setFormData({ ...formData, goal: option.id })}
                                className={`w-full p-4 rounded-2xl border text-left transition-all ${formData.goal === option.id
                                    ? 'bg-white text-black border-white'
                                    : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <div className="font-bold text-lg">{option.label}</div>
                                <div className={`text-sm ${formData.goal === option.id ? 'text-gray-600' : 'text-gray-400'}`}>
                                    {option.desc}
                                </div>
                            </button>
                        ))}

                        {/* STEP 2: LEVEL */}
                        {step === 2 && LEVELS.map(option => (
                            <button
                                key={option.id}
                                onClick={() => setFormData({ ...formData, level: option.id })}
                                className={`w-full p-4 rounded-2xl border text-left transition-all ${formData.level === option.id
                                    ? 'bg-white text-black border-white'
                                    : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <div className="font-bold text-lg">{option.label}</div>
                                <div className={`text-sm ${formData.level === option.id ? 'text-gray-600' : 'text-gray-400'}`}>
                                    {option.desc}
                                </div>
                            </button>
                        ))}

                        {/* STEP 3: EQUIPMENT */}
                        {step === 3 && EQUIPMENT.map(option => (
                            <button
                                key={option.id}
                                onClick={() => toggleEquipment(option.id)}
                                className={`w-full p-4 rounded-2xl border flex justify-between items-center transition-all ${formData.equipment.includes(option.id)
                                    ? 'bg-white text-black border-white'
                                    : 'bg-zinc-900 border-zinc-800 hover:bg-zinc-800'
                                    }`}
                            >
                                <span className="font-bold text-lg">{option.label}</span>
                                {formData.equipment.includes(option.id) && <Check size={20} />}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Navigation */}
                <div className="mt-8 flex gap-4">
                    {step > 1 && (
                        <button
                            onClick={handleBack}
                            className="p-4 rounded-full bg-zinc-900 border border-zinc-800 hover:bg-zinc-800"
                        >
                            <ChevronLeft />
                        </button>
                    )}

                    <button
                        onClick={handleNext}
                        disabled={
                            (step === 1 && !formData.goal) ||
                            (step === 2 && !formData.level) ||
                            (step === 3 && formData.equipment.length === 0) ||
                            loading
                        }
                        className="flex-1 p-4 bg-white text-black font-bold rounded-2xl hover:bg-gray-200 disabled:opacity-50 flex justify-center items-center gap-2"
                    >
                        {loading ? <Loader2 className="animate-spin" /> : (step === 3 ? 'Finish Setup' : 'Next')}
                        {!loading && step < 3 && <ChevronRight size={20} />}
                    </button>
                </div>
            </div>
        </div>
    )
}

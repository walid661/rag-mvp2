                    </button >
                </div >
            </div >
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

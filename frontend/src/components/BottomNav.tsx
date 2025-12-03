'use client'

import { usePathname, useRouter } from 'next/navigation'
import { Home, Dumbbell, User } from 'lucide-react'

export default function BottomNav() {
    const pathname = usePathname()
    const router = useRouter()

    // Don't show on login or setup pages
    if (pathname === '/login' || pathname === '/setup') {
        return null
    }

    const isActive = (path: string) => pathname === path

    return (
        <div className="fixed bottom-0 left-0 right-0 bg-zinc-900/90 backdrop-blur-lg border-t border-zinc-800 pb-safe z-50 md:hidden">
            <div className="flex justify-around items-center h-16">
                <button
                    onClick={() => router.push('/dashboard')}
                    className={`flex flex-col items-center gap-1 p-2 transition-colors ${isActive('/dashboard') ? 'text-white' : 'text-gray-500 hover:text-gray-300'
                        }`}
                >
                    <Home size={24} strokeWidth={isActive('/dashboard') ? 2.5 : 2} />
                    <span className="text-[10px] font-medium">Home</span>
                </button>

                <button
                    onClick={() => router.push('/my-programs')}
                    className={`flex flex-col items-center gap-1 p-2 transition-colors ${isActive('/my-programs') ? 'text-white' : 'text-gray-500 hover:text-gray-300'
                        }`}
                >
                    <Dumbbell size={24} strokeWidth={isActive('/my-programs') ? 2.5 : 2} />
                    <span className="text-[10px] font-medium">Programs</span>
                </button>

                <button
                    onClick={() => router.push('/profile')}
                    className={`flex flex-col items-center gap-1 p-2 transition-colors ${isActive('/profile') ? 'text-white' : 'text-gray-500 hover:text-gray-300'
                        }`}
                >
                    <User size={24} strokeWidth={isActive('/profile') ? 2.5 : 2} />
                    <span className="text-[10px] font-medium">Profile</span>
                </button>
            </div>
        </div>
    )
}

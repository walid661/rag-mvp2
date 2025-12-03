import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
    let response = NextResponse.next({
        request: {
            headers: request.headers,
        },
    })

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll()
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) =>
                        request.cookies.set(name, value)
                    )
                    response = NextResponse.next({
                        request,
                    })
                    cookiesToSet.forEach(({ name, value, options }) =>
                        response.cookies.set(name, value, options)
                    )
                },
            },
        }
    )
    const {
        data: { user },
    } = await supabase.auth.getUser()

    // Protected routes logic
    if (request.nextUrl.pathname.startsWith('/dashboard') ||
        request.nextUrl.pathname.startsWith('/profile') ||
        request.nextUrl.pathname.startsWith('/my-programs') ||
        request.nextUrl.pathname.startsWith('/setup')) {

        if (!user) {
            return NextResponse.redirect(new URL('/login', request.url))
        }

        // Check profile existence
        const { data: profile } = await supabase
            .from('user_profiles')
            .select('id')
            .eq('user_id', user.id)
            .single()

        const isSetupPage = request.nextUrl.pathname === '/setup'

        if (!profile && !isSetupPage) {
            return NextResponse.redirect(new URL('/setup', request.url))
        }

        if (profile && isSetupPage) {
            return NextResponse.redirect(new URL('/dashboard', request.url))
        }
    }

    return response
}

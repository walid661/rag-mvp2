const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function generateProgram(token: string, body: any = {}) {
    const res = await fetch(`${API_URL}/generate_plan`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    })

    if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to generate plan')
    }

    return res.json()
}

export async function chatCoach(token: string, query: string, context?: any, context_text?: string) {
    const res = await fetch(`${API_URL}/chat_coach`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query,
            context_exercise: context,
            context_text: context_text
        })
    })

    if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to chat with coach')
    }

    return res.json()
}

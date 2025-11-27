const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function generateProgram(token: string) {
    const res = await fetch(`${API_URL}/generate_plan`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })

    if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to generate plan')
    }

    return res.json()
}

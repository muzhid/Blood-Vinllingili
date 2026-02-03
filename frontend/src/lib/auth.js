
export const fetchWithAuth = async (url, options = {}) => {
    // 1. Get Token
    const token = localStorage.getItem('access_token')

    // 2. Prepare Headers
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    // 3. Make Request
    const response = await fetch(url, {
        ...options,
        headers,
    })

    // 4. Intercept 401 (Unauthorized)
    if (response.status === 401) {
        console.warn("Session expired. Logging out.")
        // Clear Storage
        localStorage.removeItem('admin_user')
        localStorage.removeItem('access_token')

        // Force Reload/Redirect to Login
        window.location.href = '/'
        return null
    }

    return response
}

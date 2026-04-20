// static/js/utils.js

/**
 * Gets the current base URL of the application.
 * @param {string} path - The path to append.
 * @returns {string} The absolute URL.
 */
export function getAbsoluteUrl(path) {
    // This is a simple implementation for a Flask app running locally.
    // In a production environment, this should be handled by a proper config.
    const baseUrl = window.location.origin;
    return `${baseUrl}${path}`;
}

/**
 * Gets the user ID from localStorage or session.
 * @returns {string|null} The user ID.
 */
export function getUserId() {
    return localStorage.getItem('finny_user_id');
}

/**
 * Saves the user ID to localStorage.
 * @param {string} userId - The ID of the authenticated user.
 */
export function saveUserId(userId) {
    localStorage.setItem('finny_user_id', userId);
}

/**
 * Clears the user session data.
 */
export function clearUserSession() {
    localStorage.removeItem('finny_user_id');
    // Note: We don't interact directly with Flask session from client-side JS.
    // Clearing the local storage item is sufficient for redirecting/blocking.
}

/**
 * Generic function to handle API fetching with JSON content type.
 * @param {string} url - The API endpoint URL.
 * @param {string} method - HTTP method (GET, POST).
 * @param {object} body - Data to send (for POST).
 * @returns {Promise<object>} The parsed JSON response.
 */
export async function apiFetch(url, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        // Throw an error with the message from the API response
        throw new Error(data.message || `API call failed with status: ${response.status}`);
    }

    return data;
}
// static/js/auth.js

import { getAbsoluteUrl, saveUserId } from './utils.js';

/**
 * Handles the login form submission.
 * @param {Event} event - The form submission event.
 */
async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    const button = document.getElementById('login-button');
    const errorMessage = document.getElementById('error-message');
    errorMessage.style.display = 'none';
    button.disabled = true;
    button.textContent = 'Logging in...';

    try {
        const response = await fetch(getAbsoluteUrl('/api/login'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        const result = await response.json();
        
        if (response.ok && result.success) {
            saveUserId(result.user_id);
            // Redirect to dashboard
            window.location.href = getAbsoluteUrl('/dashboard');
        } else {
            throw new Error(result.message || 'Login failed.');
        }

    } catch (error) {
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
        button.disabled = false;
        button.textContent = 'Log In';
    }
}

/**
 * Handles the signup form submission.
 * @param {Event} event - The form submission event.
 */
async function handleSignup(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    if (data.password !== data.confirm_password) {
        document.getElementById('error-message').textContent = 'Passwords do not match.';
        document.getElementById('error-message').style.display = 'block';
        return;
    }

    const button = document.getElementById('signup-button');
    const errorMessage = document.getElementById('error-message');
    errorMessage.style.display = 'none';
    button.disabled = true;
    button.textContent = 'Signing up...';

    try {
        const payload = {
            name: data.name,
            email: data.email,
            password: data.password
        };

        const response = await fetch(getAbsoluteUrl('/api/signup'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (response.ok && result.success) {
            saveUserId(result.user_id);
            // Redirect to onboarding page with user_id query param
            window.location.href = getAbsoluteUrl(`/onboarding?user_id=${result.user_id}`);
        } else {
            throw new Error(result.message || 'Signup failed.');
        }

    } catch (error) {
        errorMessage.textContent = error.message;
        errorMessage.style.display = 'block';
        button.disabled = false;
        button.textContent = 'Sign Up';
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
    }
});
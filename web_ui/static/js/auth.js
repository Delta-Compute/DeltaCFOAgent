/**
 * Authentication JavaScript Handler
 *
 * Handles all authentication interactions including login, register,
 * invitation acceptance, and password reset.
 */

import { signIn, signUp, signInWithGoogle, resetPassword } from './firebase_client.js';

// Utility Functions
function showError(message, elementId = 'errorAlert') {
    const errorEl = document.getElementById(elementId);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
        setTimeout(() => {
            errorEl.style.display = 'none';
        }, 5000);
    }
}

function showSuccess(message, elementId = 'successAlert') {
    const successEl = document.getElementById(elementId);
    if (successEl) {
        successEl.textContent = message;
        successEl.style.display = 'block';
    }
}

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    const textEl = btn.querySelector('.btn-text');
    const loaderEl = btn.querySelector('.btn-loader');

    if (loading) {
        btn.disabled = true;
        if (textEl) textEl.style.display = 'none';
        if (loaderEl) loaderEl.style.display = 'inline-block';
    } else {
        btn.disabled = false;
        if (textEl) textEl.style.display = 'inline';
        if (loaderEl) loaderEl.style.display = 'none';
    }
}

// API Call Helper
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);

    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
        throw new Error(`Server returned non-JSON response: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();

    if (!result.success) {
        throw new Error(result.message || 'An error occurred');
    }

    return result;
}

// Login Page
if (document.getElementById('loginForm')) {
    const form = document.getElementById('loginForm');
    const googleBtn = document.getElementById('googleSignInBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        setLoading('loginBtn', true);

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        try {
            // Sign in with Firebase
            const firebaseResult = await signIn(email, password);

            if (!firebaseResult.success) {
                showError(firebaseResult.message);
                setLoading('loginBtn', false);
                return;
            }

            // Send Firebase token to backend
            const result = await apiCall('/api/auth/login', 'POST', {
                id_token: firebaseResult.idToken
            });

            // Store user data
            localStorage.setItem('user', JSON.stringify(result.user));
            if (result.current_tenant) {
                localStorage.setItem('current_tenant', JSON.stringify(result.current_tenant));
            }

            // Redirect based on user type
            if (result.user.user_type === 'fractional_cfo') {
                window.location.href = '/cfo/dashboard';
            } else {
                window.location.href = '/';
            }

        } catch (error) {
            showError(error.message || 'Failed to login. Please try again.');
            setLoading('loginBtn', false);
        }
    });

    if (googleBtn) {
        googleBtn.addEventListener('click', async () => {
            try {
                const firebaseResult = await signInWithGoogle();

                if (!firebaseResult.success) {
                    showError(firebaseResult.message);
                    return;
                }

                // Send Firebase token to backend
                const result = await apiCall('/api/auth/login', 'POST', {
                    id_token: firebaseResult.idToken
                });

                localStorage.setItem('user', JSON.stringify(result.user));
                if (result.current_tenant) {
                    localStorage.setItem('current_tenant', JSON.stringify(result.current_tenant));
                }

                // Redirect
                if (result.user.user_type === 'fractional_cfo') {
                    window.location.href = '/cfo/dashboard';
                } else {
                    window.location.href = '/';
                }

            } catch (error) {
                showError(error.message || 'Failed to sign in with Google.');
            }
        });
    }
}

// Register Page
if (document.getElementById('registerForm')) {
    const form = document.getElementById('registerForm');
    const googleBtn = document.getElementById('googleSignUpBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        setLoading('registerBtn', true);

        const displayName = document.getElementById('displayName').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const userType = document.querySelector('input[name="userType"]:checked')?.value;

        // Validation
        if (password !== confirmPassword) {
            showError('Passwords do not match');
            setLoading('registerBtn', false);
            return;
        }

        if (password.length < 6) {
            showError('Password must be at least 6 characters');
            setLoading('registerBtn', false);
            return;
        }

        if (!userType) {
            showError('Please select your user type');
            setLoading('registerBtn', false);
            return;
        }

        try {
            // Sign up with Firebase
            const firebaseResult = await signUp(email, password, displayName);

            if (!firebaseResult.success) {
                showError(firebaseResult.message);
                setLoading('registerBtn', false);
                return;
            }

            // Register in backend
            const result = await apiCall('/api/auth/register', 'POST', {
                email,
                password,
                display_name: displayName,
                user_type: userType
            });

            showSuccess('Account created successfully! Redirecting...');

            // Store user data
            localStorage.setItem('user', JSON.stringify(result.user));

            setTimeout(() => {
                if (userType === 'fractional_cfo') {
                    window.location.href = '/cfo/dashboard';
                } else {
                    window.location.href = '/';
                }
            }, 1500);

        } catch (error) {
            showError(error.message || 'Failed to create account. Please try again.');
            setLoading('registerBtn', false);
        }
    });

    if (googleBtn) {
        googleBtn.addEventListener('click', async () => {
            showError('Please select your user type below before signing up with Google.');
        });
    }
}

// Accept Invitation Page
if (document.getElementById('acceptInvitationForm')) {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (!token) {
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('errorState').style.display = 'block';
        document.getElementById('errorMessage').textContent = 'No invitation token provided.';
    } else {
        // Verify invitation
        apiCall(`/api/auth/verify-invitation/${token}`)
            .then(result => {
                const invitation = result.invitation;

                // Check if expired
                if (invitation.is_expired || invitation.status !== 'pending') {
                    document.getElementById('loadingState').style.display = 'none';
                    document.getElementById('errorState').style.display = 'block';
                    document.getElementById('errorMessage').textContent =
                        invitation.is_expired ? 'This invitation has expired.' :
                        `This invitation is ${invitation.status}.`;
                    return;
                }

                // Show invitation details
                document.getElementById('companyName').textContent = invitation.company_name;
                document.getElementById('inviterName').textContent = invitation.invited_by_name;
                document.getElementById('userRole').textContent = invitation.role.replace('_', ' ').toUpperCase();

                const expiresDate = new Date(invitation.expires_at);
                document.getElementById('expiresAt').textContent =
                    `Expires on ${expiresDate.toLocaleDateString()}`;

                document.getElementById('loadingState').style.display = 'none';
                document.getElementById('invitationDetails').style.display = 'block';
            })
            .catch(error => {
                document.getElementById('loadingState').style.display = 'none';
                document.getElementById('errorState').style.display = 'block';
                document.getElementById('errorMessage').textContent = error.message;
            });

        // Handle form submission
        const form = document.getElementById('acceptInvitationForm');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            setLoading('acceptBtn', true);

            const displayName = document.getElementById('displayName').value;
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;

            // Validation
            if (password !== confirmPassword) {
                showError('Passwords do not match');
                setLoading('acceptBtn', false);
                return;
            }

            if (password.length < 6) {
                showError('Password must be at least 6 characters');
                setLoading('acceptBtn', false);
                return;
            }

            try {
                // Accept invitation
                const result = await apiCall(`/api/auth/accept-invitation/${token}`, 'POST', {
                    display_name: displayName,
                    password: password
                });

                showSuccess('Invitation accepted! Redirecting to login...');

                setTimeout(() => {
                    window.location.href = '/auth/login';
                }, 1500);

            } catch (error) {
                showError(error.message || 'Failed to accept invitation. Please try again.');
                setLoading('acceptBtn', false);
            }
        });
    }
}

// Forgot Password Page
if (document.getElementById('forgotPasswordForm')) {
    const form = document.getElementById('forgotPasswordForm');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        setLoading('resetBtn', true);

        const email = document.getElementById('email').value;

        try {
            const result = await resetPassword(email);

            if (!result.success) {
                showError(result.message);
                setLoading('resetBtn', false);
                return;
            }

            showSuccess('Password reset link sent! Please check your email.');
            form.reset();
            setLoading('resetBtn', false);

        } catch (error) {
            showError(error.message || 'Failed to send reset link. Please try again.');
            setLoading('resetBtn', false);
        }
    });
}

// Check if user is already logged in on protected pages
function checkAuth() {
    const publicPages = ['/auth/login', '/auth/register', '/auth/forgot-password', '/auth/accept-invitation'];
    const currentPath = window.location.pathname;

    // If on a public page, don't check auth
    if (publicPages.some(page => currentPath.includes(page))) {
        return;
    }

    // Check if user is logged in
    const user = localStorage.getItem('user');
    if (!user) {
        window.location.href = '/auth/login';
    }
}

// Initialize auth check on page load
document.addEventListener('DOMContentLoaded', () => {
    // Don't check auth on public pages
    const currentPath = window.location.pathname;
    if (!currentPath.includes('/auth/')) {
        checkAuth();
    }
});

// Export functions for use in other modules
export { showError, showSuccess, setLoading, apiCall, checkAuth };

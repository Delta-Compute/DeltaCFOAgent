/**
 * Firebase Client SDK Configuration
 *
 * This module initializes the Firebase Client SDK and provides authentication
 * functions for the frontend application.
 */

// Import Firebase modules (using CDN in HTML)
// Firebase v9+ modular SDK
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut,
    sendPasswordResetEmail,
    sendEmailVerification,
    GoogleAuthProvider,
    signInWithPopup,
    onAuthStateChanged,
    updateProfile
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyCNRnhRXG_MW4MZJjbw9V5KO1DZrkJD3Cg",
    authDomain: "aicfo-473816.firebaseapp.com",
    projectId: "aicfo-473816",
    storageBucket: "aicfo-473816.firebasestorage.app",
    messagingSenderId: "620026562181",
    appId: "1:620026562181:web:05e9ca3e4b868585b04bec"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

/**
 * Sign in with email and password
 * @param {string} email - User's email
 * @param {string} password - User's password
 * @returns {Promise<Object>} User credential and ID token
 */
export async function signIn(email, password) {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const idToken = await userCredential.user.getIdToken();

        return {
            success: true,
            user: {
                uid: userCredential.user.uid,
                email: userCredential.user.email,
                displayName: userCredential.user.displayName,
                emailVerified: userCredential.user.emailVerified
            },
            idToken: idToken
        };
    } catch (error) {
        console.error('Sign in error:', error);
        return {
            success: false,
            error: error.code,
            message: getErrorMessage(error.code)
        };
    }
}

/**
 * Sign up with email and password
 * @param {string} email - User's email
 * @param {string} password - User's password
 * @param {string} displayName - User's display name
 * @returns {Promise<Object>} User credential and ID token
 */
export async function signUp(email, password, displayName) {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);

        // Update profile with display name
        if (displayName) {
            await updateProfile(userCredential.user, {
                displayName: displayName
            });
        }

        // Send email verification
        await sendEmailVerification(userCredential.user);

        const idToken = await userCredential.user.getIdToken();

        return {
            success: true,
            user: {
                uid: userCredential.user.uid,
                email: userCredential.user.email,
                displayName: displayName,
                emailVerified: userCredential.user.emailVerified
            },
            idToken: idToken
        };
    } catch (error) {
        console.error('Sign up error:', error);
        return {
            success: false,
            error: error.code,
            message: getErrorMessage(error.code)
        };
    }
}

/**
 * Sign in with Google
 * @returns {Promise<Object>} User credential and ID token
 */
export async function signInWithGoogle() {
    try {
        const result = await signInWithPopup(auth, googleProvider);
        const idToken = await result.user.getIdToken();

        return {
            success: true,
            user: {
                uid: result.user.uid,
                email: result.user.email,
                displayName: result.user.displayName,
                emailVerified: result.user.emailVerified,
                photoURL: result.user.photoURL
            },
            idToken: idToken
        };
    } catch (error) {
        console.error('Google sign in error:', error);
        return {
            success: false,
            error: error.code,
            message: getErrorMessage(error.code)
        };
    }
}

/**
 * Sign out current user
 * @returns {Promise<Object>} Success status
 */
export async function signOutUser() {
    try {
        await signOut(auth);
        return {
            success: true
        };
    } catch (error) {
        console.error('Sign out error:', error);
        return {
            success: false,
            error: error.code,
            message: getErrorMessage(error.code)
        };
    }
}

/**
 * Send password reset email
 * @param {string} email - User's email
 * @returns {Promise<Object>} Success status
 */
export async function resetPassword(email) {
    try {
        await sendPasswordResetEmail(auth, email);
        return {
            success: true,
            message: 'Password reset email sent successfully'
        };
    } catch (error) {
        console.error('Password reset error:', error);
        return {
            success: false,
            error: error.code,
            message: getErrorMessage(error.code)
        };
    }
}

/**
 * Get current user's ID token
 * @returns {Promise<string|null>} ID token or null if not authenticated
 */
export async function getCurrentUserToken() {
    try {
        const user = auth.currentUser;
        if (user) {
            return await user.getIdToken();
        }
        return null;
    } catch (error) {
        console.error('Error getting user token:', error);
        return null;
    }
}

/**
 * Get current user
 * @returns {Object|null} Current user or null if not authenticated
 */
export function getCurrentUser() {
    const user = auth.currentUser;
    if (user) {
        return {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
            emailVerified: user.emailVerified,
            photoURL: user.photoURL
        };
    }
    return null;
}

/**
 * Listen to authentication state changes
 * @param {Function} callback - Callback function to handle auth state changes
 * @returns {Function} Unsubscribe function
 */
export function onAuthChange(callback) {
    return onAuthStateChanged(auth, (user) => {
        if (user) {
            callback({
                authenticated: true,
                user: {
                    uid: user.uid,
                    email: user.email,
                    displayName: user.displayName,
                    emailVerified: user.emailVerified,
                    photoURL: user.photoURL
                }
            });
        } else {
            callback({
                authenticated: false,
                user: null
            });
        }
    });
}

/**
 * Refresh current user's ID token
 * @returns {Promise<string|null>} Refreshed ID token or null
 */
export async function refreshUserToken() {
    try {
        const user = auth.currentUser;
        if (user) {
            return await user.getIdToken(true); // Force refresh
        }
        return null;
    } catch (error) {
        console.error('Error refreshing user token:', error);
        return null;
    }
}

/**
 * Send email verification to current user
 * @returns {Promise<Object>} Success status
 */
export async function sendVerificationEmail() {
    try {
        const user = auth.currentUser;
        if (user) {
            await sendEmailVerification(user);
            return {
                success: true,
                message: 'Verification email sent successfully'
            };
        }
        return {
            success: false,
            message: 'No user is currently signed in'
        };
    } catch (error) {
        console.error('Error sending verification email:', error);
        return {
            success: false,
            error: error.code,
            message: getErrorMessage(error.code)
        };
    }
}

/**
 * Convert Firebase error codes to user-friendly messages
 * @param {string} errorCode - Firebase error code
 * @returns {string} User-friendly error message
 */
function getErrorMessage(errorCode) {
    const errorMessages = {
        'auth/email-already-in-use': 'This email is already registered. Please sign in or use a different email.',
        'auth/invalid-email': 'Please enter a valid email address.',
        'auth/operation-not-allowed': 'This operation is not allowed. Please contact support.',
        'auth/weak-password': 'Password should be at least 6 characters long.',
        'auth/user-disabled': 'This account has been disabled. Please contact support.',
        'auth/user-not-found': 'No account found with this email. Please check your email or sign up.',
        'auth/wrong-password': 'Incorrect password. Please try again or reset your password.',
        'auth/too-many-requests': 'Too many failed attempts. Please try again later.',
        'auth/network-request-failed': 'Network error. Please check your internet connection.',
        'auth/popup-closed-by-user': 'Sign in popup was closed. Please try again.',
        'auth/cancelled-popup-request': 'Only one popup request is allowed at a time.',
        'auth/invalid-credential': 'Invalid credentials. Please check your email and password.',
        'auth/account-exists-with-different-credential': 'An account already exists with this email using a different sign-in method.'
    };

    return errorMessages[errorCode] || 'An error occurred. Please try again.';
}

// Export auth instance for direct access if needed
export { auth };

// Make functions available globally for non-module scripts
window.FirebaseAuth = {
    signIn,
    signUp,
    signInWithGoogle,
    signOutUser,
    resetPassword,
    getCurrentUserToken,
    getCurrentUser,
    onAuthChange,
    refreshUserToken,
    sendVerificationEmail,
    auth
};

console.log('Firebase Client SDK initialized successfully');

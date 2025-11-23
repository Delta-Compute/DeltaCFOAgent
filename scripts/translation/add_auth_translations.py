#!/usr/bin/env python3
"""
Add i18n translations to all auth pages (login, register, forgot_password, profile, accept_invitation)
"""

import re
import os

def translate_auth_page(filename, replacements):
    """Apply translations to a specific auth page"""
    filepath = f'web_ui/templates/auth/{filename}'

    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        return 0

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    modified_content = content
    changes_made = []

    for pattern, replacement, description in replacements:
        count = len(re.findall(pattern, modified_content))
        if count > 0:
            modified_content = re.sub(pattern, replacement, modified_content)
            changes_made.append(f"  ✓ {description}: {count}")
        else:
            changes_made.append(f"  ✗ {description}: NOT FOUND")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(modified_content)

    print(f"\n{filename}:")
    print("\n".join(changes_made))
    return len([c for c in changes_made if "✓" in c])

# ===== LOGIN.HTML =====
login_replacements = [
    (r'(<title>)Login - Delta CFO Agent(</title>)',
     r'\1<span data-i18n="auth.login.pageTitle">Login</span> - Delta CFO Agent\2',
     'Page title'),

    (r'(<p>)AI-Powered Financial Intelligence(</p>)',
     r'\1<span data-i18n="auth.login.tagline">AI-Powered Financial Intelligence</span>\2',
     'Tagline'),

    (r'(class="tab[^"]*">)Login(<)',
     r'\1<span data-i18n="auth.login.tab">Login</span>\2',
     'Login tab'),

    (r'(class="tab[^"]*">)Register(<)',
     r'\1<span data-i18n="auth.login.registerTab">Register</span>\2',
     'Register tab'),

    (r'(<label for="email">)Email Address(</label>)',
     r'\1<span data-i18n="auth.login.emailLabel">Email Address</span>\2',
     'Email label'),

    (r'placeholder="your@email\.com"',
     r'data-i18n-attr="placeholder" data-i18n="auth.login.emailPlaceholder" placeholder="your@email.com"',
     'Email placeholder'),

    (r'(<label for="password">)Password(</label>)',
     r'\1<span data-i18n="auth.login.passwordLabel">Password</span>\2',
     'Password label'),

    (r'placeholder="Enter your password"',
     r'data-i18n-attr="placeholder" data-i18n="auth.login.passwordPlaceholder" placeholder="Enter your password"',
     'Password placeholder'),

    (r'(<span>)Remember me(</span>)',
     r'\1<span data-i18n="auth.login.rememberMe">Remember me</span>\2',
     'Remember me'),

    (r'(<a[^>]*class="forgot-link">)Forgot password\?(</a>)',
     r'\1<span data-i18n="auth.login.forgotPassword">Forgot password?</span>\2',
     'Forgot password'),

    (r'(<span class="btn-text">)Sign In(</span>)',
     r'\1<span data-i18n="auth.login.signInButton">Sign In</span>\2',
     'Sign In button'),

    (r'(class="btn-google"[^>]*>[\s\S]*?)Continue with Google(</button>)',
     r'\1<span data-i18n="auth.login.googleButton">Continue with Google</span>\2',
     'Google button'),

    (r'(<p>)Don\'t have an account\? (<a[^>]*>)Register here(</a>)(</p>)',
     r'\1<span data-i18n="auth.login.noAccount">Don\'t have an account?</span> \2<span data-i18n="auth.login.registerLink">Register here</span>\3\4',
     'Footer text'),
]

# ===== REGISTER.HTML =====
register_replacements = [
    (r'(<title>)Register - Delta CFO Agent(</title>)',
     r'\1<span data-i18n="auth.register.pageTitle">Register</span> - Delta CFO Agent\2',
     'Page title'),

    (r'(<p>)Create Your Account(</p>)',
     r'\1<span data-i18n="auth.register.tagline">Create Your Account</span>\2',
     'Tagline'),

    (r'(<label for="displayName">)Full Name(</label>)',
     r'\1<span data-i18n="auth.register.fullNameLabel">Full Name</span>\2',
     'Full Name label'),

    (r'placeholder="John Doe"',
     r'data-i18n-attr="placeholder" data-i18n="auth.register.fullNamePlaceholder" placeholder="John Doe"',
     'Full Name placeholder'),

    (r'placeholder="At least 6 characters"',
     r'data-i18n-attr="placeholder" data-i18n="auth.register.passwordPlaceholder" placeholder="At least 6 characters"',
     'Password placeholder'),

    (r'(<small class="form-hint">)Must be at least 6 characters long(</small>)',
     r'\1<span data-i18n="auth.register.passwordHint">Must be at least 6 characters long</span>\2',
     'Password hint'),

    (r'(<label for="confirmPassword">)Confirm Password(</label>)',
     r'\1<span data-i18n="auth.register.confirmPasswordLabel">Confirm Password</span>\2',
     'Confirm Password label'),

    (r'placeholder="Re-enter password"',
     r'data-i18n-attr="placeholder" data-i18n="auth.register.confirmPasswordPlaceholder" placeholder="Re-enter password"',
     'Confirm Password placeholder'),

    (r'(<label>)I am a:(</label>)',
     r'\1<span data-i18n="auth.register.userTypeLabel">I am a:</span>\2',
     'User type label'),

    (r'(<strong>)Fractional CFO(</strong>)',
     r'\1<span data-i18n="auth.register.fractionalCFO">Fractional CFO</span>\2',
     'Fractional CFO option'),

    (r'(<small>)Manage multiple client businesses(</small>)',
     r'\1<span data-i18n="auth.register.fractionalCFODesc">Manage multiple client businesses</span>\2',
     'Fractional CFO description'),

    (r'(<strong>)Business Owner(</strong>)',
     r'\1<span data-i18n="auth.register.businessOwner">Business Owner</span>\2',
     'Business Owner option'),

    (r'(<small>)Manage my company\'s finances(</small>)',
     r'\1<span data-i18n="auth.register.businessOwnerDesc">Manage my company\'s finances</span>\2',
     'Business Owner description'),

    (r'I agree to the',
     r'<span data-i18n="auth.register.agreeToThe">I agree to the</span>',
     'Agree to the'),

    (r'>Terms of Service<',
     r'><span data-i18n="auth.register.termsOfService">Terms of Service</span><',
     'Terms of Service'),

    (r'>Privacy Policy<',
     r'><span data-i18n="auth.register.privacyPolicy">Privacy Policy</span><',
     'Privacy Policy'),

    (r'(<span class="btn-text">)Create Account(</span>)',
     r'\1<span data-i18n="auth.register.createAccountButton">Create Account</span>\2',
     'Create Account button'),

    (r'Sign up with Google',
     r'<span data-i18n="auth.register.googleButton">Sign up with Google</span>',
     'Google button'),

    (r'(<p>)Already have an account\? (<a[^>]*>)Login here(</a>)(</p>)',
     r'\1<span data-i18n="auth.register.haveAccount">Already have an account?</span> \2<span data-i18n="auth.register.loginLink">Login here</span>\3\4',
     'Footer text'),
]

# Run translations
print("="*60)
print("TRANSLATING AUTH PAGES")
print("="*60)

total_login = translate_auth_page('login.html', login_replacements)
total_register = translate_auth_page('register.html', register_replacements)

print("\n" + "="*60)
print(f"✓ COMPLETED: {total_login + total_register} translations applied across auth pages")
print("="*60)

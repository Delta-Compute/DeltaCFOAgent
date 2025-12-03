/**
 * Simple i18n (Internationalization) System
 * Supports English (en), Brazilian Portuguese (pt), and Spanish (es)
 * No dependencies - pure vanilla JavaScript
 */

class I18n {
    constructor() {
        this.currentLang = 'en';
        this.translations = {
            en: null,
            pt: null,
            es: null
        };
        this.supportedLanguages = ['en', 'pt', 'es'];
        this.loaded = false;
    }

    /**
     * Initialize i18n system
     * Loads translation files and sets initial language
     */
    async init() {
        try {
            const savedLang = localStorage.getItem('preferred_language') || 'en';

            await Promise.all([
                this.loadTranslations('en'),
                this.loadTranslations('pt'),
                this.loadTranslations('es')
            ]);

            this.loaded = true;
            await this.setLanguage(savedLang);

            console.log(`i18n initialized with language: ${this.currentLang}`);
        } catch (error) {
            console.error('Failed to initialize i18n:', error);
            this.currentLang = 'en';
        }
    }

    /**
     * Load translation file for a specific language
     */
    async loadTranslations(lang) {
        try {
            const response = await fetch(`/static/locales/${lang}.json`);
            if (!response.ok) {
                throw new Error(`Failed to load ${lang} translations`);
            }
            this.translations[lang] = await response.json();
        } catch (error) {
            console.error(`Error loading ${lang} translations:`, error);
            throw error;
        }
    }

    /**
     * Get translation for a key
     * Supports nested keys with dot notation: "nav.home"
     * Supports variable interpolation: "Hello {name}"
     */
    t(key, vars = {}) {
        if (!this.loaded) {
            console.warn('i18n not yet loaded');
            return key;
        }

        const keys = key.split('.');
        let value = this.translations[this.currentLang];

        for (const k of keys) {
            if (value && typeof value === 'object') {
                value = value[k];
            } else {
                console.warn(`Translation key not found: ${key}`);
                return key;
            }
        }

        if (typeof value !== 'string') {
            console.warn(`Translation value is not a string: ${key}`);
            return key;
        }

        return this.interpolate(value, vars);
    }

    /**
     * Interpolate variables into translation string
     * Example: "Hello {name}" with {name: "John"} => "Hello John"
     */
    interpolate(str, vars) {
        return str.replace(/\{(\w+)\}/g, (match, key) => {
            return vars[key] !== undefined ? vars[key] : match;
        });
    }

    /**
     * Set current language and update UI
     */
    async setLanguage(lang) {
        if (!this.supportedLanguages.includes(lang)) {
            console.error(`Unsupported language: ${lang}`);
            return;
        }

        this.currentLang = lang;
        localStorage.setItem('preferred_language', lang);

        this.updateDOM();

        document.dispatchEvent(new CustomEvent('languageChanged', {
            detail: { language: lang }
        }));
    }

    /**
     * Update all DOM elements with data-i18n attributes
     */
    updateDOM() {
        const elements = document.querySelectorAll('[data-i18n]');

        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const vars = el.getAttribute('data-i18n-vars');

            let parsedVars = {};
            if (vars) {
                try {
                    parsedVars = JSON.parse(vars);
                } catch (e) {
                    console.error('Invalid data-i18n-vars JSON:', vars);
                }
            }

            const translation = this.t(key, parsedVars);

            const attr = el.getAttribute('data-i18n-attr');
            if (attr) {
                el.setAttribute(attr, translation);
            } else {
                // Check if element has child elements that should be preserved
                const childElements = Array.from(el.children);
                if (childElements.length > 0) {
                    // Find the first text node and update only that
                    const textNode = Array.from(el.childNodes).find(n => n.nodeType === Node.TEXT_NODE);
                    if (textNode) {
                        textNode.textContent = translation + ' ';
                    } else {
                        // Insert text before child elements
                        el.insertBefore(document.createTextNode(translation + ' '), el.firstChild);
                    }
                } else {
                    el.textContent = translation;
                }
            }
        });
    }

    /**
     * Get current language
     */
    getLanguage() {
        return this.currentLang;
    }

    /**
     * Check if a language is active
     */
    isLanguage(lang) {
        return this.currentLang === lang;
    }

    /**
     * Get the locale string for the current language
     */
    getLocale() {
        const localeMap = {
            'en': 'en-US',
            'pt': 'pt-BR',
            'es': 'es-419'  // Latin American Spanish
        };
        return localeMap[this.currentLang] || 'en-US';
    }

    /**
     * Format number according to current locale
     */
    formatNumber(num, decimals = 2) {
        return num.toLocaleString(this.getLocale(), {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    /**
     * Format currency according to current locale
     * Uses locale-specific symbol placement
     */
    formatCurrency(amount, decimals = 2) {
        const formatted = this.formatNumber(Math.abs(amount), decimals);
        const symbol = this.t('currency.symbol');

        // Portuguese and Spanish use symbol with space before amount
        if (this.currentLang === 'pt' || this.currentLang === 'es') {
            return `${symbol} ${formatted}`;
        }
        return `${symbol}${formatted}`;
    }

    /**
     * Format currency with specific currency code
     * Handles different decimal places for different currencies
     */
    formatCurrencyWithCode(amount, currencyCode) {
        const currencyConfig = {
            'USD': { symbol: '$', decimals: 2 },
            'EUR': { symbol: 'E', decimals: 2 },
            'GBP': { symbol: 'GBP', decimals: 2 },
            'BRL': { symbol: 'R$', decimals: 2 },
            'ARS': { symbol: '$', decimals: 2 },
            'CLP': { symbol: '$', decimals: 0 },
            'COP': { symbol: '$', decimals: 0 },
            'MXN': { symbol: '$', decimals: 2 },
            'PEN': { symbol: 'S/', decimals: 2 },
            'UYU': { symbol: '$U', decimals: 2 },
            'BOB': { symbol: 'Bs', decimals: 2 },
            'VES': { symbol: 'Bs.S', decimals: 2 },
            'PYG': { symbol: 'Gs', decimals: 0 }
        };

        const config = currencyConfig[currencyCode] || { symbol: currencyCode, decimals: 2 };
        const formatted = this.formatNumber(Math.abs(amount), config.decimals);

        // Portuguese and Spanish use symbol with space before amount
        if (this.currentLang === 'pt' || this.currentLang === 'es') {
            return `${config.symbol} ${formatted}`;
        }
        return `${config.symbol}${formatted}`;
    }

    /**
     * Format date according to current locale
     */
    formatDate(date) {
        const d = new Date(date);
        return d.toLocaleDateString(this.getLocale());
    }
}

const i18n = new I18n();

document.addEventListener('DOMContentLoaded', async () => {
    await i18n.init();
});

window.i18n = i18n;

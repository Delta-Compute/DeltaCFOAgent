/**
 * Simple i18n (Internationalization) System
 * Supports English (en) and Brazilian Portuguese (pt)
 * No dependencies - pure vanilla JavaScript
 */

class I18n {
    constructor() {
        this.currentLang = 'en';
        this.translations = {
            en: null,
            pt: null
        };
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
                this.loadTranslations('pt')
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
        if (!['en', 'pt'].includes(lang)) {
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
                el.textContent = translation;
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
     * Format number according to current locale
     */
    formatNumber(num, decimals = 2) {
        if (this.currentLang === 'pt') {
            return num.toLocaleString('pt-BR', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            });
        }
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    /**
     * Format currency according to current locale
     */
    formatCurrency(amount, decimals = 2) {
        const formatted = this.formatNumber(Math.abs(amount), decimals);
        const symbol = this.t('currency.symbol');

        if (this.currentLang === 'pt') {
            return `${symbol} ${formatted}`;
        }
        return `${symbol}${formatted}`;
    }

    /**
     * Format date according to current locale
     */
    formatDate(date) {
        const d = new Date(date);
        if (this.currentLang === 'pt') {
            return d.toLocaleDateString('pt-BR');
        }
        return d.toLocaleDateString('en-US');
    }
}

const i18n = new I18n();

document.addEventListener('DOMContentLoaded', async () => {
    await i18n.init();
});

window.i18n = i18n;

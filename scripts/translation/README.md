# Translation Helper Scripts

This directory contains Python scripts used to add i18n translation attributes to HTML templates.

## Scripts

- `add_revenue_translations.py` - Adds data-i18n attributes to revenue.html (main UI elements)
- `add_revenue_js_translations.py` - Adds data-i18n attributes to JavaScript-generated content in revenue.html
- `add_revenue_final_translations.py` - Adds final batch of translations (buttons, modals, etc.) to revenue.html
- `add_workforce_translations.py` - Adds data-i18n attributes to workforce.html
- `translate_users_tenant_whitelisted.py` - Adds data-i18n attributes to users.html

## Usage

These scripts use regex patterns to find and replace English text with translation-enabled markup.

Example:
```bash
python3 add_revenue_translations.py
```

The scripts:
1. Read the target HTML file
2. Apply regex replacements to add data-i18n attributes
3. Write the modified content back to the file
4. Report which translations were successfully applied

## Translation System

The application uses `i18n.js` with JSON translation files:
- `/web_ui/static/locales/en.json` - English translations
- `/web_ui/static/locales/pt.json` - Portuguese translations

Translation attributes:
- `data-i18n="key.path"` - Translates text content
- `data-i18n-attr="placeholder"` - Translates attributes (like placeholder)
- Dynamic content uses `window.i18n.updateDOM()` after rendering

## Note

These are helper scripts created during the translation process. They can be used as reference for translating additional pages.

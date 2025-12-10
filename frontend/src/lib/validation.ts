// Field validation utilities for transaction editing

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

// Field-specific validators
const validators: Record<string, (value: string) => ValidationResult> = {
  category: (value: string) => {
    if (!value || value.trim() === "") {
      return { valid: false, error: "Category cannot be empty" };
    }
    if (value.length > 100) {
      return { valid: false, error: "Category must be less than 100 characters" };
    }
    return { valid: true };
  },

  subcategory: (value: string) => {
    if (value.length > 100) {
      return { valid: false, error: "Subcategory must be less than 100 characters" };
    }
    // Subcategory can be empty
    return { valid: true };
  },

  entity_name: (value: string) => {
    if (value.length > 200) {
      return { valid: false, error: "Entity name must be less than 200 characters" };
    }
    // Entity can be empty
    return { valid: true };
  },

  justification: (value: string) => {
    if (value.length > 1000) {
      return { valid: false, error: "Justification must be less than 1000 characters" };
    }
    return { valid: true };
  },

  amount: (value: string) => {
    if (!value || value.trim() === "") {
      return { valid: false, error: "Amount cannot be empty" };
    }
    const num = parseFloat(value);
    if (isNaN(num)) {
      return { valid: false, error: "Amount must be a valid number" };
    }
    return { valid: true };
  },

  date: (value: string) => {
    if (!value || value.trim() === "") {
      return { valid: false, error: "Date cannot be empty" };
    }
    const date = new Date(value);
    if (isNaN(date.getTime())) {
      return { valid: false, error: "Invalid date format" };
    }
    return { valid: true };
  },
};

// Validate a single field
export function validateField(field: string, value: string): ValidationResult {
  const validator = validators[field];
  if (!validator) {
    // No specific validation for this field, allow it
    return { valid: true };
  }
  return validator(value);
}

// Validate multiple fields
export function validateFields(
  fields: Record<string, string>
): Record<string, ValidationResult> {
  const results: Record<string, ValidationResult> = {};
  for (const [field, value] of Object.entries(fields)) {
    results[field] = validateField(field, value);
  }
  return results;
}

// Check if all validations passed
export function allValid(results: Record<string, ValidationResult>): boolean {
  return Object.values(results).every((r) => r.valid);
}

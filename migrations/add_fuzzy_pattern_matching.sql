-- Migration: Add Fuzzy Pattern Matching for Auto-Learning
-- Description: Implements keyword-based and trigram similarity matching
-- Date: 2025-11-17

-- Enable PostgreSQL trigram extension for fuzzy text matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Create function to extract keywords from transaction descriptions
-- Removes numbers, amounts, dates, and common words
CREATE OR REPLACE FUNCTION extract_pattern_keywords(description TEXT)
RETURNS TEXT AS $$
DECLARE
    keywords TEXT;
    cleaned TEXT;
BEGIN
    -- Convert to lowercase
    cleaned := LOWER(description);

    -- Remove common patterns that vary between similar transactions:
    -- - Dollar amounts: $123.45, $1,234.56
    cleaned := REGEXP_REPLACE(cleaned, '\$[\d,]+\.?\d*', '', 'g');

    -- - Crypto amounts: 0.00123456 BTC, 1.234567 ETH
    cleaned := REGEXP_REPLACE(cleaned, '[\d\.]+\s*(btc|eth|usdt|tao|ada|sol|matic|bnb)', '', 'gi');

    -- - Dates: 2024-01-15, 01/15/2024, Jan 15
    cleaned := REGEXP_REPLACE(cleaned, '\d{4}-\d{2}-\d{2}', '', 'g');
    cleaned := REGEXP_REPLACE(cleaned, '\d{1,2}/\d{1,2}/\d{2,4}', '', 'g');

    -- - Standalone numbers and decimals
    cleaned := REGEXP_REPLACE(cleaned, '\b\d+\.?\d*\b', '', 'g');

    -- - @ symbols and extra whitespace
    cleaned := REGEXP_REPLACE(cleaned, '@', '', 'g');
    cleaned := REGEXP_REPLACE(cleaned, '\s+', ' ', 'g');
    cleaned := TRIM(cleaned);

    -- Extract only significant words (length > 2)
    -- This keeps: bitcoin, deposit, received, coinbase, pix, transf, boleto, etc.
    SELECT string_agg(word, ' ' ORDER BY word)
    INTO keywords
    FROM (
        SELECT DISTINCT unnest(regexp_split_to_array(cleaned, '\s+')) AS word
    ) AS words
    WHERE LENGTH(word) > 2;

    RETURN COALESCE(keywords, cleaned);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION extract_pattern_keywords IS 'Extracts significant keywords from transaction descriptions by removing amounts, dates, and numbers';

-- 2. Add normalized pattern column to tracking table
ALTER TABLE user_classification_tracking
ADD COLUMN IF NOT EXISTS normalized_pattern TEXT;

CREATE INDEX IF NOT EXISTS idx_tracking_normalized_pattern
ON user_classification_tracking USING gin (normalized_pattern gin_trgm_ops);

COMMENT ON COLUMN user_classification_tracking.normalized_pattern IS 'Keyword-based normalized pattern for fuzzy matching';

-- 3. Create function to generate fuzzy pattern signature
CREATE OR REPLACE FUNCTION generate_fuzzy_signature(
    p_description TEXT,
    p_field VARCHAR(50),
    p_value TEXT
) RETURNS VARCHAR(255) AS $$
DECLARE
    normalized TEXT;
BEGIN
    -- Extract keywords and create signature
    normalized := extract_pattern_keywords(p_description);
    RETURN MD5(normalized || '::' || p_field || '::' || LOWER(TRIM(p_value)));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_fuzzy_signature IS 'Generates fuzzy signature based on keywords instead of exact description';

-- 4. Update existing tracking records with normalized patterns
UPDATE user_classification_tracking
SET normalized_pattern = extract_pattern_keywords(description_pattern)
WHERE normalized_pattern IS NULL;

-- 5. Create improved pattern suggestion trigger with fuzzy matching
CREATE OR REPLACE FUNCTION check_and_create_pattern_suggestion_v2()
RETURNS TRIGGER AS $$
DECLARE
    v_exact_count INTEGER := 0;
    v_fuzzy_count INTEGER := 0;
    v_existing_suggestion_id INTEGER;
    v_pattern_confidence DECIMAL(3,2);
    v_fuzzy_signature VARCHAR(255);
    v_normalized_pattern TEXT;
BEGIN
    -- Extract normalized pattern for fuzzy matching
    v_normalized_pattern := extract_pattern_keywords(NEW.description_pattern);
    v_fuzzy_signature := MD5(v_normalized_pattern || '::' || NEW.field_changed || '::' || LOWER(TRIM(NEW.new_value)));

    -- Store normalized pattern for future matching
    NEW.normalized_pattern := v_normalized_pattern;

    -- Count exact matches (original logic)
    SELECT COUNT(*) INTO v_exact_count
    FROM user_classification_tracking
    WHERE tenant_id = NEW.tenant_id
      AND pattern_signature = NEW.pattern_signature
      AND created_at >= NOW() - INTERVAL '90 days';

    -- Count fuzzy matches (new logic - uses keywords)
    SELECT COUNT(*) INTO v_fuzzy_count
    FROM user_classification_tracking
    WHERE tenant_id = NEW.tenant_id
      AND field_changed = NEW.field_changed
      AND LOWER(TRIM(new_value)) = LOWER(TRIM(NEW.new_value))
      AND (
          -- Exact signature match
          pattern_signature = NEW.pattern_signature
          OR
          -- Fuzzy signature match (keywords)
          MD5(normalized_pattern || '::' || field_changed || '::' || LOWER(TRIM(new_value))) = v_fuzzy_signature
          OR
          -- Trigram similarity (85% similar)
          normalized_pattern % v_normalized_pattern AND similarity(normalized_pattern, v_normalized_pattern) > 0.85
      )
      AND created_at >= NOW() - INTERVAL '90 days';

    -- Use fuzzy count if higher (more matches found)
    v_fuzzy_count := GREATEST(v_exact_count, v_fuzzy_count);

    -- Threshold: 3 occurrences triggers a suggestion
    IF v_fuzzy_count >= 3 THEN
        -- Check if suggestion already exists (use fuzzy signature)
        SELECT id INTO v_existing_suggestion_id
        FROM pattern_suggestions
        WHERE tenant_id = NEW.tenant_id
          AND (
              pattern_signature = NEW.pattern_signature
              OR pattern_signature = v_fuzzy_signature
          )
          AND status = 'pending'
        LIMIT 1;

        -- Calculate confidence based on consistency
        v_pattern_confidence := LEAST(0.70 + ((v_fuzzy_count - 3) * 0.05), 0.95);

        IF v_existing_suggestion_id IS NULL THEN
            -- Create new pattern suggestion using NORMALIZED keywords
            INSERT INTO pattern_suggestions (
                tenant_id,
                description_pattern,
                pattern_type,
                entity,
                accounting_category,
                accounting_subcategory,
                justification,
                occurrence_count,
                confidence_score,
                pattern_signature,
                supporting_classifications
            )
            SELECT
                NEW.tenant_id,
                '%' || v_normalized_pattern || '%', -- Use keyword pattern
                CASE
                    WHEN NEW.field_changed = 'category' AND NEW.new_value LIKE '%Revenue%' THEN 'revenue'
                    WHEN NEW.field_changed = 'category' AND NEW.new_value LIKE '%Expense%' THEN 'expense'
                    ELSE 'expense'
                END,
                CASE WHEN NEW.field_changed = 'entity' THEN NEW.new_value ELSE NULL END,
                CASE WHEN NEW.field_changed = 'category' THEN NEW.new_value ELSE NULL END,
                CASE WHEN NEW.field_changed = 'subcategory' THEN NEW.new_value ELSE NULL END,
                CASE WHEN NEW.field_changed = 'justification' THEN NEW.new_value ELSE NULL END,
                v_fuzzy_count,
                v_pattern_confidence,
                v_fuzzy_signature, -- Store fuzzy signature
                jsonb_build_array(NEW.id);

            RAISE NOTICE 'FUZZY PATTERN CREATED: % matches of "%"', v_fuzzy_count, v_normalized_pattern;
        ELSE
            -- Update existing suggestion
            UPDATE pattern_suggestions
            SET occurrence_count = v_fuzzy_count,
                confidence_score = v_pattern_confidence,
                supporting_classifications = supporting_classifications || jsonb_build_array(NEW.id),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_existing_suggestion_id;

            RAISE NOTICE 'FUZZY PATTERN UPDATED: % total matches', v_fuzzy_count;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_and_create_pattern_suggestion_v2 IS 'Improved pattern detection with keyword extraction and fuzzy matching';

-- 6. Replace the trigger to use new function
DROP TRIGGER IF EXISTS trigger_check_pattern_suggestion ON user_classification_tracking;
CREATE TRIGGER trigger_check_pattern_suggestion
    BEFORE INSERT ON user_classification_tracking
    FOR EACH ROW
    EXECUTE FUNCTION check_and_create_pattern_suggestion_v2();

COMMENT ON TRIGGER trigger_check_pattern_suggestion ON user_classification_tracking IS 'Auto-creates pattern suggestions using fuzzy keyword matching';

-- 7. Test the keyword extraction function
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TESTING KEYWORD EXTRACTION';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Input: "Bitcoin deposit - 0.0076146 BTC @ $42,776.10 = $325.72 (2024-01-16)"';
    RAISE NOTICE 'Output: "%"', extract_pattern_keywords('Bitcoin deposit - 0.0076146 BTC @ $42,776.10 = $325.72 (2024-01-16)');
    RAISE NOTICE '';
    RAISE NOTICE 'Input: "PIX TRANSF VALMIRA27/10"';
    RAISE NOTICE 'Output: "%"', extract_pattern_keywords('PIX TRANSF VALMIRA27/10');
    RAISE NOTICE '';
    RAISE NOTICE 'Fuzzy matching is now enabled!';
    RAISE NOTICE '========================================';
END $$;

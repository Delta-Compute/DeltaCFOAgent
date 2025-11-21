-- Migration: Lower pattern suggestion threshold from 50 to 3
-- Description: Make pattern learning more responsive by triggering after 3 classifications instead of 50
-- Date: 2025-11-17

CREATE OR REPLACE FUNCTION check_and_create_pattern_suggestion()
RETURNS TRIGGER AS $$
DECLARE
    v_count INTEGER;
    v_existing_suggestion_id INTEGER;
    v_pattern_confidence DECIMAL(3,2);
BEGIN
    -- Count how many times this exact pattern has been classified
    SELECT COUNT(*) INTO v_count
    FROM user_classification_tracking
    WHERE tenant_id = NEW.tenant_id
      AND pattern_signature = NEW.pattern_signature
      AND created_at >= NOW() - INTERVAL '90 days'; -- Only consider last 90 days

    -- UPDATED THRESHOLD: 3 occurrences triggers a suggestion (was 50)
    IF v_count >= 3 THEN
        -- Check if suggestion already exists
        SELECT id INTO v_existing_suggestion_id
        FROM pattern_suggestions
        WHERE tenant_id = NEW.tenant_id
          AND pattern_signature = NEW.pattern_signature
          AND status = 'pending';

        -- Calculate confidence based on consistency
        -- Adjusted formula: starts at 70% for 3 occurrences, scales up to 95% max
        v_pattern_confidence := LEAST(0.70 + ((v_count - 3) * 0.05), 0.95);

        IF v_existing_suggestion_id IS NULL THEN
            -- Create new pattern suggestion
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
                '%' || NEW.description_pattern || '%', -- Add SQL wildcards
                CASE
                    WHEN NEW.field_changed = 'category' AND NEW.new_value LIKE '%Revenue%' THEN 'revenue'
                    WHEN NEW.field_changed = 'category' AND NEW.new_value LIKE '%Expense%' THEN 'expense'
                    ELSE 'expense'
                END,
                CASE WHEN NEW.field_changed = 'entity' THEN NEW.new_value ELSE NULL END,
                CASE WHEN NEW.field_changed = 'category' THEN NEW.new_value ELSE NULL END,
                CASE WHEN NEW.field_changed = 'subcategory' THEN NEW.new_value ELSE NULL END,
                CASE WHEN NEW.field_changed = 'justification' THEN NEW.new_value ELSE NULL END,
                v_count,
                v_pattern_confidence,
                NEW.pattern_signature,
                jsonb_build_array(NEW.id);

            -- Log pattern creation
            RAISE NOTICE 'Pattern suggestion created: % occurrences of signature %', v_count, NEW.pattern_signature;
        ELSE
            -- Update existing suggestion with new occurrence
            UPDATE pattern_suggestions
            SET occurrence_count = v_count,
                confidence_score = v_pattern_confidence,
                supporting_classifications = supporting_classifications || jsonb_build_array(NEW.id),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_existing_suggestion_id;

            RAISE NOTICE 'Pattern suggestion updated: % total occurrences', v_count;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_and_create_pattern_suggestion IS 'Auto-creates pattern suggestions after 3 identical classifications (lowered from 50)';

-- Note: The trigger already exists, this just replaces the function
-- The trigger will automatically use the updated function

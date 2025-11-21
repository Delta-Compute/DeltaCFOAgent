-- Fix Pattern Trigger to Preserve Natural Word Order
--
-- Issue: The current trigger sorts keywords alphabetically, which scrambles the description:
--   "received bitcoin deposit from external" → "account bitcoin deposit external from received"
--
-- Solution: Remove alphabetical sorting and preserve the original word order

BEGIN;

-- Drop the old trigger
DROP TRIGGER IF EXISTS trigger_check_pattern_suggestion ON user_classification_tracking;
DROP FUNCTION IF EXISTS check_and_create_pattern_suggestion_v3();

-- Create improved trigger function with preserved word order
CREATE OR REPLACE FUNCTION check_and_create_pattern_suggestion_v4()
RETURNS TRIGGER AS $$
DECLARE
    v_pattern_signature TEXT;
    v_existing_pattern_id INTEGER;
    v_similar_count INTEGER;
    v_tracking_ids JSONB;
    v_description TEXT;
    v_description_keywords TEXT;
    v_origin_keywords TEXT;
    v_destination_keywords TEXT;
    v_confidence_score NUMERIC;
    v_new_suggestion_id INTEGER;
    v_pattern_words TEXT[];
    v_description_pattern TEXT;
BEGIN
    -- Only process if entity or category was changed
    IF NEW.field_changed NOT IN ('entity', 'category', 'accounting_category', 'subcategory') THEN
        RETURN NEW;
    END IF;

    -- Get the full transaction description
    SELECT description, origin, destination
    INTO v_description, v_origin_keywords, v_destination_keywords
    FROM transactions
    WHERE transaction_id = NEW.transaction_id;

    -- Clean keywords but preserve order
    v_description_keywords := regexp_replace(
        lower(trim(v_description)),
        '[^a-z0-9\s]', '', 'g'
    );

    v_origin_keywords := regexp_replace(
        lower(coalesce(v_origin_keywords, '')),
        '[^a-z0-9\s]', '', 'g'
    );

    v_destination_keywords := regexp_replace(
        lower(coalesce(v_destination_keywords, '')),
        '[^a-z0-9\s]', '', 'g'
    );

    -- Create pattern signature (for deduplication)
    v_pattern_signature := md5(
        concat_ws('|',
            NEW.new_value,
            NEW.field_changed,
            v_description_keywords,
            v_origin_keywords,
            v_destination_keywords
        )
    );

    -- Check if pattern already exists
    SELECT id INTO v_existing_pattern_id
    FROM pattern_suggestions
    WHERE tenant_id = NEW.tenant_id
      AND pattern_signature = v_pattern_signature
    LIMIT 1;

    IF v_existing_pattern_id IS NOT NULL THEN
        -- Update occurrence count
        UPDATE pattern_suggestions
        SET occurrence_count = occurrence_count + 1,
            supporting_classifications = supporting_classifications || jsonb_build_array(NEW.id),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = v_existing_pattern_id;

        RETURN NEW;
    END IF;

    -- Count similar classifications (fuzzy matching using trigram similarity)
    SELECT COUNT(*), jsonb_agg(uct.id)
    INTO v_similar_count, v_tracking_ids
    FROM user_classification_tracking uct
    JOIN transactions t ON uct.transaction_id = t.transaction_id
    WHERE uct.tenant_id = NEW.tenant_id
      AND uct.field_changed = NEW.field_changed
      AND uct.new_value = NEW.new_value
      AND (
          similarity(lower(t.description), v_description_keywords) > 0.3
          OR similarity(lower(coalesce(t.origin, '')), v_origin_keywords) > 0.3
          OR similarity(lower(coalesce(t.destination, '')), v_destination_keywords) > 0.3
      );

    -- Only create suggestion if we have 3+ occurrences
    IF v_similar_count >= 3 THEN
        -- Calculate confidence based on occurrence count
        v_confidence_score := LEAST(0.95, 0.5 + (v_similar_count * 0.05));

        -- Extract significant words (preserve original order, take first 5)
        -- Filter out common stop words
        SELECT array_agg(word)
        INTO v_pattern_words
        FROM (
            SELECT unnest(string_to_array(v_description_keywords, ' ')) as word
            WHERE unnest(string_to_array(v_description_keywords, ' ')) NOT IN (
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being'
            )
            AND length(unnest(string_to_array(v_description_keywords, ' '))) > 2
            LIMIT 5
        ) significant_words;

        -- Build description pattern with preserved order
        IF array_length(v_pattern_words, 1) > 0 THEN
            v_description_pattern := '%' || array_to_string(v_pattern_words, '%') || '%';
        ELSE
            -- Fallback: if no words after filtering, use first 50 chars of description
            v_description_pattern := '%' || substring(v_description_keywords, 1, 50) || '%';
        END IF;

        -- Create pattern suggestion
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
            supporting_classifications,
            status
        )
        VALUES (
            NEW.tenant_id,
            v_description_pattern,
            'expense',
            CASE WHEN NEW.field_changed = 'entity' THEN NEW.new_value ELSE NULL END,
            CASE WHEN NEW.field_changed IN ('category', 'accounting_category') THEN NEW.new_value ELSE NULL END,
            CASE WHEN NEW.field_changed = 'subcategory' THEN NEW.new_value ELSE NULL END,
            'Auto-detected pattern based on ' || v_similar_count || ' similar classifications',
            v_similar_count,
            v_confidence_score,
            v_pattern_signature,
            v_tracking_ids,
            'pending'
        )
        RETURNING id INTO v_new_suggestion_id;

        -- CRITICAL: Send PostgreSQL notification for automatic processing
        PERFORM pg_notify('new_pattern_suggestion', json_build_object(
            'suggestion_id', v_new_suggestion_id,
            'tenant_id', NEW.tenant_id,
            'occurrence_count', v_similar_count,
            'pattern', v_description_pattern
        )::text);

    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate the trigger
CREATE TRIGGER trigger_check_pattern_suggestion
    AFTER INSERT ON user_classification_tracking
    FOR EACH ROW
    EXECUTE FUNCTION check_and_create_pattern_suggestion_v4();

COMMIT;

COMMENT ON FUNCTION check_and_create_pattern_suggestion_v4() IS
'Automatically creates pattern suggestions with preserved word order and sends notifications for LLM validation';

-- Migration: Enhance Pattern Learning with LLM Validation
-- Description: Add LLM validation, remove amount checks, add passive notifications
-- Changes:
--   1. Add origin/destination to user_classification_tracking
--   2. Add LLM validation fields to pattern_suggestions and classification_patterns
--   3. Create pattern_notifications table
--   4. Update trigger to use 3-occurrence threshold
--   5. Add tenant configuration for pattern learning

-- ============================================================================
-- 1. Enhance user_classification_tracking with origin/destination
-- ============================================================================
ALTER TABLE user_classification_tracking
ADD COLUMN IF NOT EXISTS origin TEXT,
ADD COLUMN IF NOT EXISTS destination TEXT;

CREATE INDEX IF NOT EXISTS idx_tracking_origin ON user_classification_tracking(tenant_id, origin);
CREATE INDEX IF NOT EXISTS idx_tracking_destination ON user_classification_tracking(tenant_id, destination);

COMMENT ON COLUMN user_classification_tracking.origin IS 'Transaction origin for similarity matching';
COMMENT ON COLUMN user_classification_tracking.destination IS 'Transaction destination for similarity matching';

-- ============================================================================
-- 2. Add LLM validation tracking to pattern_suggestions
-- ============================================================================
ALTER TABLE pattern_suggestions
ADD COLUMN IF NOT EXISTS llm_validation_result JSONB,
ADD COLUMN IF NOT EXISTS llm_validated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS validation_model VARCHAR(50);

COMMENT ON COLUMN pattern_suggestions.llm_validation_result IS 'Full JSON response from LLM validation';
COMMENT ON COLUMN pattern_suggestions.validation_model IS 'Claude model used for validation (e.g., claude-3-5-sonnet-20241022)';

-- ============================================================================
-- 3. Add LLM validation fields to classification_patterns
-- ============================================================================
ALTER TABLE classification_patterns
ADD COLUMN IF NOT EXISTS created_by VARCHAR(50) DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS llm_confidence_adjustment DECIMAL(3,2) DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS risk_assessment VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_patterns_created_by ON classification_patterns(created_by);

COMMENT ON COLUMN classification_patterns.created_by IS 'Source: manual, llm_validated, user_approved, imported';
COMMENT ON COLUMN classification_patterns.llm_confidence_adjustment IS 'Confidence adjustment from LLM (-0.2 to +0.2)';
COMMENT ON COLUMN classification_patterns.risk_assessment IS 'LLM risk assessment: low, medium, high';

-- ============================================================================
-- 4. Create pattern_notifications table for passive notifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS pattern_notifications (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    pattern_id INTEGER REFERENCES classification_patterns(pattern_id) ON DELETE CASCADE,

    -- Notification details
    notification_type VARCHAR(50) NOT NULL, -- 'pattern_created', 'pattern_activated', 'pattern_deactivated', 'pattern_low_confidence'
    title VARCHAR(255) NOT NULL,
    message TEXT,
    metadata JSONB, -- Additional context (pattern details, stats, etc.)

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,

    CONSTRAINT fk_notification_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE,
    CONSTRAINT chk_notification_type CHECK (notification_type IN
        ('pattern_created', 'pattern_activated', 'pattern_deactivated', 'pattern_low_confidence', 'pattern_rejected'))
);

CREATE INDEX idx_notifications_tenant_unread ON pattern_notifications(tenant_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_pattern ON pattern_notifications(pattern_id);

COMMENT ON TABLE pattern_notifications IS 'Passive notifications for auto-created patterns (no approval required)';
COMMENT ON COLUMN pattern_notifications.notification_type IS 'Type of notification: pattern_created, pattern_activated, pattern_deactivated, pattern_low_confidence, pattern_rejected';
COMMENT ON COLUMN pattern_notifications.priority IS 'Display priority: low, normal, high, urgent';

-- ============================================================================
-- 5. Update check_and_create_pattern_suggestion function to use 3 occurrences
-- ============================================================================
CREATE OR REPLACE FUNCTION check_and_create_pattern_suggestion_v2()
RETURNS TRIGGER AS $$
DECLARE
    v_count INTEGER;
    v_existing_suggestion_id INTEGER;
    v_pattern_confidence DECIMAL(3,2);
    v_similar_records JSONB;
BEGIN
    -- Count how many SIMILAR (not just exact) patterns have been classified
    -- Now uses: description similarity + (origin OR destination match)
    -- Threshold changed from 50 to 3

    SELECT COUNT(*), jsonb_agg(jsonb_build_object('id', id, 'description', description_pattern, 'origin', origin, 'destination', destination))
    INTO v_count, v_similar_records
    FROM user_classification_tracking
    WHERE tenant_id = NEW.tenant_id
      AND field_changed = NEW.field_changed
      AND new_value = NEW.new_value
      AND created_at >= NOW() - INTERVAL '90 days'
      AND (
          -- Description similarity using trigram (requires pg_trgm extension)
          -- OR simple keyword matching as fallback
          description_pattern % NEW.description_pattern
          OR description_pattern ILIKE '%' || (
              SELECT string_agg(word, '%')
              FROM unnest(string_to_array(NEW.description_pattern, ' ')) AS word
              WHERE length(word) > 3
              LIMIT 3
          ) || '%'
      )
      AND (
          -- Origin OR Destination must match
          LOWER(TRIM(origin)) = LOWER(TRIM(NEW.origin))
          OR LOWER(TRIM(destination)) = LOWER(TRIM(NEW.destination))
      );

    -- Threshold: 3 occurrences triggers LLM validation (not auto-creation)
    -- The actual pattern creation happens in Python after LLM validates
    IF v_count >= 3 THEN
        -- Check if suggestion already exists
        SELECT id INTO v_existing_suggestion_id
        FROM pattern_suggestions
        WHERE tenant_id = NEW.tenant_id
          AND pattern_signature = NEW.pattern_signature
          AND status = 'pending';

        -- Calculate initial confidence based on count
        v_pattern_confidence := LEAST(v_count / 10.0 * 0.6, 0.75); -- Max 75% before LLM adjustment

        IF v_existing_suggestion_id IS NULL THEN
            -- Create new pattern suggestion (will be validated by LLM in Python)
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
                '%' || NEW.description_pattern || '%',
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
                v_similar_records,
                'pending' -- Will be processed by LLM validation
            );

            -- Log for debugging
            RAISE NOTICE '3-occurrence pattern detected for LLM validation: % (count: %)', NEW.description_pattern, v_count;
        ELSE
            -- Update existing suggestion
            UPDATE pattern_suggestions
            SET occurrence_count = v_count,
                confidence_score = v_pattern_confidence,
                supporting_classifications = v_similar_records,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_existing_suggestion_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop old trigger and create new one
DROP TRIGGER IF EXISTS trigger_check_pattern_suggestion ON user_classification_tracking;
CREATE TRIGGER trigger_check_pattern_suggestion
    AFTER INSERT ON user_classification_tracking
    FOR EACH ROW
    EXECUTE FUNCTION check_and_create_pattern_suggestion_v2();

COMMENT ON FUNCTION check_and_create_pattern_suggestion_v2 IS 'Updated: 3-occurrence threshold with similarity matching (description + origin/dest)';

-- ============================================================================
-- 6. Add pattern learning configuration to tenant_configuration
-- ============================================================================
ALTER TABLE tenant_configuration
ADD COLUMN IF NOT EXISTS pattern_learning_config JSONB DEFAULT '{
  "enabled": true,
  "min_occurrences": 3,
  "llm_validation": {
    "enabled": true,
    "model": "claude-3-5-sonnet-20241022",
    "auto_create_on_validation": true,
    "require_user_approval_if_medium_risk": false
  },
  "similarity_thresholds": {
    "description_similarity": 0.70,
    "require_origin_or_dest_match": true
  },
  "notifications": {
    "enabled": true,
    "notify_on_pattern_creation": true,
    "notify_on_pattern_deactivation": true
  },
  "pattern_expiry_days": 30
}'::jsonb;

COMMENT ON COLUMN tenant_configuration.pattern_learning_config IS 'Configuration for LLM-validated 3-occurrence pattern learning system';

-- ============================================================================
-- 7. Install pg_trgm extension for similarity matching (if not exists)
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMENT ON EXTENSION pg_trgm IS 'Trigram similarity matching for fuzzy text comparison';

-- Create trigram index on description_pattern for faster similarity searches
CREATE INDEX IF NOT EXISTS idx_tracking_description_trgm ON user_classification_tracking
USING gin (description_pattern gin_trgm_ops);

-- ============================================================================
-- Grant permissions
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON pattern_notifications TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE pattern_notifications_id_seq TO PUBLIC;

-- ============================================================================
-- Migration complete
-- ============================================================================

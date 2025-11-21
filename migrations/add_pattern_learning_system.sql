-- Migration: Add Pattern Learning System
-- Description: Implements auto-learning with user approval workflow
-- Cadence: Suggests patterns after 50 manual classifications

-- 1. Add justification column to classification_patterns table
ALTER TABLE classification_patterns
ADD COLUMN IF NOT EXISTS justification TEXT;

COMMENT ON COLUMN classification_patterns.justification IS 'Standard justification text to apply when this pattern matches';

-- 2. Create table to track manual user classifications
CREATE TABLE IF NOT EXISTS user_classification_tracking (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    transaction_id UUID,

    -- What was changed
    field_changed VARCHAR(50) NOT NULL, -- 'entity', 'category', 'subcategory', 'justification'
    old_value TEXT,
    new_value TEXT NOT NULL,

    -- Pattern detection
    description_pattern TEXT NOT NULL, -- The transaction description that triggered this
    pattern_signature VARCHAR(255), -- Hash of (description_pattern + field_changed + new_value)

    -- Metadata
    confidence_score DECIMAL(3,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tracking_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE
);

CREATE INDEX idx_tracking_tenant ON user_classification_tracking(tenant_id);
CREATE INDEX idx_tracking_signature ON user_classification_tracking(pattern_signature);
CREATE INDEX idx_tracking_created ON user_classification_tracking(created_at DESC);

COMMENT ON TABLE user_classification_tracking IS 'Tracks every manual classification change to identify patterns';
COMMENT ON COLUMN user_classification_tracking.pattern_signature IS 'MD5 hash used to group identical classification patterns';

-- 3. Create table for pending pattern suggestions (awaiting user approval)
CREATE TABLE IF NOT EXISTS pattern_suggestions (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,

    -- Suggested pattern details
    description_pattern TEXT NOT NULL,
    pattern_type VARCHAR(50),
    entity VARCHAR(255),
    accounting_category VARCHAR(100),
    accounting_subcategory VARCHAR(255),
    justification TEXT,

    -- Learning metadata
    occurrence_count INTEGER NOT NULL DEFAULT 0, -- How many times this pattern was observed
    confidence_score DECIMAL(3,2) NOT NULL,
    pattern_signature VARCHAR(255) NOT NULL,

    -- Supporting data (JSON array of tracking IDs that led to this suggestion)
    supporting_classifications JSONB,

    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_suggestion_tenant FOREIGN KEY (tenant_id)
        REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE,
    CONSTRAINT chk_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

CREATE INDEX idx_suggestions_tenant_status ON pattern_suggestions(tenant_id, status);
CREATE INDEX idx_suggestions_signature ON pattern_suggestions(pattern_signature);
CREATE INDEX idx_suggestions_created ON pattern_suggestions(created_at DESC);

COMMENT ON TABLE pattern_suggestions IS 'Auto-learned patterns awaiting user approval (after 50 classifications)';
COMMENT ON COLUMN pattern_suggestions.occurrence_count IS 'Number of identical manual classifications that generated this suggestion';
COMMENT ON COLUMN pattern_suggestions.supporting_classifications IS 'Array of user_classification_tracking IDs that support this pattern';

-- 4. Create function to generate pattern signatures
CREATE OR REPLACE FUNCTION generate_pattern_signature(
    p_description TEXT,
    p_field VARCHAR(50),
    p_value TEXT
) RETURNS VARCHAR(255) AS $$
BEGIN
    RETURN MD5(LOWER(TRIM(p_description)) || '::' || p_field || '::' || LOWER(TRIM(p_value)));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_pattern_signature IS 'Generates consistent hash for pattern matching';

-- 5. Create function to check if pattern suggestion should be created
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

    -- Threshold: 50 occurrences triggers a suggestion
    IF v_count >= 50 THEN
        -- Check if suggestion already exists
        SELECT id INTO v_existing_suggestion_id
        FROM pattern_suggestions
        WHERE tenant_id = NEW.tenant_id
          AND pattern_signature = NEW.pattern_signature
          AND status = 'pending';

        -- Calculate confidence based on consistency
        v_pattern_confidence := LEAST(v_count / 50.0 * 0.8, 0.95); -- Max 95% confidence

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
        ELSE
            -- Update existing suggestion with new occurrence
            UPDATE pattern_suggestions
            SET occurrence_count = v_count,
                confidence_score = v_pattern_confidence,
                supporting_classifications = supporting_classifications || jsonb_build_array(NEW.id),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_existing_suggestion_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. Create trigger to auto-generate suggestions
DROP TRIGGER IF EXISTS trigger_check_pattern_suggestion ON user_classification_tracking;
CREATE TRIGGER trigger_check_pattern_suggestion
    AFTER INSERT ON user_classification_tracking
    FOR EACH ROW
    EXECUTE FUNCTION check_and_create_pattern_suggestion();

COMMENT ON TRIGGER trigger_check_pattern_suggestion ON user_classification_tracking IS 'Auto-creates pattern suggestions after 50 identical classifications';

-- 7. Add priority column to pattern_suggestions for ranking
ALTER TABLE pattern_suggestions
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 500;

COMMENT ON COLUMN pattern_suggestions.priority IS 'Priority for pattern application (lower = higher priority)';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON user_classification_tracking TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON pattern_suggestions TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE user_classification_tracking_id_seq TO PUBLIC;
GRANT USAGE, SELECT ON SEQUENCE pattern_suggestions_id_seq TO PUBLIC;

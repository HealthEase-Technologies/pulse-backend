-- Sprint 7: Custom Thresholds, Anomaly Detection & Alert System
-- Run this in Supabase SQL Editor

-- ============================================================================
-- 1. ALERT THRESHOLDS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS alert_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    set_by_user_id UUID NOT NULL REFERENCES users(id),
    set_by_role TEXT NOT NULL CHECK (set_by_role IN ('patient', 'provider')),
    biomarker_type TEXT NOT NULL CHECK (biomarker_type IN (
        'heart_rate', 'blood_pressure_systolic', 'blood_pressure_diastolic',
        'glucose', 'steps', 'sleep'
    )),
    warning_low FLOAT,
    warning_high FLOAT,
    critical_low FLOAT,
    critical_high FLOAT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Each patient can have at most one patient-set and one provider-set threshold per biomarker
    UNIQUE (patient_user_id, biomarker_type, set_by_role)
);

-- Index for fast lookup by patient
CREATE INDEX IF NOT EXISTS idx_alert_thresholds_patient
    ON alert_thresholds(patient_user_id, biomarker_type);


-- ============================================================================
-- 2. ALERT HISTORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    biomarker_id UUID REFERENCES biomarkers(id),
    biomarker_type TEXT NOT NULL,
    value FLOAT NOT NULL,
    unit TEXT NOT NULL,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('warning', 'critical')),
    alert_direction TEXT CHECK (alert_direction IN ('high', 'low')),
    threshold_id UUID REFERENCES alert_thresholds(id) ON DELETE SET NULL,
    threshold_source TEXT NOT NULL CHECK (threshold_source IN ('provider', 'patient', 'global')),
    threshold_value FLOAT NOT NULL,
    status TEXT NOT NULL DEFAULT 'triggered' CHECK (status IN ('triggered', 'notified', 'acknowledged', 'resolved')),
    notification_channels JSONB DEFAULT '[]'::jsonb,
    notification_attempts INT DEFAULT 0,
    notification_results JSONB DEFAULT '[]'::jsonb,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for patient alert history (newest first)
CREATE INDEX IF NOT EXISTS idx_alert_history_patient
    ON alert_history(patient_user_id, created_at DESC);

-- Partial index for unresolved alerts (fast badge count)
CREATE INDEX IF NOT EXISTS idx_alert_history_unresolved
    ON alert_history(patient_user_id, status)
    WHERE status != 'resolved';


-- ============================================================================
-- 3. ALERT COOLDOWNS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS alert_cooldowns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    biomarker_type TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    last_alerted_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One cooldown record per patient + biomarker + alert type
    UNIQUE (patient_user_id, biomarker_type, alert_type)
);

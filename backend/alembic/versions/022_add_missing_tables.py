"""022: Create 33 missing tables for operations, restaurant extras, and happy hours.

Tables from operations.py (26), restaurant.py (6), and advanced_features.py (1).
"""

from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== operations.py tables (26) =====

    op.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id SERIAL PRIMARY KEY,
            category VARCHAR(50) NOT NULL,
            key VARCHAR(100) NOT NULL,
            value JSONB,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_app_settings_category ON app_settings(category)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS payroll_runs (
            id SERIAL PRIMARY KEY,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            total_gross NUMERIC(12,2) DEFAULT 0,
            total_net NUMERIC(12,2) DEFAULT 0,
            total_tax NUMERIC(12,2) DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            approved_at TIMESTAMP WITH TIME ZONE,
            paid_at TIMESTAMP WITH TIME ZONE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS payroll_entries (
            id SERIAL PRIMARY KEY,
            payroll_run_id INTEGER REFERENCES payroll_runs(id),
            staff_id INTEGER NOT NULL,
            staff_name VARCHAR(200),
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            hours_worked NUMERIC(8,2) DEFAULT 0,
            overtime_hours NUMERIC(8,2) DEFAULT 0,
            hourly_rate NUMERIC(8,2) DEFAULT 0,
            gross_pay NUMERIC(10,2) DEFAULT 0,
            tax NUMERIC(10,2) DEFAULT 0,
            deductions NUMERIC(10,2) DEFAULT 0,
            net_pay NUMERIC(10,2) DEFAULT 0,
            tips NUMERIC(10,2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_payroll_entries_staff ON payroll_entries(staff_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            title VARCHAR(200) NOT NULL,
            message TEXT,
            type VARCHAR(50) DEFAULT 'info',
            category VARCHAR(50),
            read BOOLEAN DEFAULT FALSE,
            action_url VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            channel VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            categories JSONB,
            quiet_hours_start VARCHAR(5),
            quiet_hours_end VARCHAR(5)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_configs (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            type VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            threshold DOUBLE PRECISION,
            channels JSONB,
            recipients JSONB
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS haccp_temperature_logs (
            id SERIAL PRIMARY KEY,
            location VARCHAR(100) NOT NULL,
            equipment VARCHAR(100),
            temperature DOUBLE PRECISION NOT NULL,
            unit VARCHAR(5) DEFAULT 'C',
            min_temp DOUBLE PRECISION,
            max_temp DOUBLE PRECISION,
            status VARCHAR(20) DEFAULT 'normal',
            recorded_by VARCHAR(100),
            notes TEXT,
            recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS haccp_safety_checks (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(50),
            frequency VARCHAR(20) DEFAULT 'daily',
            status VARCHAR(20) DEFAULT 'pending',
            due_date TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            completed_by VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS feedback_reviews (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50) DEFAULT 'internal',
            customer_name VARCHAR(200),
            rating INTEGER,
            text TEXT,
            sentiment VARCHAR(20),
            status VARCHAR(20) DEFAULT 'new',
            response TEXT,
            responded_at TIMESTAMP WITH TIME ZONE,
            responded_by VARCHAR(100),
            visit_date DATE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log_entries (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            user_name VARCHAR(200),
            action VARCHAR(50) NOT NULL,
            entity_type VARCHAR(50),
            entity_id VARCHAR(50),
            details JSONB,
            ip_address VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log_entries(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log_entries(action)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log_entries(entity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log_entries(created_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS vip_customer_links (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER,
            name VARCHAR(200) NOT NULL,
            email VARCHAR(200),
            phone VARCHAR(50),
            tier VARCHAR(50) DEFAULT 'silver',
            points INTEGER DEFAULT 0,
            total_spent NUMERIC(12,2) DEFAULT 0,
            visits INTEGER DEFAULT 0,
            joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            notes TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_vip_customer ON vip_customer_links(customer_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS vip_occasions (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER,
            customer_name VARCHAR(200),
            type VARCHAR(50) NOT NULL,
            occasion_date DATE NOT NULL,
            notes TEXT,
            notification_sent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            type VARCHAR(50) DEFAULT 'dry',
            location_id INTEGER,
            address TEXT,
            capacity INTEGER,
            temperature_min DOUBLE PRECISION,
            temperature_max DOUBLE PRECISION,
            manager VARCHAR(200),
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS warehouse_transfers (
            id SERIAL PRIMARY KEY,
            from_warehouse_id INTEGER REFERENCES warehouses(id),
            to_warehouse_id INTEGER REFERENCES warehouses(id),
            product_id INTEGER,
            product_name VARCHAR(200),
            quantity NUMERIC(10,2) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            notes TEXT,
            created_by VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            type VARCHAR(50) DEFAULT 'percentage',
            value NUMERIC(10,2),
            min_order_amount NUMERIC(10,2),
            max_discount NUMERIC(10,2),
            code VARCHAR(50),
            start_date TIMESTAMP WITH TIME ZONE,
            end_date TIMESTAMP WITH TIME ZONE,
            active BOOLEAN DEFAULT TRUE,
            usage_count INTEGER DEFAULT 0,
            usage_limit INTEGER,
            applicable_items JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            icon VARCHAR(50),
            category VARCHAR(50),
            criteria JSONB,
            points INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            type VARCHAR(50) DEFAULT 'individual',
            target_value DOUBLE PRECISION,
            reward_points INTEGER DEFAULT 0,
            reward_description VARCHAR(200),
            start_date DATE,
            end_date DATE,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS staff_achievements (
            id SERIAL PRIMARY KEY,
            staff_id INTEGER NOT NULL,
            staff_name VARCHAR(200),
            badge_id INTEGER REFERENCES badges(id),
            badge_name VARCHAR(200),
            points INTEGER DEFAULT 0,
            earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_achievements_staff ON staff_achievements(staff_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS staff_points (
            id SERIAL PRIMARY KEY,
            staff_id INTEGER NOT NULL UNIQUE,
            staff_name VARCHAR(200),
            total_points INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            badges_earned INTEGER DEFAULT 0,
            challenges_completed INTEGER DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_staff_points_staff ON staff_points(staff_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS risk_alerts (
            id SERIAL PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) DEFAULT 'medium',
            title VARCHAR(200) NOT NULL,
            description TEXT,
            staff_id INTEGER,
            staff_name VARCHAR(200),
            amount NUMERIC(10,2),
            status VARCHAR(20) DEFAULT 'open',
            acknowledged_by VARCHAR(100),
            acknowledged_at TIMESTAMP WITH TIME ZONE,
            details JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS referral_programs (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            reward_type VARCHAR(50) DEFAULT 'discount',
            reward_value NUMERIC(10,2) DEFAULT 0,
            referee_reward_value NUMERIC(10,2) DEFAULT 0,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS referral_records (
            id SERIAL PRIMARY KEY,
            referrer_name VARCHAR(200),
            referrer_email VARCHAR(200),
            referee_name VARCHAR(200),
            referee_email VARCHAR(200),
            status VARCHAR(20) DEFAULT 'pending',
            reward_claimed BOOLEAN DEFAULT FALSE,
            program_id INTEGER REFERENCES referral_programs(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tax_filings (
            id SERIAL PRIMARY KEY,
            period VARCHAR(20) NOT NULL,
            year INTEGER NOT NULL,
            total_revenue NUMERIC(12,2) DEFAULT 0,
            total_tax NUMERIC(12,2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pending',
            due_date DATE,
            filed_at TIMESTAMP WITH TIME ZONE,
            filed_by VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(100) NOT NULL,
            period VARCHAR(20),
            year INTEGER,
            month INTEGER,
            budgeted_amount NUMERIC(12,2) DEFAULT 0,
            actual_amount NUMERIC(12,2) DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_reconciliations (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            status VARCHAR(20) DEFAULT 'open',
            expected_cash NUMERIC(10,2) DEFAULT 0,
            actual_cash NUMERIC(10,2) DEFAULT 0,
            cash_variance NUMERIC(10,2) DEFAULT 0,
            total_sales NUMERIC(12,2) DEFAULT 0,
            card_total NUMERIC(12,2) DEFAULT 0,
            cash_total NUMERIC(12,2) DEFAULT 0,
            completed_by VARCHAR(100),
            completed_at TIMESTAMP WITH TIME ZONE,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS shift_schedules (
            id SERIAL PRIMARY KEY,
            staff_id INTEGER NOT NULL,
            staff_name VARCHAR(200),
            role VARCHAR(50),
            date DATE NOT NULL,
            start_time VARCHAR(10),
            end_time VARCHAR(10),
            status VARCHAR(20) DEFAULT 'scheduled',
            break_minutes INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_shift_schedules_staff ON shift_schedules(staff_id)")

    # ===== restaurant.py tables (6) =====

    op.execute("""
        CREATE TABLE IF NOT EXISTS menu_categories (
            id SERIAL PRIMARY KEY,
            name_bg VARCHAR(200) NOT NULL,
            name_en VARCHAR(200),
            description_bg TEXT DEFAULT '',
            description_en TEXT DEFAULT '',
            icon VARCHAR(10) DEFAULT '🍽',
            color VARCHAR(20) DEFAULT '#3B82F6',
            image_url VARCHAR(500),
            sort_order INTEGER DEFAULT 0,
            active BOOLEAN DEFAULT TRUE,
            parent_id INTEGER REFERENCES menu_categories(id),
            visibility VARCHAR(20) DEFAULT 'all',
            tax_rate NUMERIC(5,2),
            printer_id INTEGER,
            display_on_kiosk BOOLEAN DEFAULT TRUE,
            display_on_app BOOLEAN DEFAULT TRUE,
            display_on_web BOOLEAN DEFAULT TRUE,
            schedule JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS modifier_groups (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            min_selections INTEGER DEFAULT 0,
            max_selections INTEGER DEFAULT 1,
            active BOOLEAN DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS modifier_options (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES modifier_groups(id),
            name VARCHAR(200) NOT NULL,
            price_adjustment NUMERIC(10,2) DEFAULT 0,
            available BOOLEAN DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS menu_item_modifier_groups (
            id SERIAL PRIMARY KEY,
            menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
            modifier_group_id INTEGER NOT NULL REFERENCES modifier_groups(id),
            sort_order INTEGER DEFAULT 0
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS combo_meals (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            price NUMERIC(10,2) NOT NULL,
            image_url VARCHAR(500),
            available BOOLEAN DEFAULT TRUE,
            featured BOOLEAN DEFAULT FALSE,
            category VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS combo_items (
            id SERIAL PRIMARY KEY,
            combo_id INTEGER NOT NULL REFERENCES combo_meals(id),
            menu_item_id INTEGER REFERENCES menu_items(id),
            name VARCHAR(200) NOT NULL,
            quantity INTEGER DEFAULT 1,
            is_choice BOOLEAN DEFAULT FALSE,
            choice_group VARCHAR(100)
        )
    """)

    # ===== advanced_features.py table (1) =====

    op.execute("""
        CREATE TABLE IF NOT EXISTS happy_hours (
            id SERIAL PRIMARY KEY,
            location_id INTEGER,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            days JSONB NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            start_date DATE,
            end_date DATE,
            discount_type VARCHAR(20) NOT NULL,
            discount_value NUMERIC(10,2) NOT NULL,
            applies_to VARCHAR(50) NOT NULL,
            category_ids JSONB,
            item_ids JSONB,
            max_per_customer INTEGER,
            min_purchase NUMERIC(10,2),
            status VARCHAR(20) DEFAULT 'active',
            times_used INTEGER DEFAULT 0,
            total_discount_given NUMERIC(12,2) DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_happy_hours_location ON happy_hours(location_id)")


def downgrade() -> None:
    tables = [
        "happy_hours",
        "combo_items", "combo_meals", "menu_item_modifier_groups",
        "modifier_options", "modifier_groups", "menu_categories",
        "shift_schedules", "daily_reconciliations", "budgets", "tax_filings",
        "referral_records", "referral_programs", "risk_alerts",
        "staff_points", "staff_achievements", "challenges", "badges",
        "promotions", "warehouse_transfers", "warehouses",
        "vip_occasions", "vip_customer_links",
        "audit_log_entries", "feedback_reviews",
        "haccp_safety_checks", "haccp_temperature_logs",
        "alert_configs", "notification_preferences", "notifications",
        "payroll_entries", "payroll_runs", "app_settings",
    ]
    for t in tables:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

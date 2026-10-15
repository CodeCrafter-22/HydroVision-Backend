```sql
-- Enable Supabase Realtime for approved HydroVision tables.
-- Fail explicitly if a required table is missing.

DO $$
DECLARE
    table_name TEXT;
    realtime_tables TEXT[] := ARRAY[
        'risk_snapshots',
        'sos_events',
        'tasks',
        'alert_deliveries',
        'reports',
        'resource_suggestions',
        'shelters',
        'source_health',
        'sitreps'
    ];
BEGIN
    FOREACH table_name IN ARRAY realtime_tables
    LOOP
        IF to_regclass(format('public.%I', table_name)) IS NULL THEN
            RAISE EXCEPTION
                'Required Realtime table public.% is missing',
                table_name;
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM pg_publication_tables
            WHERE pubname = 'supabase_realtime'
              AND schemaname = 'public'
              AND tablename = table_name
        ) THEN
            EXECUTE format(
                'ALTER PUBLICATION supabase_realtime ADD TABLE public.%I',
                table_name
            );
        END IF;
    END LOOP;
END $$;
```
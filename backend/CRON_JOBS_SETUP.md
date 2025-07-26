# Supabase Cron Jobs Setup Guide

Follow these steps to set up automated tasks in your Supabase project:

## Prerequisites
1. Go to your Supabase Dashboard
2. Navigate to Database > Extensions
3. Make sure `pg_cron` extension is enabled

## Step 1: Create SQL Functions

### A. Function to Suspend Overdue Vendors

Go to Database > SQL Editor and run this query:

```sql
-- Create function to suspend vendors with overdue payments
CREATE OR REPLACE FUNCTION suspend_overdue_vendors()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- Update vendor profiles to set is_active = false for overdue payments
    UPDATE vendor_profiles 
    SET is_active = false, updated_at = NOW()
    WHERE user_profile_id IN (
        SELECT DISTINCT o.buyer_id
        FROM orders o
        WHERE o.payment_status = 'pending'
          AND o.order_type = 'buy_now_pay_later'
          AND o.due_date < NOW()
          AND o.buyer_id IN (
              SELECT vp.user_profile_id 
              FROM vendor_profiles vp 
              WHERE vp.is_active = true
          )
    );
    
    -- Log the number of vendors suspended
    RAISE NOTICE 'Suspended vendors with overdue payments at %', NOW();
END;
$$;
```

### B. Function to Finalize Bulk Orders

```sql
-- Create function to finalize bulk order windows
CREATE OR REPLACE FUNCTION finalize_bulk_orders()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    bulk_window RECORD;
    order_record RECORD;
    total_participants INTEGER;
    total_amount_sum DECIMAL;
BEGIN
    -- Find all bulk order windows that need to be finalized
    FOR bulk_window IN 
        SELECT * FROM bulk_order_windows 
        WHERE status = 'open' 
          AND window_end_time < NOW()
    LOOP
        -- Calculate totals for this window
        SELECT COUNT(DISTINCT buyer_id), COALESCE(SUM(total_amount), 0)
        INTO total_participants, total_amount_sum
        FROM orders 
        WHERE bulk_order_window_id = bulk_window.id;
        
        -- Update the bulk order window
        UPDATE bulk_order_windows 
        SET status = 'finalized',
            total_participants = total_participants,
            total_amount = total_amount_sum,
            updated_at = NOW()
        WHERE id = bulk_window.id;
        
        -- Process each order in this window
        FOR order_record IN 
            SELECT * FROM orders 
            WHERE bulk_order_window_id = bulk_window.id 
              AND payment_status = 'pending'
        LOOP
            -- Deduct balance from vendor
            UPDATE vendor_profiles 
            SET balance = balance - order_record.total_amount,
                updated_at = NOW()
            WHERE user_profile_id = order_record.buyer_id
              AND balance >= order_record.total_amount;
            
            -- Update order status to paid if balance was sufficient
            UPDATE orders 
            SET payment_status = CASE 
                WHEN (SELECT balance FROM vendor_profiles WHERE user_profile_id = order_record.buyer_id) >= 0 
                THEN 'paid' 
                ELSE 'failed' 
            END,
            updated_at = NOW()
            WHERE id = order_record.id;
        END LOOP;
        
        RAISE NOTICE 'Finalized bulk order window % with % participants', bulk_window.id, total_participants;
    END LOOP;
END;
$$;
```

## Step 2: Schedule the Cron Jobs

### A. Schedule Daily Vendor Suspension Check

Go to Database > SQL Editor and run:

```sql
-- Schedule to run every day at 2:00 AM UTC
SELECT cron.schedule(
    'suspend-overdue-vendors',           -- job name
    '0 2 * * *',                        -- cron expression (daily at 2 AM)
    'SELECT suspend_overdue_vendors();'  -- SQL to execute
);
```

### B. Schedule Bulk Order Finalization

```sql
-- Schedule to run every 10 minutes
SELECT cron.schedule(
    'finalize-bulk-orders',              -- job name
    '*/10 * * * *',                     -- cron expression (every 10 minutes)
    'SELECT finalize_bulk_orders();'     -- SQL to execute
);
```

## Step 3: Verify Jobs are Running

### Check Active Jobs

```sql
-- View all scheduled jobs
SELECT * FROM cron.job;
```

### Check Job Run History

```sql
-- View recent job runs
SELECT * FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 10;
```

## Step 4: Manual Testing

You can test the functions manually:

```sql
-- Test vendor suspension function
SELECT suspend_overdue_vendors();

-- Test bulk order finalization function
SELECT finalize_bulk_orders();
```

## Troubleshooting

### If Jobs Don't Appear
1. Make sure `pg_cron` extension is enabled
2. Check if your Supabase plan supports cron jobs
3. Verify the SQL syntax is correct

### Modify a Job
```sql
-- Unschedule a job
SELECT cron.unschedule('job-name');

-- Schedule again with new settings
SELECT cron.schedule('new-job-name', 'new-cron-expression', 'new-sql');
```

### Delete a Job
```sql
SELECT cron.unschedule('job-name');
```

## Cron Expression Examples

- `'0 2 * * *'` - Daily at 2:00 AM
- `'*/10 * * * *'` - Every 10 minutes
- `'0 */6 * * *'` - Every 6 hours
- `'0 0 * * 0'` - Weekly on Sunday at midnight
- `'0 0 1 * *'` - Monthly on the 1st at midnight

## Notes

1. All times are in UTC
2. The functions will create logs using `RAISE NOTICE`
3. Make sure your database has the necessary permissions
4. Test thoroughly before deploying to production
5. Monitor the job run history regularly

## Next Steps

After setting up the cron jobs:
1. Create test orders with overdue dates
2. Create test bulk order windows
3. Monitor the logs to ensure jobs are running
4. Set up alerting if needed (external monitoring)

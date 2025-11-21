# Data Preparation Guide

## What Level of Data Should You Provide?

The answer depends on your **metric type** and **analysis needs**. This guide explains the different data granularities and when to use each.

---

## Data Granularity Options

### Option 1: User-Level Aggregated (RECOMMENDED for most cases)

**What it is:** One row per user with their aggregated metric value.

**When to use:**
- ✅ User-level metrics (e.g., total revenue per user, average session duration per user)
- ✅ Binary metrics (e.g., conversion rate - 0 or 1 per user)
- ✅ Most A/B tests analyzing user behavior

**Example:**
```
user_id    | metric  | timestamp           | platform
-----------|---------|---------------------|----------
user_001   | 150.50  | 2024-01-15 10:30:00 | web
user_002   | 0.00    | 2024-01-15 10:31:00 | web
user_003   | 220.75  | 2024-01-15 10:32:00 | web
```

**Metrics:**
- Total revenue per user
- Number of purchases per user
- Average session duration per user
- Conversion (0 = didn't convert, 1 = converted)
- Days active in test period

**Advantages:**
- ✅ Simple to understand
- ✅ Clean statistical properties (independent observations)
- ✅ Fast computation
- ✅ Correct duplicate user detection

**How to prepare:**
```sql
-- SQL example
SELECT
    user_id,
    SUM(revenue) as metric,
    MIN(event_timestamp) as timestamp,
    platform
FROM events
WHERE test_id = 'my_test'
GROUP BY user_id, platform
```

```python
# Python/Pandas example
user_level = events.groupby(['user_id', 'platform']).agg({
    'revenue': 'sum',
    'timestamp': 'min'
}).reset_index()
user_level.rename(columns={'revenue': 'metric'}, inplace=True)
```

---

### Option 2: Event-Level (For specific analyses)

**What it is:** One row per event, multiple rows per user.

**When to use:**
- ⚠️ Analyzing event-level metrics (e.g., click-through rate on specific elements)
- ⚠️ Need to detect bot patterns via high-frequency events
- ⚠️ Want to check temporal consistency at event level

**Example:**
```
user_id    | metric | timestamp           | event_type | platform
-----------|--------|---------------------|------------|----------
user_001   | 25.00  | 2024-01-15 10:30:00 | purchase   | web
user_001   | 10.50  | 2024-01-15 11:45:00 | purchase   | web
user_001   | 15.00  | 2024-01-15 14:20:00 | purchase   | web
user_002   | 50.00  | 2024-01-15 10:31:00 | purchase   | web
```

**Metrics:**
- Individual purchase amounts
- Click events (0 or 1 per event)
- Page load times per page view

**⚠️ Important Considerations:**
- **Statistical issue**: Events from same user are NOT independent
- **Sample size**: Number of events ≠ number of users
- **Duplicate detection**: Will flag users with multiple events as "duplicates" (false alarm)
- **Variance**: Will be artificially inflated or deflated

**When event-level is WRONG:**
```python
# ❌ WRONG: Using 1000 events from 100 users
# The framework will think you have 1000 independent samples
# But you really only have 100 independent users
# This violates independence assumption!
```

**How to use event-level data:**
1. **Aggregate to user-level first** (RECOMMENDED)
2. Or use specialized event-level analysis (not currently supported)

---

### Option 3: Session-Level Aggregated

**What it is:** One row per session, multiple rows per user.

**When to use:**
- Sessions are the unit of analysis
- Metric is session-based (e.g., items per session, session duration)

**Example:**
```
user_id    | session_id | metric | timestamp           | platform
-----------|------------|--------|---------------------|----------
user_001   | sess_001   | 3.5    | 2024-01-15 10:30:00 | web
user_001   | sess_002   | 2.0    | 2024-01-16 09:15:00 | web
user_002   | sess_003   | 5.2    | 2024-01-15 10:31:00 | web
```

**⚠️ Same issues as event-level:**
- Not independent observations
- Need to account for clustering by user
- May need multi-level modeling

---

### Option 4: Daily User-Level

**What it is:** One row per user per day.

**When to use:**
- Long-running tests
- Daily engagement metrics

**Example:**
```
user_id    | date       | metric | platform
-----------|------------|--------|----------
user_001   | 2024-01-15 | 2.5    | web
user_001   | 2024-01-16 | 3.0    | web
user_002   | 2024-01-15 | 1.0    | web
```

**⚠️ Same clustering issues** - need to aggregate to user-level or use proper methods.

---

## Recommendations by Metric Type

| Metric | Data Level | Aggregation |
|--------|-----------|-------------|
| **Revenue per user** | User-level | `SUM(revenue)` per user |
| **Conversion rate** | User-level | `1` if converted, `0` if not, one row per user |
| **Average order value** | User-level | `SUM(revenue) / COUNT(orders)` per user |
| **Items per user** | User-level | `COUNT(items)` per user |
| **Session duration** | User-level | `AVG(session_duration)` per user |
| **Page views per user** | User-level | `COUNT(page_views)` per user |
| **Click-through rate** | User-level | `1` if clicked, `0` if not, one row per user |
| **Time to conversion** | User-level | Time from first exposure to conversion, one row per user |
| **Retention (D7)** | User-level | `1` if active on day 7, `0` if not |

---

## Framework Expectations (Current Implementation)

### What the current code expects:

```python
diagnostics.load_platform_data(
    platform_name='web',
    control_data=control_df,      # DataFrame with one row per observation
    treatment_data=treatment_df,   # DataFrame with one row per observation
    metric_column='metric',        # Column with metric values
    user_id_column='user_id',      # Column with user IDs
    timestamp_column='timestamp'   # Optional: for temporal checks
)
```

### Current behavior:

1. **Sample size**: Counts number of rows → assumes one row per user
2. **Duplicate detection**: Looks for duplicate user_ids → expects one row per user
3. **Statistical tests**: Treats each row as independent → requires user-level data
4. **Bot detection**: Counts rows per user_id → works with both but interprets differently

### ⚠️ Current Limitation:

The framework **assumes user-level aggregated data** for correct statistical analysis but doesn't enforce it or provide helpers to aggregate.

---

## Data Preparation Examples

### Example 1: E-commerce Revenue Test

**Goal:** Test if new checkout flow increases revenue per user

**Raw event data:**
```python
# events table
user_id | variant   | event_type | revenue | timestamp
--------|-----------|------------|---------|-------------------
u001    | control   | purchase   | 25.00   | 2024-01-15 10:30
u001    | control   | purchase   | 15.00   | 2024-01-15 14:20
u002    | treatment | purchase   | 50.00   | 2024-01-15 11:00
u003    | control   | view       | 0.00    | 2024-01-15 12:00
```

**✅ Correct preparation (user-level):**
```python
import pandas as pd

# Aggregate to user level
user_metrics = events.groupby(['user_id', 'variant']).agg({
    'revenue': 'sum',           # Total revenue per user
    'timestamp': 'min',         # First event timestamp
}).reset_index()

# Split into control and treatment
control = user_metrics[user_metrics['variant'] == 'control']
treatment = user_metrics[user_metrics['variant'] == 'treatment']

# Load into framework
diagnostics.load_platform_data(
    'web',
    control[['user_id', 'revenue', 'timestamp']],
    treatment[['user_id', 'revenue', 'timestamp']],
    metric_column='revenue',
    user_id_column='user_id',
    timestamp_column='timestamp'
)
```

**Result:**
- ✅ 3 independent observations (3 users)
- ✅ Correct statistical properties
- ✅ Correct duplicate detection

---

### Example 2: Conversion Rate Test

**Goal:** Test if new landing page increases conversion rate

**Raw event data:**
```python
# users table
user_id | variant   | converted | first_seen
--------|-----------|-----------|-------------------
u001    | control   | 0         | 2024-01-15 10:30
u002    | treatment | 1         | 2024-01-15 11:00
u003    | control   | 1         | 2024-01-15 12:00
u004    | treatment | 0         | 2024-01-15 13:00
```

**✅ Already user-level (perfect!):**
```python
control = users[users['variant'] == 'control']
treatment = users[users['variant'] == 'treatment']

diagnostics.load_platform_data(
    'web',
    control[['user_id', 'converted', 'first_seen']],
    treatment[['user_id', 'converted', 'first_seen']],
    metric_column='converted',  # Binary: 0 or 1
    user_id_column='user_id',
    timestamp_column='first_seen'
)
```

---

### Example 3: Engagement Metric (Multi-day test)

**Goal:** Test if new feature increases daily active days

**Raw event data:**
```python
# daily_activity table
user_id | variant   | date       | was_active
--------|-----------|------------|------------
u001    | control   | 2024-01-15 | 1
u001    | control   | 2024-01-16 | 1
u001    | control   | 2024-01-17 | 0
u002    | treatment | 2024-01-15 | 1
u002    | treatment | 2024-01-16 | 1
u002    | treatment | 2024-01-17 | 1
```

**✅ Aggregate to user level:**
```python
# Count active days per user during test period
user_metrics = daily_activity.groupby(['user_id', 'variant']).agg({
    'was_active': 'sum',  # Total active days
    'date': 'min'         # First date in test
}).reset_index()
user_metrics.rename(columns={'was_active': 'active_days'}, inplace=True)

control = user_metrics[user_metrics['variant'] == 'control']
treatment = user_metrics[user_metrics['variant'] == 'treatment']

diagnostics.load_platform_data(
    'mobile_app',
    control[['user_id', 'active_days', 'date']],
    treatment[['user_id', 'active_days', 'date']],
    metric_column='active_days',
    user_id_column='user_id',
    timestamp_column='date'
)
```

---

## Common Mistakes

### ❌ Mistake 1: Passing Event-Level Data Directly

```python
# ❌ WRONG
# events has 10,000 rows from 1,000 users
diagnostics.load_platform_data('web', control_events, treatment_events)
# Framework thinks you have 10,000 independent users!
# Statistical tests will be WRONG
```

**✅ Fix:**
```python
# Aggregate to user level first
control_users = control_events.groupby('user_id').agg({'metric': 'sum'}).reset_index()
treatment_users = treatment_events.groupby('user_id').agg({'metric': 'sum'}).reset_index()
diagnostics.load_platform_data('web', control_users, treatment_users)
```

---

### ❌ Mistake 2: Mixing Granularities Across Platforms

```python
# ❌ WRONG
# Web: user-level (1 row per user)
diagnostics.load_platform_data('web', web_control_users, web_treatment_users)

# Mobile: event-level (multiple rows per user)
diagnostics.load_platform_data('mobile', mobile_control_events, mobile_treatment_events)

# Now comparing apples (users) to oranges (events)!
```

**✅ Fix:**
```python
# Ensure same granularity for all platforms
mobile_control_users = mobile_control_events.groupby('user_id').agg({'metric': 'sum'}).reset_index()
mobile_treatment_users = mobile_treatment_events.groupby('user_id').agg({'metric': 'sum'}).reset_index()

diagnostics.load_platform_data('web', web_control_users, web_treatment_users)
diagnostics.load_platform_data('mobile', mobile_control_users, mobile_treatment_users)
```

---

### ❌ Mistake 3: Not Handling Users With Zero Events

```python
# ❌ WRONG
# Only users with events appear in data
# Missing users who were assigned but never engaged
active_users = events.groupby('user_id').agg({'revenue': 'sum'})
```

**✅ Fix:**
```python
# Include ALL assigned users, even those with zero events
assigned_users = get_all_assigned_users(test_id)  # From assignment log
events_agg = events.groupby('user_id').agg({'revenue': 'sum'})

# Left join to keep users with zero events
user_metrics = assigned_users.merge(events_agg, on='user_id', how='left')
user_metrics['revenue'].fillna(0, inplace=True)  # Zero for users with no events
```

---

## Quick Reference

### User-Level Data Checklist

Before loading data into the framework, verify:

- [ ] ✅ One row per user (no duplicate user_ids in control or treatment)
- [ ] ✅ Metric is aggregated appropriately (sum, mean, max, etc.)
- [ ] ✅ Includes ALL assigned users (even those with zero activity)
- [ ] ✅ Same granularity across all platforms
- [ ] ✅ User_id uniquely identifies a user
- [ ] ✅ Timestamp represents user's first event or assignment time

### Validation Code

```python
def validate_user_level_data(df, user_col='user_id'):
    """Validate that DataFrame is properly prepared user-level data."""

    # Check for duplicates
    duplicates = df[user_col].duplicated().sum()
    if duplicates > 0:
        print(f"❌ FAIL: {duplicates} duplicate user_ids found!")
        print("   Data should have one row per user.")
        return False

    # Check for nulls in user_id
    nulls = df[user_col].isnull().sum()
    if nulls > 0:
        print(f"❌ FAIL: {nulls} null user_ids found!")
        return False

    print(f"✅ PASS: {len(df)} unique users")
    return True

# Usage
validate_user_level_data(control_data)
validate_user_level_data(treatment_data)
```

---

## Summary

**For 95% of A/B tests:**

1. ✅ **Use user-level aggregated data** (one row per user)
2. ✅ **Aggregate your events to user level** before loading into framework
3. ✅ **Include all assigned users**, even those with zero activity
4. ✅ **Use consistent granularity** across all platforms

**The framework expects:**
- User-level data for correct statistical analysis
- Independent observations (no clustering)
- One row per user in each group

**If you need event-level or session-level analysis:**
- Consider using specialized time-series or multi-level modeling techniques
- Or aggregate to user-level and analyze user-level metrics

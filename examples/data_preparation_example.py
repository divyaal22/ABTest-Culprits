"""
Example: Preparing data at the correct granularity.

This example demonstrates:
1. How to convert event-level data to user-level
2. How to validate data preparation
3. Common patterns for different metric types
"""

import pandas as pd
import numpy as np
from abtest_culprits import (
    ABTestDiagnostics,
    CrossPlatformAnalyzer,
    prepare_from_events,
    validate_user_level,
    aggregate_to_user_level
)


def generate_event_level_data():
    """
    Generate sample event-level data (multiple events per user).
    This simulates real-world raw event logs.
    """
    np.random.seed(42)

    events = []

    # Web platform
    for user_idx in range(500):  # 500 users
        variant = 'control' if user_idx < 250 else 'treatment'
        n_events = np.random.poisson(5)  # Average 5 events per user

        for event_idx in range(max(1, n_events)):
            events.append({
                'user_id': f'web_user_{user_idx}',
                'platform': 'web',
                'variant': variant,
                'revenue': np.random.exponential(20) if np.random.random() < 0.1 else 0,
                'timestamp': pd.Timestamp('2024-01-15') + pd.Timedelta(hours=user_idx, minutes=event_idx)
            })

    # Mobile platform
    for user_idx in range(400):  # 400 users
        variant = 'control' if user_idx < 200 else 'treatment'
        n_events = np.random.poisson(3)  # Average 3 events per user

        for event_idx in range(max(1, n_events)):
            events.append({
                'user_id': f'mobile_user_{user_idx}',
                'platform': 'mobile',
                'variant': variant,
                'revenue': np.random.exponential(25) if np.random.random() < 0.12 else 0,
                'timestamp': pd.Timestamp('2024-01-15') + pd.Timedelta(hours=user_idx, minutes=event_idx)
            })

    return pd.DataFrame(events)


def example_1_wrong_way():
    """
    ❌ WRONG: Loading event-level data directly into framework.
    This violates independence assumption!
    """
    print("=" * 80)
    print("Example 1: WRONG WAY (Event-Level Data)")
    print("=" * 80)
    print()

    # Generate event-level data
    events_df = generate_event_level_data()
    print(f"Generated {len(events_df):,} events")
    print(f"Sample:\n{events_df.head(10)}\n")

    # ❌ WRONG: Split events directly by variant
    web_events = events_df[events_df['platform'] == 'web']
    control_events = web_events[web_events['variant'] == 'control']
    treatment_events = web_events[web_events['variant'] == 'treatment']

    print(f"Control events: {len(control_events):,}")
    print(f"Treatment events: {len(treatment_events):,}")
    print()

    # This will FAIL validation
    print("Validating control data...")
    validate_user_level(control_events, user_id_column='user_id')
    print()

    print("❌ PROBLEM: Multiple rows per user violates independence assumption!")
    print("❌ Statistical tests will be WRONG because events are correlated within users.")
    print()


def example_2_correct_way():
    """
    ✅ CORRECT: Aggregate to user-level first.
    """
    print("=" * 80)
    print("Example 2: CORRECT WAY (User-Level Aggregation)")
    print("=" * 80)
    print()

    # Generate event-level data
    events_df = generate_event_level_data()
    print(f"Generated {len(events_df):,} events")
    print()

    # ✅ CORRECT: Use the prepare_from_events helper
    print("Converting event-level to user-level data...")
    platform_data = prepare_from_events(
        events_df,
        user_id_column='user_id',
        variant_column='variant',
        metric_column='revenue',
        platform_column='platform',
        timestamp_column='timestamp',
        aggregation='sum'  # Sum revenue per user
    )

    print()
    print("=" * 80)
    print("Ready for Analysis")
    print("=" * 80)
    print()

    # Now we can use this with the diagnostic framework
    diagnostics = ABTestDiagnostics()

    for platform, (control, treatment) in platform_data.items():
        print(f"\n--- Loading {platform} into diagnostics framework ---")

        diagnostics.load_platform_data(
            platform,
            control,
            treatment,
            metric_column='revenue',
            user_id_column='user_id',
            timestamp_column='timestamp'
        )

        # Run diagnostics
        results = diagnostics.run_all_diagnostics(platform)

    # Print summary
    print()
    print(diagnostics.get_summary())


def example_3_manual_aggregation():
    """
    Alternative: Manual aggregation using pandas.
    """
    print("=" * 80)
    print("Example 3: Manual Aggregation (Alternative Method)")
    print("=" * 80)
    print()

    events_df = generate_event_level_data()

    # Filter to one platform
    web_events = events_df[events_df['platform'] == 'web']
    print(f"Web events: {len(web_events):,}")
    print()

    # Aggregate to user level manually
    print("Aggregating to user level...")
    user_level = web_events.groupby(['user_id', 'variant']).agg({
        'revenue': 'sum',           # Total revenue per user
        'timestamp': 'min'          # First event timestamp
    }).reset_index()

    print(f"✅ Result: {len(user_level):,} users")
    print(f"   Average events per user: {len(web_events) / len(user_level):.2f}")
    print()

    # Validate
    print("Validating user-level data...")
    validate_user_level(user_level, user_id_column='user_id')
    print()

    # Split by variant
    control = user_level[user_level['variant'] == 'control']
    treatment = user_level[user_level['variant'] == 'treatment']

    print(f"Control: {len(control):,} users")
    print(f"Treatment: {len(treatment):,} users")
    print()

    # Load into diagnostics
    diagnostics = ABTestDiagnostics()
    diagnostics.load_platform_data(
        'web',
        control,
        treatment,
        metric_column='revenue',
        user_id_column='user_id',
        timestamp_column='timestamp'
    )

    results = diagnostics.run_all_diagnostics('web')
    print(diagnostics.get_summary())


def example_4_conversion_metric():
    """
    Example with binary conversion metric.
    """
    print("=" * 80)
    print("Example 4: Binary Conversion Metric")
    print("=" * 80)
    print()

    np.random.seed(42)

    # Generate user-level conversion data (already aggregated)
    users = []
    for i in range(1000):
        variant = 'control' if i < 500 else 'treatment'
        # Treatment has higher conversion rate
        conversion_rate = 0.10 if variant == 'control' else 0.12
        converted = 1 if np.random.random() < conversion_rate else 0

        users.append({
            'user_id': f'user_{i}',
            'variant': variant,
            'converted': converted,
            'platform': 'web',
            'timestamp': pd.Timestamp('2024-01-15') + pd.Timedelta(hours=i)
        })

    users_df = pd.DataFrame(users)

    print(f"Generated {len(users_df):,} users")
    print(f"Sample:\n{users_df.head()}\n")

    # This is already user-level, so we can use directly
    print("Data is already user-level (one row per user).")
    print("Validating...")
    validate_user_level(users_df, user_id_column='user_id')
    print()

    # Split by variant
    control = users_df[users_df['variant'] == 'control']
    treatment = users_df[users_df['variant'] == 'treatment']

    print(f"Control: {len(control):,} users, Conversion rate: {control['converted'].mean():.2%}")
    print(f"Treatment: {len(treatment):,} users, Conversion rate: {treatment['converted'].mean():.2%}")
    print()

    # Load into diagnostics
    diagnostics = ABTestDiagnostics()
    diagnostics.load_platform_data(
        'web',
        control,
        treatment,
        metric_column='converted',
        user_id_column='user_id',
        timestamp_column='timestamp'
    )

    results = diagnostics.run_all_diagnostics('web')
    print(diagnostics.get_summary())


def example_5_include_zero_users():
    """
    Example including users with zero activity.
    """
    print("=" * 80)
    print("Example 5: Including Users with Zero Activity")
    print("=" * 80)
    print()

    np.random.seed(42)

    # All assigned users (1000 users)
    all_users = pd.DataFrame({
        'user_id': [f'user_{i}' for i in range(1000)],
        'variant': ['control' if i < 500 else 'treatment' for i in range(1000)],
        'platform': 'web'
    })

    print(f"Total assigned users: {len(all_users):,}")
    print()

    # Only 60% of users actually had events
    active_user_ids = np.random.choice(all_users['user_id'], size=600, replace=False)

    # Generate events only for active users
    events = []
    for user_id in active_user_ids:
        variant = all_users[all_users['user_id'] == user_id]['variant'].iloc[0]
        n_events = np.random.poisson(5)

        for _ in range(max(1, n_events)):
            events.append({
                'user_id': user_id,
                'variant': variant,
                'revenue': np.random.exponential(20),
                'platform': 'web',
                'timestamp': pd.Timestamp('2024-01-15')
            })

    events_df = pd.DataFrame(events)
    print(f"Events generated: {len(events_df):,}")
    print(f"Active users: {events_df['user_id'].nunique()}")
    print()

    # Aggregate to user level
    print("Aggregating events to user level...")
    active_users = events_df.groupby(['user_id', 'variant', 'platform']).agg({
        'revenue': 'sum',
        'timestamp': 'min'
    }).reset_index()

    print(f"Active users: {len(active_users):,}")
    print()

    # ✅ IMPORTANT: Include users with zero activity
    print("Including users with zero activity...")
    from abtest_culprits import DataPreparation

    complete_users = DataPreparation.include_zero_activity_users(
        active_users,
        all_users,
        user_id_column='user_id',
        metric_column='revenue',
        fill_value=0.0
    )

    print()
    print(f"Zero-activity users: {(complete_users['revenue'] == 0).sum()}")
    print(f"Revenue > 0: {(complete_users['revenue'] > 0).sum()}")
    print()

    # Now we have the complete picture
    control = complete_users[complete_users['variant'] == 'control']
    treatment = complete_users[complete_users['variant'] == 'treatment']

    print(f"Control: {len(control):,} users (mean revenue: ${control['revenue'].mean():.2f})")
    print(f"Treatment: {len(treatment):,} users (mean revenue: ${treatment['revenue'].mean():.2f})")
    print()

    print("✅ This is the CORRECT way to analyze A/B tests!")
    print("✅ Including zero-activity users prevents survivorship bias.")


def main():
    """Run all examples."""
    print("\n")
    print("*" * 80)
    print("DATA PREPARATION EXAMPLES")
    print("*" * 80)
    print("\n")

    # Example 1: Wrong way (event-level)
    example_1_wrong_way()
    print("\n" + "=" * 80 + "\n")

    # Example 2: Correct way (user-level with helper)
    example_2_correct_way()
    print("\n" + "=" * 80 + "\n")

    # Example 3: Manual aggregation
    example_3_manual_aggregation()
    print("\n" + "=" * 80 + "\n")

    # Example 4: Conversion metric
    example_4_conversion_metric()
    print("\n" + "=" * 80 + "\n")

    # Example 5: Including zero-activity users
    example_5_include_zero_users()

    print("\n")
    print("*" * 80)
    print("KEY TAKEAWAYS")
    print("*" * 80)
    print()
    print("1. ✅ Always aggregate to USER-LEVEL before analysis")
    print("2. ✅ Use prepare_from_events() for automatic conversion")
    print("3. ✅ Validate with validate_user_level() to catch errors")
    print("4. ✅ Include users with zero activity to avoid bias")
    print("5. ❌ Never use event-level data directly in statistical tests")
    print()


if __name__ == '__main__':
    main()

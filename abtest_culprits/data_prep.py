"""
Data preparation helpers for A/B test analysis.

This module helps convert event-level or session-level data into
user-level aggregated data suitable for the diagnostic framework.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
import warnings


class DataPreparation:
    """
    Helper class to prepare A/B test data at the correct granularity.
    """

    @staticmethod
    def validate_user_level(
        df: pd.DataFrame,
        user_id_column: str = 'user_id',
        raise_error: bool = False
    ) -> bool:
        """
        Validate that DataFrame contains user-level data (one row per user).

        Args:
            df: DataFrame to validate
            user_id_column: Name of user ID column
            raise_error: If True, raises ValueError on validation failure

        Returns:
            True if valid user-level data, False otherwise
        """
        issues = []

        # Check for duplicates
        duplicates = df[user_id_column].duplicated().sum()
        if duplicates > 0:
            issues.append(f"❌ {duplicates} duplicate user_ids found! Data should have one row per user.")

        # Check for nulls
        nulls = df[user_id_column].isnull().sum()
        if nulls > 0:
            issues.append(f"❌ {nulls} null user_ids found!")

        if issues:
            message = "\n".join(issues)
            if raise_error:
                raise ValueError(f"Data validation failed:\n{message}")
            else:
                print(message)
            return False

        print(f"✅ PASS: {len(df)} unique users in dataset")
        return True

    @staticmethod
    def aggregate_to_user_level(
        events_df: pd.DataFrame,
        user_id_column: str = 'user_id',
        metric_column: str = 'metric',
        aggregation: str = 'sum',
        timestamp_column: Optional[str] = None,
        group_by_columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Aggregate event-level data to user-level.

        Args:
            events_df: Event-level DataFrame
            user_id_column: Column containing user IDs
            metric_column: Column containing metric values
            aggregation: How to aggregate ('sum', 'mean', 'count', 'max', 'min')
            timestamp_column: Optional timestamp column (will take min/first)
            group_by_columns: Additional columns to group by (e.g., ['platform', 'variant'])

        Returns:
            User-level aggregated DataFrame
        """
        group_cols = [user_id_column]
        if group_by_columns:
            group_cols.extend(group_by_columns)

        agg_dict = {metric_column: aggregation}

        if timestamp_column and timestamp_column in events_df.columns:
            agg_dict[timestamp_column] = 'min'  # First timestamp

        user_level = events_df.groupby(group_cols).agg(agg_dict).reset_index()

        print(f"✅ Aggregated {len(events_df):,} events to {len(user_level):,} users")
        print(f"   Average events per user: {len(events_df) / len(user_level):.2f}")

        return user_level

    @staticmethod
    def prepare_conversion_metric(
        users_df: pd.DataFrame,
        user_id_column: str = 'user_id',
        conversion_column: str = 'converted',
        timestamp_column: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Prepare binary conversion data (already user-level).

        Args:
            users_df: DataFrame with user-level conversion data
            user_id_column: Column with user IDs
            conversion_column: Column with conversion indicator (0 or 1)
            timestamp_column: Optional timestamp column

        Returns:
            Validated and formatted DataFrame
        """
        result = users_df[[user_id_column, conversion_column]].copy()

        if timestamp_column and timestamp_column in users_df.columns:
            result[timestamp_column] = users_df[timestamp_column]

        # Validate binary
        unique_values = result[conversion_column].unique()
        if not set(unique_values).issubset({0, 1, np.nan}):
            warnings.warn(
                f"Conversion column contains values other than 0/1: {unique_values}. "
                "For conversion metrics, use 1 for converted, 0 for not converted."
            )

        DataPreparation.validate_user_level(result, user_id_column)
        return result

    @staticmethod
    def split_by_variant(
        df: pd.DataFrame,
        variant_column: str = 'variant',
        control_value: str = 'control',
        treatment_value: str = 'treatment'
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split DataFrame into control and treatment groups.

        Args:
            df: DataFrame with both variants
            variant_column: Column indicating variant assignment
            control_value: Value indicating control group
            treatment_value: Value indicating treatment group

        Returns:
            Tuple of (control_df, treatment_df)
        """
        control_df = df[df[variant_column] == control_value].copy()
        treatment_df = df[df[variant_column] == treatment_value].copy()

        print(f"✅ Split into Control: {len(control_df):,} users, Treatment: {len(treatment_df):,} users")

        if len(control_df) == 0 or len(treatment_df) == 0:
            warnings.warn("One of the groups is empty! Check variant_column values.")

        return control_df, treatment_df

    @staticmethod
    def include_zero_activity_users(
        events_df: pd.DataFrame,
        all_assigned_users: pd.DataFrame,
        user_id_column: str = 'user_id',
        metric_column: str = 'metric',
        fill_value: float = 0.0
    ) -> pd.DataFrame:
        """
        Include users who were assigned but had no events (zero activity).

        Args:
            events_df: Aggregated user-level data from events
            all_assigned_users: DataFrame with all assigned user IDs
            user_id_column: Column with user IDs
            metric_column: Column with metric values
            fill_value: Value to fill for users with no events

        Returns:
            DataFrame with all assigned users, filling zeros for inactive users
        """
        # Merge to get all assigned users
        result = all_assigned_users.merge(
            events_df,
            on=user_id_column,
            how='left'
        )

        # Fill NaN with zero
        result[metric_column].fillna(fill_value, inplace=True)

        added = len(result) - len(events_df)
        print(f"✅ Added {added:,} users with zero activity")
        print(f"   Total users: {len(result):,}")

        return result

    @staticmethod
    def prepare_from_events(
        events_df: pd.DataFrame,
        user_id_column: str = 'user_id',
        variant_column: str = 'variant',
        metric_column: str = 'metric',
        platform_column: Optional[str] = None,
        timestamp_column: Optional[str] = None,
        aggregation: str = 'sum',
        all_assigned_users: Optional[pd.DataFrame] = None,
        control_value: str = 'control',
        treatment_value: str = 'treatment'
    ) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Complete pipeline: Convert event-level data to user-level and split by variant.

        This is the main convenience method for most users.

        Args:
            events_df: Raw event-level DataFrame
            user_id_column: Column with user IDs
            variant_column: Column with variant assignment
            metric_column: Column with metric values
            platform_column: Optional column with platform (for multi-platform analysis)
            timestamp_column: Optional timestamp column
            aggregation: Aggregation method ('sum', 'mean', 'count', etc.)
            all_assigned_users: Optional DataFrame with all assigned users (to include zeros)
            control_value: Value indicating control variant
            treatment_value: Value indicating treatment variant

        Returns:
            Dictionary mapping platform names to (control_df, treatment_df) tuples.
            If no platform_column, returns {'all': (control_df, treatment_df)}
        """
        results = {}

        # Handle single platform vs multi-platform
        if platform_column and platform_column in events_df.columns:
            platforms = events_df[platform_column].unique()
            print(f"Processing {len(platforms)} platforms: {list(platforms)}")
        else:
            platforms = ['all']
            platform_column = None

        for platform in platforms:
            print(f"\n--- Platform: {platform} ---")

            # Filter to platform
            if platform_column:
                platform_events = events_df[events_df[platform_column] == platform]
            else:
                platform_events = events_df

            # Aggregate to user level
            group_cols = [variant_column]
            if platform_column:
                group_cols.append(platform_column)

            user_level = DataPreparation.aggregate_to_user_level(
                platform_events,
                user_id_column=user_id_column,
                metric_column=metric_column,
                aggregation=aggregation,
                timestamp_column=timestamp_column,
                group_by_columns=group_cols
            )

            # Include zero-activity users if provided
            if all_assigned_users is not None:
                if platform_column:
                    assigned = all_assigned_users[all_assigned_users[platform_column] == platform]
                else:
                    assigned = all_assigned_users

                user_level = DataPreparation.include_zero_activity_users(
                    user_level,
                    assigned,
                    user_id_column=user_id_column,
                    metric_column=metric_column
                )

            # Split by variant
            control, treatment = DataPreparation.split_by_variant(
                user_level,
                variant_column=variant_column,
                control_value=control_value,
                treatment_value=treatment_value
            )

            # Validate
            DataPreparation.validate_user_level(control, user_id_column)
            DataPreparation.validate_user_level(treatment, user_id_column)

            results[platform] = (control, treatment)

        return results

    @staticmethod
    def quick_summary(
        df: pd.DataFrame,
        metric_column: str = 'metric',
        variant_column: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Generate quick summary statistics for a dataset.

        Args:
            df: DataFrame to summarize
            metric_column: Column with metric values
            variant_column: Optional variant column to group by

        Returns:
            DataFrame with summary statistics
        """
        if variant_column and variant_column in df.columns:
            summary = df.groupby(variant_column)[metric_column].agg([
                ('count', 'count'),
                ('mean', 'mean'),
                ('std', 'std'),
                ('min', 'min'),
                ('25%', lambda x: x.quantile(0.25)),
                ('50%', lambda x: x.quantile(0.50)),
                ('75%', lambda x: x.quantile(0.75)),
                ('max', 'max')
            ]).reset_index()
        else:
            summary = df[metric_column].agg([
                ('count', 'count'),
                ('mean', 'mean'),
                ('std', 'std'),
                ('min', 'min'),
                ('25%', lambda x: x.quantile(0.25)),
                ('50%', lambda x: x.quantile(0.50)),
                ('75%', lambda x: x.quantile(0.75)),
                ('max', 'max')
            ]).to_frame().T

        return summary


# Convenience functions
def validate_user_level(df: pd.DataFrame, user_id_column: str = 'user_id') -> bool:
    """Validate user-level data. See DataPreparation.validate_user_level()."""
    return DataPreparation.validate_user_level(df, user_id_column)


def aggregate_to_user_level(
    events_df: pd.DataFrame,
    user_id_column: str = 'user_id',
    metric_column: str = 'metric',
    aggregation: str = 'sum',
    **kwargs
) -> pd.DataFrame:
    """Aggregate events to user level. See DataPreparation.aggregate_to_user_level()."""
    return DataPreparation.aggregate_to_user_level(
        events_df, user_id_column, metric_column, aggregation, **kwargs
    )


def prepare_from_events(events_df: pd.DataFrame, **kwargs) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Prepare data from events (main convenience function).
    See DataPreparation.prepare_from_events().
    """
    return DataPreparation.prepare_from_events(events_df, **kwargs)

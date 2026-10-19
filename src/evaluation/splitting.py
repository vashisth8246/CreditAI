"""Chronological and grouped splitting for evaluation.

This module provides utilities for creating train/validation/test splits
with proper temporal controls and borrower-level grouping.

This phase does NOT train models—it only creates split definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
import numpy as np
import re


DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class SplitResult:
    """Result of a split operation."""
    train_indices: np.ndarray
    validation_indices: np.ndarray
    test_indices: np.ndarray
    metadata: dict[str, Any]


def _parse_date(val: Any) -> date | None:
    """Attempt to parse a date string, returning None if invalid."""
    if isinstance(val, str) and DATE_REGEX.match(val):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def chronological_split(
    dates: list[Any],
    train_end_date: str,
    validation_end_date: str,
    test_end_date: str,
) -> SplitResult:
    """Create chronological train/validation/test splits based on dates.

    Args:
        dates: List of date values (strings or date objects).
        train_end_date: End date for training set (inclusive).
        validation_end_date: End date for validation set (inclusive).
        test_end_date: End date for test set (inclusive).

    Returns:
        SplitResult with indices for each split.

    Raises:
        ValueError: If dates are invalid or chronological order is violated.
    """
    # Parse date boundaries
    train_end = _parse_date(train_end_date)
    validation_end = _parse_date(validation_end_date)
    test_end = _parse_date(test_end_date)

    if train_end is None or validation_end is None or test_end is None:
        raise ValueError("Invalid date boundaries.")

    if not (train_end < validation_end < test_end):
        raise ValueError("Date boundaries must be in chronological order: train_end < validation_end < test_end.")

    # Parse all dates
    parsed_dates = []
    for i, d in enumerate(dates):
        parsed = _parse_date(d)
        if parsed is None:
            raise ValueError(f"Invalid date at index {i}: {d}")
        parsed_dates.append(parsed)

    parsed_dates = np.array(parsed_dates)

    # Create splits
    train_mask = parsed_dates <= train_end
    validation_mask = (parsed_dates > train_end) & (parsed_dates <= validation_end)
    test_mask = (parsed_dates > validation_end) & (parsed_dates <= test_end)

    train_indices = np.where(train_mask)[0]
    validation_indices = np.where(validation_mask)[0]
    test_indices = np.where(test_mask)[0]

    # Check for empty splits
    if len(train_indices) == 0:
        raise ValueError("Training split is empty.")
    if len(validation_indices) == 0:
        raise ValueError("Validation split is empty.")
    if len(test_indices) == 0:
        raise ValueError("Test split is empty.")

    return SplitResult(
        train_indices=train_indices,
        validation_indices=validation_indices,
        test_indices=test_indices,
        metadata={
            "train_count": len(train_indices),
            "validation_count": len(validation_indices),
            "test_count": len(test_indices),
            "train_end_date": str(train_end),
            "validation_end_date": str(validation_end),
            "test_end_date": str(test_end),
        }
    )


def grouped_chronological_split(
    dates: list[Any],
    group_ids: list[Any],
    train_end_date: str,
    validation_end_date: str,
    test_end_date: str,
) -> SplitResult:
    """Create chronological splits with borrower-level grouping.

    All records from the same borrower (group_id) are assigned to the same split
    based on the borrower's earliest date.

    Args:
        dates: List of date values (strings or date objects).
        group_ids: List of group identifiers (e.g., borrower IDs).
        train_end_date: End date for training set (inclusive).
        validation_end_date: End date for validation set (inclusive).
        test_end_date: End date for test set (inclusive).

    Returns:
        SplitResult with indices for each split.

    Raises:
        ValueError: If dates are invalid or lengths don't match.
    """
    if len(dates) != len(group_ids):
        raise ValueError("dates and group_ids must have the same length.")

    # Parse date boundaries
    train_end = _parse_date(train_end_date)
    validation_end = _parse_date(validation_end_date)
    test_end = _parse_date(test_end_date)

    if train_end is None or validation_end is None or test_end is None:
        raise ValueError("Invalid date boundaries.")

    if not (train_end < validation_end < test_end):
        raise ValueError("Date boundaries must be in chronological order: train_end < validation_end < test_end.")

    # Parse all dates
    parsed_dates = []
    for i, d in enumerate(dates):
        parsed = _parse_date(d)
        if parsed is None:
            raise ValueError(f"Invalid date at index {i}: {d}")
        parsed_dates.append(parsed)

    # Find earliest date for each group
    group_earliest_dates = {}
    for group_id, date_val in zip(group_ids, parsed_dates):
        if group_id not in group_earliest_dates:
            group_earliest_dates[group_id] = date_val
        else:
            group_earliest_dates[group_id] = min(group_earliest_dates[group_id], date_val)

    # Assign each group to a split based on its earliest date
    group_assignments = {}
    for group_id, earliest_date in group_earliest_dates.items():
        if earliest_date <= train_end:
            group_assignments[group_id] = "train"
        elif earliest_date <= validation_end:
            group_assignments[group_id] = "validation"
        elif earliest_date <= test_end:
            group_assignments[group_id] = "test"
        else:
            group_assignments[group_id] = "excluded"

    # Assign each record to its group's split
    train_indices = []
    validation_indices = []
    test_indices = []
    excluded_indices = []

    for i, group_id in enumerate(group_ids):
        assignment = group_assignments[group_id]
        if assignment == "train":
            train_indices.append(i)
        elif assignment == "validation":
            validation_indices.append(i)
        elif assignment == "test":
            test_indices.append(i)
        else:
            excluded_indices.append(i)

    # Check for empty splits
    if len(train_indices) == 0:
        raise ValueError("Training split is empty.")
    if len(validation_indices) == 0:
        raise ValueError("Validation split is empty.")
    if len(test_indices) == 0:
        raise ValueError("Test split is empty.")

    return SplitResult(
        train_indices=np.array(train_indices),
        validation_indices=np.array(validation_indices),
        test_indices=np.array(test_indices),
        metadata={
            "train_count": len(train_indices),
            "validation_count": len(validation_indices),
            "test_count": len(test_indices),
            "excluded_count": len(excluded_indices),
            "train_end_date": str(train_end),
            "validation_end_date": str(validation_end),
            "test_end_date": str(test_end),
            "num_groups": len(group_earliest_dates),
            "groups_in_train": sum(1 for a in group_assignments.values() if a == "train"),
            "groups_in_validation": sum(1 for a in group_assignments.values() if a == "validation"),
            "groups_in_test": sum(1 for a in group_assignments.values() if a == "test"),
        }
    )


def check_train_test_overlap(
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    group_ids: list[Any] | None = None,
) -> dict[str, Any]:
    """Check for overlap between train and test sets.

    Args:
        train_indices: Indices in training set.
        test_indices: Indices in test set.
        group_ids: Optional list of group IDs to check for borrower-level overlap.

    Returns:
        Dictionary with overlap check results.
    """
    # Check index-level overlap
    index_overlap = np.intersect1d(train_indices, test_indices)
    index_overlap_count = len(index_overlap)

    result = {
        "index_overlap": index_overlap_count == 0,
        "index_overlap_count": index_overlap_count,
    }

    # Check group-level overlap if group IDs provided
    if group_ids is not None:
        train_groups = set(group_ids[i] for i in train_indices)
        test_groups = set(group_ids[i] for i in test_indices)
        group_overlap = train_groups.intersection(test_groups)
        result["group_overlap"] = len(group_overlap) == 0
        result["group_overlap_count"] = len(group_overlap)
        result["overlapping_groups"] = list(group_overlap) if group_overlap else []

    return result


def random_split(
    n_samples: int,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
) -> SplitResult:
    """Create random train/validation/test splits (NOT recommended for credit risk).

    WARNING: Random splitting is NOT recommended for credit risk evaluation
    because it can cause temporal leakage. Use chronological_split instead.

    This function is provided for baseline comparison only.

    Args:
        n_samples: Total number of samples.
        train_ratio: Proportion of data for training.
        validation_ratio: Proportion of data for validation.
        test_ratio: Proportion of data for testing.
        random_seed: Random seed for reproducibility.

    Returns:
        SplitResult with indices for each split.
    """
    if not np.isclose(train_ratio + validation_ratio + test_ratio, 1.0):
        raise ValueError("Split ratios must sum to 1.0.")

    rng = np.random.default_rng(random_seed)
    indices = rng.permutation(n_samples)

    train_end = int(n_samples * train_ratio)
    validation_end = train_end + int(n_samples * validation_ratio)

    train_indices = indices[:train_end]
    validation_indices = indices[train_end:validation_end]
    test_indices = indices[validation_end:]

    return SplitResult(
        train_indices=train_indices,
        validation_indices=validation_indices,
        test_indices=test_indices,
        metadata={
            "train_count": len(train_indices),
            "validation_count": len(validation_indices),
            "test_count": len(test_indices),
            "random_seed": random_seed,
            "warning": "Random splitting can cause temporal leakage. Use chronological_split for credit risk evaluation.",
        }
    )

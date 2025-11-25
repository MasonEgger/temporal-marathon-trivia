# ABOUTME: Integration tests for CSV export with S3 upload using moto.
# Tests end-to-end CSV generation and S3 upload with mocked AWS services.

import csv
import io

import boto3
from moto import mock_aws
from temporalio.testing import ActivityEnvironment

from src.activities.export import ExportActivities
from tests.fixtures.players import create_test_players


@mock_aws
def test_export_csv_end_to_end_with_s3() -> None:
    """Test end-to-end CSV generation and S3 upload with mocked S3."""
    # Create mock S3 bucket
    s3_client = boto3.client("s3", region_name="us-west-2")
    bucket_name = "test-marathon-bucket"
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )

    # Get test players
    players = create_test_players()

    # Run export activity
    activity_env = ActivityEnvironment()
    activities = ExportActivities()
    s3_url = activity_env.run(
        activities.export_daily_csv_to_s3,
        bucket_name,
        "us-west-2",
        "2025-03-12",
        players,
        ["2025-03-10", "2025-03-11", "2025-03-12"],
    )

    # Verify S3 URL is correct
    expected_url = f"https://{bucket_name}.s3.us-west-2.amazonaws.com/marathon-trivia-2025-03-12.csv"
    assert s3_url == expected_url

    # Verify S3 object exists
    response = s3_client.get_object(
        Bucket=bucket_name, Key="marathon-trivia-2025-03-12.csv"
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Verify CSV content
    csv_content = response["Body"].read().decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(csv_content))

    # Convert to list for easier assertions
    rows = list(csv_reader)

    # Should have 3 players
    assert len(rows) == 3

    # Verify first player (John Doe)
    assert rows[0]["email"] == "john.doe@example.com"
    assert rows[0]["first_name"] == "John"
    assert rows[0]["last_name"] == "Doe"
    assert rows[0]["total_score"] == "8"
    assert rows[0]["day1_score"] == "3"
    assert rows[0]["day2_score"] == "5"
    assert rows[0]["day3_score"] == "0"  # Not completed
    assert rows[0]["completed_days"] == "2"

    # Verify second player (Alice Smith)
    assert rows[1]["email"] == "alice.smith@example.com"
    assert rows[1]["first_name"] == "Alice"
    assert rows[1]["last_name"] == "Smith"
    assert rows[1]["total_score"] == "12"
    assert rows[1]["day1_score"] == "5"
    assert rows[1]["day2_score"] == "4"
    assert rows[1]["day3_score"] == "3"
    assert rows[1]["completed_days"] == "3"

    # Verify third player (Bob Adams)
    assert rows[2]["email"] == "bob.adams@example.com"
    assert rows[2]["first_name"] == "Bob"
    assert rows[2]["last_name"] == "Adams"
    assert rows[2]["total_score"] == "5"
    assert rows[2]["day1_score"] == "5"
    assert rows[2]["day2_score"] == "0"  # Not completed
    assert rows[2]["day3_score"] == "0"  # Not completed
    assert rows[2]["completed_days"] == "1"

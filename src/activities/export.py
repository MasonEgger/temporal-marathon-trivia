# ABOUTME: CSV export activities for player data reporting.
# Generates CSV files and uploads them to S3 for event organizers.

import csv
import io

import boto3  # type: ignore[import-untyped]
from temporalio import activity

from src.models.player import Player


class ExportActivities:
    """Activity class for CSV export and S3 upload operations."""

    @activity.defn
    def export_daily_csv_to_s3(
        self,
        bucket: str,
        region: str,
        date: str,
        players: list[Player],
        event_dates: list[str],
    ) -> str:
        """Generate CSV from player data and upload to S3.

        Creates an in-memory CSV with player data including email, name, scores,
        and uploads it to S3 with key format "marathon-trivia-{date}.csv".

        Args:
            bucket: S3 bucket name for upload.
            region: AWS region for S3 bucket.
            date: Export date in ISO format (YYYY-MM-DD).
            players: List of Player instances to include in CSV.
            event_dates: List of event dates to create day columns.

        Returns:
            S3 URL of uploaded CSV file.

        Raises:
            Exception: If S3 upload fails (Temporal will handle retries).

        Example:
            >>> activities = ExportActivities()
            >>> url = activities.export_daily_csv_to_s3(
            ...     "my-bucket",
            ...     "us-west-2",
            ...     "2025-03-12",
            ...     [player1, player2],
            ...     ["2025-03-10", "2025-03-11", "2025-03-12"]
            ... )
            >>> print(url)
            https://my-bucket.s3.us-west-2.amazonaws.com/marathon-trivia-2025-03-12.csv
        """
        # Create in-memory CSV using StringIO
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)

        # Build header row with dynamic day columns
        day_columns = [f"day{i + 1}_score" for i in range(len(event_dates))]
        header = ["email", "first_name", "last_name", "total_score"]
        header.extend(day_columns)
        header.append("completed_days")
        csv_writer.writerow(header)

        # Write player data rows
        for player in players:
            row = [
                player.email,
                player.first_name,
                player.last_name,
                player.total_score,
            ]

            # Add daily scores for each event date
            for event_date in event_dates:
                score = player.daily_scores.get(event_date, 0)
                row.append(score)

            # Add completed days count
            row.append(len(player.completed_days))

            csv_writer.writerow(row)

        # Get CSV content as string
        csv_content = csv_buffer.getvalue()

        # Upload to S3
        activity.logger.info(f"Uploading CSV for {len(players)} players to S3: {bucket}/{date}")
        s3_client = boto3.client("s3", region_name=region)
        key = f"marathon-trivia-{date}.csv"

        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=csv_content.encode("utf-8"),
            ContentType="text/csv",
        )

        # Return S3 URL
        s3_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        activity.logger.info(f"Successfully uploaded CSV to S3: {s3_url}")
        return s3_url

import asyncio
import json
from google.cloud import storage
from models import HealthSummary


def _sync_fetch(bucket_name: str, prefix: str) -> HealthSummary:
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blobs = list(bucket.list_blobs(prefix=prefix))
    if not blobs:
        return HealthSummary()

    # Use the most recently updated file
    latest = max(blobs, key=lambda b: b.updated)
    raw = json.loads(latest.download_as_bytes())

    # Health Auto Export format: {"data": {"metrics": [...], "workouts": [...]}}
    data = raw.get("data", raw)  # handle both wrapped and unwrapped formats
    metrics = {m["name"]: m.get("data", []) for m in data.get("metrics", [])}
    workouts = data.get("workouts", [])

    def _avg(records: list[dict]) -> float:
        vals = [r["qty"] for r in records if "qty" in r]
        return sum(vals) / len(vals) if vals else 0.0

    steps = metrics.get("step_count", [])
    energy = metrics.get("active_energy", [])
    sleep = metrics.get("sleep_analysis", [])

    last_workout_type = ""
    last_workout_duration_min = 0
    if workouts:
        last = sorted(workouts, key=lambda w: w.get("start", ""), reverse=True)[0]
        last_workout_type = last.get("name", "")
        last_workout_duration_min = int(last.get("duration", 0))

    data_through = ""
    all_dates = [r.get("date", "") for records in metrics.values() for r in records]
    if all_dates:
        data_through = sorted(all_dates)[-1]

    return HealthSummary(
        avg_daily_steps=int(_avg(steps)),
        avg_active_energy_kcal=round(_avg(energy), 1),
        avg_sleep_hours=round(_avg(sleep), 1),
        last_workout_type=last_workout_type,
        last_workout_duration_min=last_workout_duration_min,
        data_through=data_through,
    )


async def fetch_apple_health(bucket_name: str, prefix: str) -> HealthSummary:
    return await asyncio.to_thread(_sync_fetch, bucket_name, prefix)

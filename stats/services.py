from datetime import date
from django.db.models import BigIntegerField, Sum, Count, Value, IntegerField
from django.db.models.functions import Coalesce, TruncMonth

from videos.models import Video


WEATHER_LABELS = ["맑음", "흐림", "비", "눈", "안개"]

WEATHER_DB_TO_LABEL = {
    Video.Weather.CLEAR: "맑음",
    Video.Weather.CLOUDY: "흐림",
    Video.Weather.RAIN: "비",
    Video.Weather.SNOW: "눈",
    Video.Weather.FOG: "안개",
}

WEATHER_LABEL_TO_DB = {
    label: db_value
    for db_value, label in WEATHER_DB_TO_LABEL.items()
}


def get_base_queryset(start_date, end_date):
    return Video.objects.filter(
        status=Video.Status.COMPLETED,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )


def subtract_one_year(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        # 2월 29일 처리
        return d.replace(year=d.year - 1, day=28)


def sum_skygazer_count(qs):
    return qs.aggregate(
        total=Coalesce(
            Sum("skygazer_count"),
            Value(0),
            output_field=BigIntegerField(),
        )
    )["total"]


def get_total_detected(start_date, end_date):
    qs = get_base_queryset(start_date, end_date)
    total_detected = sum_skygazer_count(qs)

    prev_start = subtract_one_year(start_date)
    prev_end = subtract_one_year(end_date)

    prev_qs = get_base_queryset(prev_start, prev_end)
    prev_year_detected = sum_skygazer_count(prev_qs)

    if prev_year_detected == 0:
        year_over_year_change = 0 if total_detected == 0 else 100
    else:
        year_over_year_change = round(
            ((total_detected - prev_year_detected) / prev_year_detected) * 100
        )

    return {
        "totalDetected": int(total_detected),
        "prevYearDetected": int(prev_year_detected),
        "yearOverYearChange": int(year_over_year_change),
    }


def get_total_videos(start_date, end_date):
    qs = get_base_queryset(start_date, end_date)

    today = date.today()
    first_day_of_month = today.replace(day=1)

    this_month_videos = Video.objects.filter(
        status=Video.Status.COMPLETED,
        created_at__date__gte=first_day_of_month,
        created_at__date__lte=today,
    ).count()

    return {
        "totalVideos": qs.count(),
        "thisMonthVideos": this_month_videos,
    }


def get_top_region(start_date, end_date):
    qs = get_base_queryset(start_date, end_date)

    row = (
        qs.values("region__region_name")
        .annotate(
            count=Coalesce(
                Sum("skygazer_count"),
                Value(0),
                output_field=BigIntegerField(),
            )
        )
        .order_by("-count", "region__region_name")
        .first()
    )

    if not row:
        return {
            "name": "",
            "count": 0,
        }

    return {
        "name": row["region__region_name"],
        "count": row["count"],
    }


def get_top_weather(start_date, end_date):
    qs = get_base_queryset(start_date, end_date)

    total_detected = sum_skygazer_count(qs)

    row = (
        qs.values("weather")
        .annotate(
            count=Coalesce(
                Sum("skygazer_count"),
                Value(0),
                output_field=BigIntegerField(),
            )
        )
        .order_by("-count", "weather")
        .first()
    )

    if not row or total_detected == 0:
        return {
            "weather": "",
            "percentage": 0,
        }

    weather_label = WEATHER_DB_TO_LABEL.get(row["weather"], row["weather"])
    percentage = round((row["count"] / total_detected) * 100)

    return {
        "weather": weather_label,
        "percentage": int(percentage),
    }


def iter_months(start_date, end_date):
    current = date(start_date.year, start_date.month, 1)
    last = date(end_date.year, end_date.month, 1)

    while current <= last:
        yield current

        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


def get_monthly_stats(start_date, end_date):
    qs = get_base_queryset(start_date, end_date)

    rows = (
        qs.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total=Coalesce(
                Sum("skygazer_count"),
                Value(0),
                output_field=BigIntegerField(),
            )
        )
        .order_by("month")
    )

    month_map = {
        date(row["month"].year, row["month"].month, 1): int(row["total"])
        for row in rows
        if row["month"] is not None
    }

    labels = []
    data = []

    for month in iter_months(start_date, end_date):
        labels.append(f"{month.month}월")
        data.append(month_map.get(month, 0))

    return {
        "labels": labels,
        "data": data,
    }


def get_by_region_stats(start_date, end_date):
    qs = get_base_queryset(start_date, end_date)

    rows = (
        qs.values("region__region_name")
        .annotate(
            total=Coalesce(
                Sum("skygazer_count"),
                Value(0),
                output_field=BigIntegerField(),
            )
        )
        .order_by("-total", "region__region_name")
    )

    return {
        "labels": [row["region__region_name"] for row in rows],
        "data": [int(row["total"]) for row in rows],
    }


def get_by_weather_stats(start_date, end_date):
    qs = get_base_queryset(start_date, end_date)

    rows = (
        qs.values("weather")
        .annotate(
            total=Coalesce(
                Sum("skygazer_count"),
                Value(0),
                output_field=BigIntegerField(),
            )
        )
    )

    weather_map = {
        row["weather"]: int(row["total"])
        for row in rows
    }

    return {
        "labels": WEATHER_LABELS,
        "data": [
            weather_map.get(WEATHER_LABEL_TO_DB[label], 0)
            for label in WEATHER_LABELS
        ],
    }

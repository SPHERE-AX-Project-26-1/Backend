from django.shortcuts import render

from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import (
    get_total_detected,
    get_total_videos,
    get_top_region,
    get_top_weather,
    get_monthly_stats,
    get_by_region_stats,
    get_by_weather_stats,
)


def parse_date_range(request):
    start_date_str = request.query_params.get("startDate")
    end_date_str = request.query_params.get("endDate")

    if not start_date_str or not end_date_str:
        return None, Response(
            {"message": "날짜 형식이 올바르지 않습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None, Response(
            {"message": "날짜 형식이 올바르지 않습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if start_date > end_date:
        return None, Response(
            {"message": "시작일이 종료일보다 클 수 없습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return (start_date, end_date), None


class TotalDetectedAPIView(APIView):
    def get(self, request):
        date_range, error_response = parse_date_range(request)
        if error_response:
            return error_response

        start_date, end_date = date_range
        data = get_total_detected(start_date, end_date)
        return Response(data)


class TotalVideosAPIView(APIView):
    def get(self, request):
        date_range, error_response = parse_date_range(request)
        if error_response:
            return error_response

        start_date, end_date = date_range
        data = get_total_videos(start_date, end_date)
        return Response(data)


class TopRegionAPIView(APIView):
    def get(self, request):
        date_range, error_response = parse_date_range(request)
        if error_response:
            return error_response

        start_date, end_date = date_range
        data = get_top_region(start_date, end_date)
        return Response(data)


class TopWeatherAPIView(APIView):
    def get(self, request):
        date_range, error_response = parse_date_range(request)
        if error_response:
            return error_response

        start_date, end_date = date_range
        data = get_top_weather(start_date, end_date)
        return Response(data)


class MonthlyStatsAPIView(APIView):
    def get(self, request):
        date_range, error_response = parse_date_range(request)
        if error_response:
            return error_response

        start_date, end_date = date_range
        data = get_monthly_stats(start_date, end_date)
        return Response(data)


class ByRegionStatsAPIView(APIView):
    def get(self, request):
        date_range, error_response = parse_date_range(request)
        if error_response:
            return error_response

        start_date, end_date = date_range
        data = get_by_region_stats(start_date, end_date)
        return Response(data)


class ByWeatherStatsAPIView(APIView):
    def get(self, request):
        date_range, error_response = parse_date_range(request)
        if error_response:
            return error_response

        start_date, end_date = date_range
        data = get_by_weather_stats(start_date, end_date)
        return Response(data)

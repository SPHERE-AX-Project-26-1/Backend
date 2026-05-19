from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import (
    get_dashboard_home,
    get_dashboard_markers,
    get_region_detail,
    get_dashboard_summary,
)


RISK_PARAM_MAP = {
    "ALL": "ALL",
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH": "HIGH",
    "전체": "ALL",
    "보통": "LOW",
    "정상": "LOW",
    "주의": "MEDIUM",
    "위험": "HIGH",
}


def normalize_risk_param(value):
    if not value:
        return "ALL"

    value = value.strip().upper()

    if value in RISK_PARAM_MAP:
        return RISK_PARAM_MAP[value]

    return None


class DashboardHomeAPIView(APIView):
    def get(self, request):
        risk = normalize_risk_param(request.query_params.get("risk"))

        if risk is None:
            return Response(
                {"message": "위험도 필터 값이 올바르지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = get_dashboard_home(risk=risk)
        return Response(data)


class DashboardMapAPIView(APIView):
    def get(self, request):
        risk = normalize_risk_param(request.query_params.get("risk"))

        if risk is None:
            return Response(
                {"message": "위험도 필터 값이 올바르지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "markers": get_dashboard_markers(risk=risk),
        }
        return Response(data)


class DashboardRegionDetailAPIView(APIView):
    def get(self, request, region_id):
        data = get_region_detail(region_id)
        return Response(data)


class DashboardSummaryAPIView(APIView):
    def get(self, request):
        data = get_dashboard_summary()
        return Response(data)

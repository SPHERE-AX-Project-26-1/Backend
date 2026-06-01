from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated

from .services import (
    get_dashboard_summary,
    get_dashboard_rivers,
    get_top_rivers,
)


class DashboardSummaryAPIView(APIView):

    def get(self, request):
        data = get_dashboard_summary()
        return Response(data, status=drf_status.HTTP_200_OK)


class DashboardRiversAPIView(APIView):

    def get(self, request):
        risk = request.query_params.get("risk")

        try:
            data = get_dashboard_rivers(risk=risk)
        except ValueError as e:
            return Response(
                {"message": str(e)},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        return Response(data, status=drf_status.HTTP_200_OK)


class DashboardTopRiversAPIView(APIView):

    def get(self, request):
        limit = request.query_params.get("limit")

        try:
            data = get_top_rivers(limit=limit)
        except ValueError as e:
            return Response(
                {"message": str(e)},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        return Response(data, status=drf_status.HTTP_200_OK)

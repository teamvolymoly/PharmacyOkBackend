from django.db import connection
from django.db.utils import DatabaseError
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.CharField()


class HealthView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = HealthSerializer

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response({"status": "degraded", "database": "unavailable"}, status=503)
        return Response({"status": "ok", "database": "ok"})


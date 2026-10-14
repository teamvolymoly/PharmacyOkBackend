from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from common.tenancy import resolve_tenant_context

from .serializers import TenantSerializer


class CurrentTenantView(GenericAPIView):
    serializer_class = TenantSerializer

    def get(self, request):
        membership = resolve_tenant_context(request)
        return Response(self.get_serializer(membership.tenant).data)


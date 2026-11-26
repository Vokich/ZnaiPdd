from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.models import Organization
from app.organizations.directory import search_municipalities


def organization_data(organization):
    return {'id': organization.pk, 'name': organization.name, 'municipality': organization.municipality.name}


@api_view(['GET'])
def municipalities(request):
    results, more = search_municipalities(request.query_params.get('q', ''))
    return Response({'results': results, 'more': more})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organizations(request):
    query = request.query_params.get('q', '').strip()
    if not 2 <= len(query) <= 300:
        return Response([])
    organizations = Organization.objects.filter(name__icontains=query).select_related('municipality')[:30]
    return Response([organization_data(organization) for organization in organizations])

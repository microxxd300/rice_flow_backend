from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """PageNumberPagination with an optional ?page_size= (capped) and total_pages.

    Responses keep count/next/previous/results, so existing clients are unaffected.
    """
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })

    def get_paginated_response_schema(self, schema):
        response_schema = super().get_paginated_response_schema(schema)
        response_schema['properties']['total_pages'] = {'type': 'integer', 'example': 5}
        return response_schema

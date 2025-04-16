from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from urllib.parse import urlencode


class MSMEDefaultPaginationClass(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size =100
    message = ''
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = kwargs.get('message', '')
        
    def get_paginated_response(self, data):
        request = getattr(self, "request", None)
        # request = self.context.get("request")  # Get the request from context
        limit = self.request.query_params.get('page_size', 10)

        if self.page.paginator.count == 0:
            return Response({
                'status': True,
                "status_code":200,
                "message":"Data not found",
                "error":"",
                'links': {
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link()
                },
                'count': self.page.paginator.count,
                'page_size':int(limit),
                "data":data}
            )
        else:
            return Response({
                'status': True,
                "status_code":200,
                "message":self.message,
                "error":"",
                'links': {
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link()
                },
                'count': self.page.paginator.count,
                'page_size':int(limit),
                "data":data}
            )


class TTMSMEDefaultPaginationClass(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    message = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = kwargs.get('message', '')

    def get_paginated_response(self, data):
        # Retrieve request safely from self
        request = self.request if hasattr(self, 'request') else None
        limit = int(request.query_params.get('page_size', self.page_size)) if request else self.page_size

        return Response({
            'status': True,
            "status_code": 200,
            "message": self.message if data else "Data not found",
            "error": "",
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'page_size': limit,
            "data": data
        })
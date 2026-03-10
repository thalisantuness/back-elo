from rest_framework import generics
from business import Business
from business import BusinessSerializer


class BusinessCreateListView(generics.ListCreateAPIView):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
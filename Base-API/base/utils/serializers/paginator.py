from rest_framework import serializers

class PaginationSerializer(serializers.Serializer):
    page = serializers.SerializerMethodField()
    items_per_page = serializers.SerializerMethodField()
    total_pages = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

    def get_page(self, page):
        return page.number

    def get_items_per_page(self, page):
        return page.paginator.per_page

    def get_total_pages(self, page):
        return page.paginator.num_pages

    def get_total_items(self, page):
        return page.paginator.count

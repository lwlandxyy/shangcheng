from django.db.models import Q

from goods.models import Goods
from django_filters import rest_framework as filters

class GoodsFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="shop_price", lookup_expr='gte')
    max_price = filters.NumberFilter(field_name="shop_price", lookup_expr='lte')
    name =filters.CharFilter(field_name = "name",lookup_expr = 'icontains') #contains代表包含，i代表不区分大小写


    top_category = filters.NumberFilter(method='top_category_filter')
    #为了应对点击某个品类后，把该品类下的数据传递给前端
    def top_category_filter(self, queryset, name, value):
        return queryset.filter(Q(category_id=value) | Q(category__parent_category_id=value) | Q(
            category__parent_category__parent_category_id=value))

    class Meta:
        model = Goods
        fields = ['min_price', 'max_price','name','is_hot','is_new']
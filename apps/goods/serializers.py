from django.db.models import Q
from rest_framework import serializers

from goods.models import Goods, GoodsCategory, GoodsImage, Banner, GoodsCategoryBrand, IndexAd


class GoodsImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsImage
        fields = ("image", )
class CategorySerializer3(serializers.ModelSerializer):

    class Meta:
        model = GoodsCategory
        fields = "__all__"


class CategorySerializer2(serializers.ModelSerializer):
    sub_cat = CategorySerializer3(many=True)  #序列化字段名字必须是模型类中的parent_category
    class Meta:
        model = GoodsCategory
        fields = "__all__"
class CategorySerializer(serializers.ModelSerializer):
    sub_cat = CategorySerializer2(many=True)
    class Meta:
        model = GoodsCategory
        fields = "__all__"
class GoodsSerializer(serializers.ModelSerializer):
    images = GoodsImageSerializer(many=True)
    category = CategorySerializer()
    class Meta :
        model = Goods
        fields = '__all__'

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = "__all__"

# 首页商品分类显示功能，商品的品牌信息
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsCategoryBrand
        fields = "__all__"



# 商品分类显示序列化类
class IndexCategorySerializer(serializers.ModelSerializer):
    brands = BrandSerializer(many=True)  # 首先是拿到品牌信息，品牌表中的Category id是外键
    goods = serializers.SerializerMethodField()  # 因为我们拿到的Category是最顶级的级别，下面是没有商品的，所以不能用GoodsSerializer，这个是最右边的商品
    sub_cat = CategorySerializer2(many=True)  # 左下角的二级分类数据
    ad_goods = serializers.SerializerMethodField()  # 处于从中间大图的广告位

    def get_ad_goods(self, obj):
        goods_json = {}
        ad_goods = IndexAd.objects.filter(category_id=obj.id, )
        if ad_goods:  # 如果广告表中有数据
            good_ins = ad_goods[0].goods
            # 加入context={'request': self.context['request']}的作用是我们的图片资源带有访问的url，在view中我们调用serializer时，看ListModelMixin上下文是自动传进来的，而我们自己的serializer在调用serializer时，是没有的，所以我们自己加上
            goods_json = GoodsSerializer(good_ins, many=False, context={'request': self.context['request']}).data
        return goods_json

    # 对应的是上面goods的字段，具体可以看SerializerMethodField类
    def get_goods(self, obj):
        # 这个商品过滤我们在filters中top_category_filter已经使用过，就是找到某个大类下的所有商品
        all_goods = Goods.objects.filter(Q(category_id=obj.id) | Q(category__parent_category_id=obj.id) | Q(
            category__parent_category__parent_category_id=obj.id))
        # 下面两条是我们在构造一个serializer,可以看下ListModelMixin类，也是传递request得到serializer
        goods_serializer = GoodsSerializer(all_goods, many=True, context={'request': self.context['request']})
        return goods_serializer.data  # goods_serializer.data里边存的json数据

    class Meta:
        model = GoodsCategory
        fields = "__all__"
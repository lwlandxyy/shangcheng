
from rest_framework import serializers
from goods.serializers import GoodsSerializer
from goods.models import Goods
from shop5.settings import private_key_path, ali_pub_key_path
# from shop5.settings import private_key_path, ali_pub_key_path
from utils.alipay import AliPay
from .models import ShoppingCart, OrderInfo, OrderGoods

class ShopCartDetailSerializer(serializers.ModelSerializer) :
    """
    列表页使用的序列化类
    """
    goods = GoodsSerializer(many = False, read_only = True)

    class Meta :
        model = ShoppingCart
        fields = ("goods", "nums")


class ShopCartSerializer(serializers.Serializer) :
    user = serializers.HiddenField(
        default = serializers.CurrentUserDefault()
    )
    nums = serializers.IntegerField(required = True, label = "数量", min_value = 1,
                                    error_messages = {
                                        "min_value" : "商品数量不能小于一",
                                        "required" : "请选择购买数量"
                                    })
    goods = serializers.PrimaryKeyRelatedField(required = True, queryset = Goods.objects.all())

    def create(self, validated_data ) :
        # 在序列化类中通过self.context["request"]就可以拿到request对象
        user = self.context["request"].user
        nums = validated_data[ "nums" ]
        goods = validated_data[ "goods" ]

        existed = ShoppingCart.objects.filter(user = user, goods = goods)

        if existed :  #购物车中原本已经有了，就修改数量，不是新增一条资料
            existed = existed[0]
            existed.nums += nums
            existed.save()
        else :
            existed = ShoppingCart.objects.create(**validated_data)
        # 加入购物车几个就把商品数目减去几个
        goods=existed.goods
        goods.goods_num-=nums
        goods.save()
        return existed

    def update( self, instance, validated_data ) :
        # 修改商品数量，前端在修改时，直接传输过来的是最终数目
        instance.nums = validated_data[ "nums" ]
        instance.save()
        return instance

import time
class OrderGoodsSerialzier(serializers.ModelSerializer):
    goods = GoodsSerializer(many=False)#一个商品id只会对应一件商品
    class Meta:
        model = OrderGoods
        fields = "__all__"

class OrderDetailSerializer(serializers.ModelSerializer):
    goods = OrderGoodsSerialzier(many=True)#一个订单id可以有多个商品
    #SerializerMethodField自定义的serializer，无需用户提交
    alipay_url = serializers.SerializerMethodField(read_only=True)

    def get_alipay_url(self, obj):
        server_ip = "47.112.116.110"  # 改为你自己的公网IP
        alipay = AliPay(
            appid="2016101400687743",
            # app_notify_url="http://127.0.0.1:8000/alipay/return/",
            app_notify_url="http://" + server_ip + ":8000/alipay/return/",
            app_private_key_path=private_key_path,
            alipay_public_key_path=ali_pub_key_path,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            debug=True,  # 默认False,
            return_url="http://" + server_ip + ":8000/alipay/return/"
        )

        url = alipay.direct_pay(
            subject=obj.order_sn,
            out_trade_no=obj.order_sn,
            total_amount=obj.order_mount,
        )
        re_url = "https://openapi.alipaydev.com/gateway.do?{data}".format(data=url)

        return re_url

    class Meta:
        model = OrderInfo
        fields = "__all__"
class OrderSerializer(serializers.ModelSerializer):
    #用户信息默认不用提交，因为我们已经登录，当然知道谁提交订单
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    #订单号每次生成
    def generate_order_sn(self):
        # 当前时间+userid+随机数
        from random import Random
        random_ins = Random()
        order_sn = "{time_str}{userid}{ranstr}".format(time_str=time.strftime("%Y%m%d%H%M%S"),
                                                       userid=self.context["request"].user.id, ranstr=random_ins.randint(10, 99))

        return order_sn

    def validate(self, attrs):
        """
        页面不需要提交某个字段，但是后端通过代码来生成这个字段的操作
        :param attrs:
        :return:
        """
        attrs["order_sn"] = self.generate_order_sn()
        return attrs

    alipay_url = serializers.SerializerMethodField(read_only=True)

    def get_alipay_url(self, obj):
        server_ip = "127.0.0.1"  # 改为你自己的公网IP
        alipay = AliPay(
            appid="2016101400687743",
            # app_notify_url="http://127.0.0.1:8000/alipay/return/",
            app_notify_url="http://" + server_ip + ":8000/alipay/return/",
            app_private_key_path=private_key_path,
            alipay_public_key_path=ali_pub_key_path,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            debug=True,  # 默认False,
            return_url="http://" + server_ip + ":8000/alipay/return/"
        )

        url = alipay.direct_pay(
            subject=obj.order_sn,
            out_trade_no=obj.order_sn,
            total_amount=obj.order_mount,
        )
        re_url = "https://openapi.alipaydev.com/gateway.do?{data}".format(data=url)

        return re_url

    class Meta:
        model = OrderInfo
        fields = "__all__"
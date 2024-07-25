from django.shortcuts import render, redirect
from rest_framework import viewsets,mixins
from rest_framework.permissions import IsAuthenticated

from trade.models import ShoppingCart, OrderInfo, OrderGoods
from trade.serializers import ShopCartSerializer, ShopCartDetailSerializer, OrderSerializer
from utils.permissions import IsOwnerOrReadOnly


# Create your views here.
class ShoppingCartViewset(viewsets.ModelViewSet):
    """
    购物车功能
    list:
        获取购物车详情
    create：
        加入购物车
    delete：
        删除购物记录
    """
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    serializer_class = ShopCartSerializer
    lookup_field = "goods_id"  # 为查询，修改，删除提供的id，默认是主键，现在改变了
    def get_queryset(self):
        return ShoppingCart.objects.filter(user=self.request.user)
    def get_serializer_class(self):
        if self.action == 'list':
            return ShopCartDetailSerializer
        else:
            return ShopCartSerializer
class OrderViewset(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin,
                   viewsets.GenericViewSet):
    """
    订单管理
    list:
        获取个人订单
    delete:
        删除订单
    create：
        新增订单
    """
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
    serializer_class = OrderSerializer
    # def get_serializer_class(self):
    #     if self.action == "retrieve":
    #         return OrderDetailSerializer
    #     return OrderSerializer

    def get_queryset(self):
        """
        每个人只能看到自己的订单
        :return:
        """
        return OrderInfo.objects.filter(user=self.request.user)

    # perform_create用于对我们的实例进行修改
    def perform_create(self, serializer):
        order = serializer.save()
        # 拿到购物车中的信息
        shop_carts = ShoppingCart.objects.filter(user=self.request.user)
        # 遍历购物车
        order_mount = 0
        for shop_cart in shop_carts:
            order_goods = OrderGoods()
            order_goods.goods = shop_cart.goods
            order_goods.goods_num = shop_cart.nums
            order_mount += order_goods.goods.shop_price * shop_cart.nums
            order_goods.order = order
            # 订单商品信息保存
            order_goods.save()
            # 清空购物车
            shop_cart.delete()
        # 把我们自己算出的订单金额保存进去
        print(order_mount)
        order.order_mount = order_mount
        order.save()
        return order

        # 购物车数目删除几个，就加回去
        def perform_destroy(self, instance):
            goods = instance.goods
            goods.goods_num += instance.nums
            goods.save()
            instance.delete()

        # 修改了购物车数目，也要
        def perform_update(self, serializer):
            existed_record = ShoppingCart.objects.get(id=serializer.instance.id)
            existed_nums = existed_record.nums  # 变化之前的数量，因为变化之前的数量是存入了数据库的
            saved_record = serializer.save()  # 变化后的数量存入数据库
            nums = saved_record.nums - existed_nums  # nums可正可负
            goods = saved_record.goods
            goods.goods_num -= nums
            goods.save()  # 把商品库存数目更新


from rest_framework.views import APIView
from utils.alipay import AliPay
from shop5.settings import ali_pub_key_path, private_key_path
from rest_framework.response import Response
from datetime import datetime


class AlipayView(APIView):
    server_ip = "127.0.0.1:8000"  #改为你的公网IP
    alipay = AliPay(
        appid="2016101400687743",
        # app_notify_url="http://127.0.0.1:8000/alipay/return/",
        app_notify_url="http://" + server_ip + "/alipay/return/",
        app_private_key_path=private_key_path,
        alipay_public_key_path=ali_pub_key_path,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        debug=True,  # 默认False,
        return_url="http://" + server_ip + "/alipay/return/"
    )

    def get(self, request):
        """
        处理支付宝的return_url返回
        :param request:
        :return:
        """
        processed_dict = {}
        for key, value in request.GET.items():
            processed_dict[key] = value

        sign = processed_dict.pop("sign", None)

        verify_re = self.alipay.verify(processed_dict, sign)
        # 这里我们可以调试看一下，如果verify_re为真，说明验证成功
        if verify_re is True:
            # order_sn = processed_dict.get('out_trade_no', None)  # 订单号
            # trade_no = processed_dict.get('trade_no', None)  # 支付宝交易号
            # trade_status = processed_dict.get('trade_status', None)  # 交易状态
            #
            # existed_orders = OrderInfo.objects.filter(order_sn=order_sn)
            # for existed_order in existed_orders:
            #     existed_order.pay_status = trade_status  # 更新交易状态
            #     existed_order.trade_no = trade_no
            #     existed_order.pay_time = datetime.now()
            #     existed_order.save()

            # 订单没支付，跳转到支付页面
            response = redirect("/index/#/app/home/member/order")
            # response.set_cookie("nextPath","pay", max_age=3)
            return response
        else:
            response = redirect("/index/#/app/home/member/order")
            return response

    def post(self, request):
        """
        处理支付宝的notify_url，异步的，支付宝发过来的是post请求
        :param request:
        :return:
        """
        processed_dict = {}

        for key, value in request.POST.items():
            processed_dict[key] = value

        sign = processed_dict.pop("sign", None)

        verify_re = self.alipay.verify(processed_dict, sign)

        if verify_re is True:
            order_sn = processed_dict.get('out_trade_no', None)  #我们的订单
            trade_no = processed_dict.get('trade_no', None)  #阿里会生成一个交易号
            trade_status = processed_dict.get('trade_status', None)

            existed_orders = OrderInfo.objects.filter(order_sn=order_sn)

            for existed_order in existed_orders:
                # 一旦订单完成支付，我们查询订单中的所有商品，对商品销量进行增加，后面会讲
                order_goods = existed_order.goods.all()
                for order_good in order_goods:
                    goods = order_good.goods
                    goods.sold_num += order_good.goods_num
                    goods.save()

                existed_order.pay_status = trade_status
                existed_order.trade_no = trade_no
                existed_order.pay_time = datetime.now()
                existed_order.save()

            return Response("success")
from datetime import datetime, timedelta

from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator
import re
from users.models import VerifyCode
from shop5.settings import REGEX_MOBILE
User = get_user_model()
class SmsSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=11)

    def validate_mobile(self, mobile):
        """
        验证手机号码
        :param data:
        :return:
        """

        # 手机是否注册
        if User.objects.filter(mobile=mobile).count():
            raise serializers.ValidationError("用户已经存在")

        # 验证手机号码是否合法
        if not re.match(REGEX_MOBILE, mobile):
            raise serializers.ValidationError("手机号码非法")

        # 验证码发送频率
        one_mintes_ago = datetime.now() - timedelta(hours=0, minutes=1, seconds=0)
        if VerifyCode.objects.filter(add_time__gt=one_mintes_ago, mobile=mobile).count():
            raise serializers.ValidationError("距离上一次发送未超过60s")
#验证通过，返回手机号
        return mobile

class UserRegSerializer(serializers.ModelSerializer):
    '''
    用户注册序列化类
    '''
    #required=True代表必须有该字段
    code = serializers.CharField(required=True, write_only=True, max_length=4, min_length=4,
                                 label="验证码",
                                 error_messages={
                                     "blank": "请输入验证码",
                                     "required": "请输入验证码1",#代表json格式数据中没带
                                     "max_length": "验证码不能超过4位",
                                     "min_length": "验证码不能低于4位"
                                 },
                                 help_text="验证码")
    username = serializers.CharField(label="用户名", help_text="用户名", required=True,
                                     allow_blank=False,
                                     validators=[UniqueValidator(queryset=User.objects.all(),
                                                                 message="用户已经存在")])

    password = serializers.CharField(
        style={'input_type': 'password'},help_text="密码", label="密码", write_only=True,
    )

    def create(self, validated_data):
        user = super().create(validated_data=validated_data)
        user.set_password(validated_data["password"]) # set_password把明文密码变为密文
        user.save()
        return user

    def validate_code(self, code):
        # 不用get是因为写起来比较麻烦，而且时间判断也麻烦
        # try:
        #     verify_records = VerifyCode.objects.get(mobile=self.initial_data["username"], code=code)
        # except VerifyCode.DoesNotExist as e:
        #     pass
        # except VerifyCode.MultipleObjectsReturned as e:
        #     pass
        verify_records = VerifyCode.objects.filter(mobile=self.initial_data["username"]).order_by("-add_time")
        if verify_records:
            last_record = verify_records[0]

            five_mintes_ago = datetime.now() - timedelta(hours=0, minutes=5, seconds=0)
            if five_mintes_ago > last_record.add_time:
                raise serializers.ValidationError("验证码过期")

            if last_record.code != code:
                raise serializers.ValidationError("验证码错误")

        else:
            raise serializers.ValidationError("验证码错误")
    #validate作用于所有字段，因为我们想直接将用户名赋值给手机号，这也是我们在models中设计mobile可以为空的原因
    def validate(self, attrs):
        attrs["mobile"] = attrs["username"]
        del attrs["code"] #因为user表中不需要存code，所以删除
        return attrs

    class Meta:
        model = User
        #这里一般是和前端对应，当然通过validate可以操作，这里写的字段我们直接访问链接时都会呈现
        fields = ("username", "code", "mobile", "password")


class UserDetailSerializer(serializers.ModelSerializer):
    """
    用户详情序列化类
    """
    class Meta:
        model = User
        fields = ("name", "gender", "birthday", "email", "mobile")
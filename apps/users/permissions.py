from rest_framework import permissions


class IsOwnerOrNone(permissions.BasePermission):
    """
    删除时，不同用户不能删除其他用户的收藏
    """

    def has_object_permission(self, request, view, obj):

        return obj == request.user
from rest_framework import serializers
from .models import User, Table, Order, Payment

class UserSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)

    class Meta:
        model = User
        fields = ('_id', 'name', 'email', 'phone', 'role')


class TableSimpleSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)

    class Meta:
        model = Table
        fields = ('_id', 'tableNo', 'status', 'seats')


class TableSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)
    currentOrder = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = ('_id', 'tableNo', 'status', 'seats', 'currentOrder')

    def get_currentOrder(self, obj):
        if obj.currentOrder:
            return {
                '_id': str(obj.currentOrder.id),
                'customerDetails': obj.currentOrder.customerDetails
            }
        return None


class OrderSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)
    table = serializers.PrimaryKeyRelatedField(
        queryset=Table.objects.all(), 
        required=False, 
        allow_null=True
    )

    class Meta:
        model = Order
        fields = (
            '_id', 'customerDetails', 'orderStatus', 'orderDate', 
            'bills', 'items', 'table', 'paymentMethod', 'paymentData'
        )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Populate table details in output (matching mongoose populate behavior)
        if instance.table:
            rep['table'] = TableSimpleSerializer(instance.table).data
        else:
            rep['table'] = None
        return rep


class PaymentSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='id', read_only=True)

    class Meta:
        model = Payment
        fields = (
            '_id', 'paymentId', 'orderId', 'amount', 'currency', 
            'status', 'method', 'email', 'contact', 'createdAt'
        )

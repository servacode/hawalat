"""حوالات — Serializers الحركات."""

from rest_framework import serializers

from apps.boxes.models import Currency

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    created_by_code = serializers.CharField(source="created_by.office_code", read_only=True)
    box_name = serializers.CharField(source="box.name", read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "reference_code",
            "sender",
            "beneficiary",
            "destination",
            "amount",
            "currency_received",
            "currency_delivered",
            "exchange_rate",
            "amount_delivered",
            "fee_cost",
            "fee_charged",
            "box",
            "box_name",
            "approval_status",
            "payment_status",
            "delivery_status",
            "created_by_name",
            "created_by_code",
            "created_at",
            "approved_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        return obj.created_by.first_name or obj.created_by.username


class CreateTransactionSerializer(serializers.Serializer):
    sender = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    beneficiary = serializers.CharField(max_length=150)
    amount = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)
    currency_received = serializers.CharField(max_length=8)
    currency_delivered = serializers.CharField(max_length=8)
    destination = serializers.CharField(max_length=150)

    def validate(self, attrs):
        # العملات يجب أن تكون معرّفة لدى المستأجر (يديرها الكبير)
        codes = set(Currency.objects.filter(is_active=True).values_list("code", flat=True))
        for f in ("currency_received", "currency_delivered"):
            if attrs[f] not in codes:
                raise serializers.ValidationError({f: "عملة غير معرّفة لدى مكتبك."})
        return attrs


class ApproveSerializer(serializers.Serializer):
    box = serializers.IntegerField()
    fee_cost = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)
    fee_charged = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)
    exchange_rate = serializers.DecimalField(
        max_digits=18, decimal_places=6, required=False, allow_null=True
    )
    amount_delivered = serializers.DecimalField(
        max_digits=18, decimal_places=4, required=False, allow_null=True
    )

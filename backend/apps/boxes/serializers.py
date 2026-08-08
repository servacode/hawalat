"""حوالات — Serializers الصناديق والعملات والتسويات."""

from rest_framework import serializers

from .models import CreditLimit, Currency, IntermediaryBox


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "is_active"]


class IntermediaryBoxSerializer(serializers.ModelSerializer):
    currencies = serializers.SlugRelatedField(
        many=True, slug_field="code", queryset=Currency.objects.all()
    )
    balances = serializers.SerializerMethodField()

    class Meta:
        model = IntermediaryBox
        fields = ["id", "name", "number", "currencies", "is_active", "balances"]

    def get_balances(self, obj):
        return [
            {"currency": link.currency, "balance": str(link.account.balance)}
            for link in obj.currency_accounts.select_related("account")
        ]


class CreditLimitSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = CreditLimit
        fields = ["id", "user", "username", "currency", "negative_limit"]


class MemberPaymentSerializer(serializers.Serializer):
    """دفعة نقدية من مكتب صغير لصندوق المحل (ملاحظة 54) — الملاحظة إلزامية."""

    member = serializers.IntegerField()
    currency = serializers.CharField(max_length=8)
    amount = serializers.DecimalField(max_digits=18, decimal_places=4)
    memo = serializers.CharField(
        max_length=255,
        error_messages={"required": "الملاحظة إلزامية.", "blank": "الملاحظة إلزامية."},
    )


class SettlementSerializer(serializers.Serializer):
    box = serializers.IntegerField()
    small_user = serializers.IntegerField()
    currency = serializers.CharField(max_length=8)
    amount = serializers.DecimalField(max_digits=18, decimal_places=4)
    # سبب واضح إلزامي: لماذا اعتمدنا/سحبنا (ملاحظة 16)
    memo = serializers.CharField(
        max_length=255,
        error_messages={"required": "سبب العملية إلزامي.", "blank": "سبب العملية إلزامي."},
    )

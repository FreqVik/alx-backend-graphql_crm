import re
import decimal
import graphene
from django.db import transaction
from django.core.exceptions import ValidationError
from crm.models import Customer, Product, Order
from django.utils import timezone
from graphene_django.filter import DjangoFilterConnectionField
from crm.filters import CustomerFilter, ProductFilter, OrderFilter
from graphene import relay


# ---------- GraphQL Types ----------
class CustomerType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    email = graphene.String()
    phone = graphene.String()


class ProductType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    price = graphene.Float()
    stock = graphene.Int()


class OrderType(graphene.ObjectType):
    id = graphene.Int()
    customer = graphene.Field(CustomerType)
    products = graphene.List(ProductType)
    total_amount = graphene.Float()
    order_date = graphene.DateTime()


# ---------- Input Types ----------
class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int(required=False, default_value=0)


class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime(required=False)


# ---------- Utility Validators ----------
def validate_phone(phone):
    if phone and not re.match(r"^(\+?\d{7,15}|(\d{3}-\d{3}-\d{4}))$", phone):
        raise ValidationError("Invalid phone format. Use +1234567890 or 123-456-7890.")


def validate_price_and_stock(price, stock):
    if price <= 0:
        raise ValidationError("Price must be positive.")
    if stock < 0:
        raise ValidationError("Stock cannot be negative.")


# ---------- Mutations ----------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, input):
        try:
            if Customer.objects.filter(email=input.email).exists():
                raise ValidationError("Email already exists.")
            validate_phone(input.phone)
            customer = Customer.objects.create(
                name=input.name, email=input.email, phone=input.phone
            )
            return CreateCustomer(customer=customer, message="Customer created successfully.")
        except ValidationError as e:
            return CreateCustomer(customer=None, message=str(e))


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CreateCustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, input):
        created_customers = []
        errors = []

        for data in input:
            try:
                if Customer.objects.filter(email=data.email).exists():
                    raise ValidationError(f"Email already exists: {data.email}")
                validate_phone(data.phone)
                customer = Customer.objects.create(
                    name=data.name, email=data.email, phone=data.phone
                )
                created_customers.append(customer)
            except ValidationError as e:
                errors.append(str(e))

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    product = graphene.Field(ProductType)
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, input):
        try:
            validate_price_and_stock(input.price, input.stock)
            product = Product.objects.create(
                name=input.name, price=decimal.Decimal(input.price), stock=input.stock or 0
            )
            return CreateProduct(product=product, message="Product created successfully.")
        except ValidationError as e:
            raise graphene.GraphQLError(str(e))


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()

    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, input):
        try:
            customer = Customer.objects.get(id=input.customer_id)
        except Customer.DoesNotExist:
            raise graphene.GraphQLError(f"Customer with ID {input.customer_id} does not exist.")

        products = list(Product.objects.filter(id__in=input.product_ids))
        if len(products) != len(input.product_ids):
            raise graphene.GraphQLError("One or more product IDs are invalid.")

        order_date = input.order_date or timezone.now()
        order = Order.objects.create(customer=customer, order_date=order_date)
        order.products.set(products)
        order.total_amount = sum(p.price for p in products)
        order.save()

        return CreateOrder(
            order=OrderType(
                id=order.id,
                customer=order.customer,
                products=products,
                total_amount=float(order.total_amount),
                order_date=order.order_date,
            ),
            message="Order created successfully.",
        )


# ---------- Root Schema ----------
class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)
    all_products = graphene.List(ProductType)
    all_orders = graphene.List(OrderType)

    def resolve_all_customers(self, info):
        return Customer.objects.all()

    def resolve_all_products(self, info):
        return Product.objects.all()

    def resolve_all_orders(self, info):
        return Order.objects.all()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


class CustomerNode(graphene.ObjectType):
    class Meta:
        name = "CustomerNode"


class ProductNode(graphene.ObjectType):
    class Meta:
        name = "ProductNode"


class OrderNode(graphene.ObjectType):
    class Meta:
        name = "OrderNode"


class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerType, filterset_class=CustomerFilter)
    all_products = DjangoFilterConnectionField(ProductType, filterset_class=ProductFilter)
    all_orders = DjangoFilterConnectionField(OrderType, filterset_class=OrderFilter)
    order_by = graphene.String(required=False)

    def resolve_all_customers(self, info, **kwargs):
        order_by = kwargs.get("order_by")
        qs = Customer.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_products(self, info, **kwargs):
        order_by = kwargs.get("order_by")
        qs = Product.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_orders(self, info, **kwargs):
        order_by = kwargs.get("order_by")
        qs = Order.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs
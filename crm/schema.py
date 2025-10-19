import re
import decimal
import graphene
from django.db import transaction
from django.core.exceptions import ValidationError
from crm.models import Customer, Product, Order


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
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, name, email, phone=None):
        try:
            if Customer.objects.filter(email=email).exists():
                raise ValidationError("Email already exists.")
            validate_phone(phone)
            customer = Customer.objects.create(name=name, email=email, phone=phone)
            return CreateCustomer(customer=customer, message="Customer created successfully.")
        except ValidationError as e:
            return CreateCustomer(customer=None, message=str(e))


# ---------- Input Types ----------
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


# ---------- Mutations ----------
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, input):
        created_customers = []
        errors = []

        for data in input:
            try:
                name = data.name
                email = data.email
                phone = getattr(data, "phone", None)

                if Customer.objects.filter(email=email).exists():
                    raise ValidationError(f"Email already exists: {email}")
                validate_phone(phone)
                customer = Customer.objects.create(name=name, email=email, phone=phone)
                created_customers.append(customer)
            except ValidationError as e:
                errors.append(str(e))

        return BulkCreateCustomers(customers=created_customers, errors=errors)


    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, input):
        created_customers = []
        errors = []

        for data in input:
            try:
                name = data.get("name")
                email = data.get("email")
                phone = data.get("phone")

                if Customer.objects.filter(email=email).exists():
                    raise ValidationError(f"Email already exists: {email}")
                validate_phone(phone)
                customer = Customer.objects.create(name=name, email=email, phone=phone)
                created_customers.append(customer)
            except ValidationError as e:
                errors.append(str(e))

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(required=False, default_value=0)

    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, name, price, stock=0):
        try:
            validate_price_and_stock(price, stock)
            product = Product.objects.create(name=name, price=decimal.Decimal(price), stock=stock)
            return CreateProduct(product=product)
        except ValidationError as e:
            raise graphene.GraphQLError(str(e))


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.Int(required=True)
        product_ids = graphene.List(graphene.Int, required=True)

    order = graphene.Field(OrderType)

    @classmethod
    @transaction.atomic
    def mutate(cls, root, info, customer_id, product_ids):
        if not product_ids:
            raise graphene.GraphQLError("At least one product must be selected.")

        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise graphene.GraphQLError(f"Customer with ID {customer_id} does not exist.")

        products = list(Product.objects.filter(id__in=product_ids))
        if len(products) != len(product_ids):
            raise graphene.GraphQLError("One or more product IDs are invalid.")

        order = Order.objects.create(customer_id=customer)
        total_amount = sum(p.price for p in products)

        # Note: To truly link products to orders, a many-to-many model would be needed.
        # For this task, we’ll assume a single product per order for demonstration.
        # If multiple products are expected, you'd use an intermediary table.

        # Create multiple orders if multiple products are passed
        if len(products) > 1:
            Order.objects.filter(id=order.id).delete()
            orders = []
            for p in products:
                orders.append(Order.objects.create(customer_id=customer, product_id=p))
            order = orders[0]  # Return the first for simplicity

        return CreateOrder(
            order=OrderType(
                id=order.id,
                customer=order.customer_id,
                products=products,
                total_amount=float(total_amount),
                order_date=order.order_date,
            )
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

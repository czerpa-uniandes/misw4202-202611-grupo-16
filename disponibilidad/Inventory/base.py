from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields
from flask_restful import Api, Resource
from redis import Redis
from rq import Queue

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = \
    'postgresql://postgres:postgres@postgres/inventory'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)

# Cola Redis
q = Queue(connection=Redis(host='redis', port=6379, db=0))


class HotelProperty(db.Model):
    __tablename__ = "hotel_property"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    category = db.Column(db.String(50))

    room_types = db.relationship(
        "RoomType",
        backref="hotel",
        cascade="all, delete-orphan",
        lazy=True
    )

    pms_integrations = db.relationship(
        "PmsIntegration",
        backref="hotel",
        cascade="all, delete-orphan",
        lazy=True
    )


class RoomType(db.Model):
    __tablename__ = "room_type"

    id = db.Column(db.Integer, primary_key=True)
    hotel_property_id = db.Column(
        db.Integer,
        db.ForeignKey("hotel_property.id"),
        nullable=False
    )

    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    bed_configuration = db.Column(db.String(150))

    rate_plans = db.relationship(
        "RatePlan",
        backref="room_type",
        cascade="all, delete-orphan",
        lazy=True
    )

    inventory_items = db.relationship(
        "InventoryItem",
        backref="room_type",
        cascade="all, delete-orphan",
        lazy=True
    )


class RatePlan(db.Model):
    __tablename__ = "rate_plan"

    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(
        db.Integer,
        db.ForeignKey("room_type.id"),
        nullable=False
    )

    name = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    refundable = db.Column(db.Boolean, default=True)
    cancellation_policy = db.Column(db.String(255))

    inventory_items = db.relationship(
        "InventoryItem",
        backref="rate_plan",
        lazy=True
    )


class InventoryItem(db.Model):
    __tablename__ = "inventory_item"

    id = db.Column(db.Integer, primary_key=True)

    room_type_id = db.Column(
        db.Integer,
        db.ForeignKey("room_type.id"),
        nullable=False
    )

    rate_plan_id = db.Column(
        db.Integer,
        db.ForeignKey("rate_plan.id"),
        nullable=False
    )

    date = db.Column(db.Date, nullable=False)
    available_quantity = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "room_type_id",
            "rate_plan_id",
            "date",
            name="uq_inventory_per_day"
        ),
        db.Index("idx_inventory_date", "date"),
    )


class PmsIntegration(db.Model):
    __tablename__ = "pms_integration"

    id = db.Column(db.Integer, primary_key=True)

    hotel_property_id = db.Column(
        db.Integer,
        db.ForeignKey("hotel_property.id"),
        nullable=False
    )

    provider_name = db.Column(db.String(100))
    external_hotel_id = db.Column(db.String(100))
    sync_mode = db.Column(db.String(50))


class HotelSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = HotelProperty
        include_relationships = True
        load_instance = True


class RoomTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = RoomType
        include_fk = True
        load_instance = True


class RatePlanSchema(ma.SQLAlchemyAutoSchema):

    base_price = fields.Decimal(as_string=True)
    class Meta:
        model = RatePlan
        include_fk = True
        load_instance = True


class InventoryItemSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = InventoryItem
        include_fk = True
        load_instance = True


hotel_schema = HotelSchema()
room_type_schema = RoomTypeSchema()
rate_plan_schema = RatePlanSchema()
inventory_item_schema = InventoryItemSchema()

inventory_items_schema = InventoryItemSchema(many=True)
from base import (
    app, api, db,
    HotelProperty, RoomType, RatePlan, InventoryItem,
    hotel_schema, room_type_schema,
    rate_plan_schema, inventory_item_schema,
    Resource, request, q
)

from updater import process_reservation
from datetime import datetime
from heartbeat import start_heartbeat


class HotelResource(Resource):

    def post(self):
        hotel = HotelProperty(
            name=request.json['name'],
            address=request.json.get('address'),
            country=request.json.get('country'),
            city=request.json.get('city'),
            category=request.json.get('category')
        )

        db.session.add(hotel)
        db.session.commit()

        return hotel_schema.dump(hotel), 201


class RoomTypeResource(Resource):

    def post(self):
        room_type = RoomType(
            hotel_property_id=request.json['hotel_property_id'],
            name=request.json['name'],
            capacity=request.json['capacity'],
            bed_configuration=request.json.get('bed_configuration')
        )

        db.session.add(room_type)
        db.session.commit()

        return room_type_schema.dump(room_type), 201


class RatePlanResource(Resource):

    def post(self):
        rate_plan = RatePlan(
            room_type_id=request.json['room_type_id'],
            name=request.json['name'],
            currency=request.json['currency'],
            base_price=request.json['base_price'],
            refundable=request.json.get('refundable', True),
            cancellation_policy=request.json.get('cancellation_policy')
        )

        db.session.add(rate_plan)
        db.session.commit()

        return rate_plan_schema.dump(rate_plan), 201


class InventoryResource(Resource):

    def post(self):

        inventory = InventoryItem(
            room_type_id=request.json['room_type_id'],
            rate_plan_id=request.json['rate_plan_id'],
            date=datetime.strptime(request.json['date'], "%Y-%m-%d").date(),
            available_quantity=request.json['available_quantity']
        )

        db.session.add(inventory)
        db.session.commit()

        return inventory_item_schema.dump(inventory), 201


class ReservationResource(Resource):

    def post(self):

        data = request.json

        q.enqueue(
            process_reservation,
            data['room_type_id'],
            data['rate_plan_id'],
            data['start_date'],
            data['end_date']
        )

        return {"message": "Reservation processing"}, 202


api.add_resource(HotelResource, '/api-commands/hotels')
api.add_resource(RoomTypeResource, '/api-commands/room-types')
api.add_resource(RatePlanResource, '/api-commands/rate-plans')
api.add_resource(InventoryResource, '/api-commands/inventory')
api.add_resource(ReservationResource, '/api-commands/reservations')


if __name__ == '__main__':
    start_heartbeat()
    app.run(debug=True, host='0.0.0.0')
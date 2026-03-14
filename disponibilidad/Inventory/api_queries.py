from base import (
    app, api,
    HotelProperty, RoomType, RatePlan, InventoryItem,
    hotel_schema, room_type_schema,
    rate_plan_schema,
    inventory_item_schema, inventory_items_schema,
    Resource, request
)
from heartbeat import start_heartbeat
from datetime import datetime


class HotelListResource(Resource):

    def get(self):
        hotels = HotelProperty.query.all()
        return hotel_schema.dump(hotels, many=True)


class RoomTypeByHotelResource(Resource):

    def get(self, hotel_id):
        room_types = RoomType.query.filter_by(
            hotel_property_id=hotel_id
        ).all()

        return room_type_schema.dump(room_types, many=True)


class RatePlanByRoomTypeResource(Resource):

    def get(self, room_type_id):
        rate_plans = RatePlan.query.filter_by(
            room_type_id=room_type_id
        ).all()

        return rate_plan_schema.dump(rate_plans, many=True)


class InventoryByRangeResource(Resource):

    def get(self):

        room_type_id = request.args.get("room_type_id")
        rate_plan_id = request.args.get("rate_plan_id")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if not all([room_type_id, rate_plan_id, start_date, end_date]):
            return {"error": "Missing parameters"}, 400

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        inventory = (
            InventoryItem.query
            .filter(
                InventoryItem.room_type_id == room_type_id,
                InventoryItem.rate_plan_id == rate_plan_id,
                InventoryItem.date >= start,
                InventoryItem.date < end
            )
            .order_by(InventoryItem.date)
            .all()
        )

        return inventory_items_schema.dump(inventory)


api.add_resource(HotelListResource, '/api-queries/hotels')
api.add_resource(RoomTypeByHotelResource,
                 '/api-queries/hotels/<int:hotel_id>/room-types')
api.add_resource(RatePlanByRoomTypeResource,
                 '/api-queries/room-types/<int:room_type_id>/rate-plans')
api.add_resource(InventoryByRangeResource,
                 '/api-queries/inventory')


if __name__ == '__main__':
    start_heartbeat()
    app.run(debug=True, host='0.0.0.0')
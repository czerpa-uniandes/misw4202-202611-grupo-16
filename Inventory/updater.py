from base import app, db, InventoryItem
from datetime import datetime, timedelta


def process_reservation(room_type_id, rate_plan_id, start_date, end_date):

    try:
        with app.app_context():

            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

            current = start

            while current < end:

                inventory = (
                    InventoryItem.query
                    .with_for_update()
                    .filter_by(
                        room_type_id=room_type_id,
                        rate_plan_id=rate_plan_id,
                        date=current
                    )
                    .first()
                )

                if not inventory or inventory.available_quantity <= 0:
                    db.session.rollback()
                    return

                inventory.available_quantity -= 1
                current += timedelta(days=1)

            db.session.commit()

    except:
        db.session.rollback()
        raise
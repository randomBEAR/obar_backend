from datetime import datetime as dt
from datetime import timedelta as td

from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import InternalServerError

from obar.models import db, Product, Customer, Purchase, PurchaseItem


def purchase_leaderboard():
    per_user_purchase = dict()
    leaderboard = []
    try:
        customers = db.session.query(Customer).all()
    except OperationalError:
        raise InternalServerError('Customer table does not exists')
    for customer in customers:
        per_user_purchase['customer'] = customer.customer_mail_address
        per_user_purchase['first_name'] = customer.customer_first_name
        per_user_purchase['last_name'] = customer.customer_last_name
        per_user_purchase['purchases'] = len(customer.purchase)
        leaderboard.append(per_user_purchase.copy())
    return sorted(leaderboard, key=lambda x: x['purchases'], reverse=True)


def best_selling_product():
    try:
        products = db.session.query(Product).all()
    except OperationalError:
        raise InternalServerError('Product table does not exists')
    result = sorted(
        [{
            'product_code_uuid': product.product_code_uuid,
            'product_name': product.product_name,
            'product_availability': product.product_availability,
            'product_quantity': product.product_quantity,
            'product_price': product.product_price,
            'product_discount': product.product_discount,
            'product_location_id': product.product_location_id,
            'purchases': len(product.purchaseItem)}
            for product in products if len(product.purchaseItem) is not 0]
        , key=lambda x: x['purchases'], reverse=True)
    return result, 200


def produce_expenses():
    result = []
    try:
        customers = db.session.query(Customer).all()
    except OperationalError:
        raise InternalServerError('Customer table does not exists')
    for customer in customers:
        total_expense = 0
        purchases = []
        for purchase in customer.purchase:
            single_expense = 0
            for item in purchase.purchase_item:
                single_expense += item.purchase_item_price
                total_expense += item.purchase_item_price
            purchases.append(
                {
                    'date': purchase.purchase_date,
                    'code': purchase.purchase_code_uuid,
                    'cost': single_expense
                })
        customer_review = {
            'customer': customer.customer_mail_address,
            'total_expenses': total_expense,
            'purchases': purchases}
        result.append(customer_review)
    return result, 200


def produce_purchase_list(mail_address):
    try:
        customer = db.session.query(Customer).filter_by(customer_mail_address=mail_address).first()
    except OperationalError:
        raise InternalServerError('Customer table does not exists')
    per_user_purchase = []
    for purchase in customer.purchase:
        purchase_details = dict()
        purchase_details['date'] = purchase.purchase_date
        item_list = []
        for item in purchase.purchase_item:
            item_list.append(item)
        purchase_details['items'] = item_list
        per_user_purchase.append(purchase_details)
    return per_user_purchase, 200


def recent_purchases():
    """
    Shows the most recent purchases within X minutes
    """
    result = db.session.query(Purchase, Product, PurchaseItem)\
        .filter(Purchase.purchase_date > dt.utcnow() - td(minutes=10)) \
        .filter(PurchaseItem.purchase_item_product_code_uuid == Product.product_code_uuid) \
        .filter(PurchaseItem.purchase_item_purchase_code_uuid == Purchase.purchase_code_uuid) \
        .all()
    recent_purchases_details = dict()
    for entry in result:
        recent_product = {
                    "product": entry[1].product_name,
                    "quantity": entry[2].purchase_item_quantity,
                    "price": entry[2].purchase_item_price
                }
        if entry[0].purchase_code_uuid not in recent_purchases_details.keys():
            recent_purchases_details[entry[0].purchase_code_uuid] = [recent_product]
        else:
            recent_purchases_details[entry[0].purchase_code_uuid].append(recent_product)
    return recent_purchases_details


def gift_purchase(purchase_uuid, customer_mail_address):
    """
    Replace the customer mail address of a purchase with a new one
    """
    result = db.session.query(Purchase) \
        .filter(Purchase.purchase_date > dt.utcnow() - td(minutes=10)) \
        .filter(Purchase.purchase_code_uuid == purchase_uuid) \
        .first()
    result.purchase_customer_mail_address = customer_mail_address
    db.session.commit()

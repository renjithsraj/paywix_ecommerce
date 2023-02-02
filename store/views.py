from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime

from .models import *
from .utils import cookieCart, cartData, guestOrder
from django.conf import  settings
from paywix.payu import Payu
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

merchant_key = settings.MERCHANT_KEY
merchant_salt = settings.MERCHANT_SALT
payu = Payu(merchant_key, merchant_salt, "Test")

def store(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    products = Product.objects.all()
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)


def cart(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/cart.html', context)


def checkout(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    import uuid
    lowercase_str = uuid.uuid4().hex
    transaction_id = f"{order.id}_{lowercase_str}"
    order.transaction_id = transaction_id
    order.save()
    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/checkout.html', context)

def payment_processing(request):

    if request.method != 'POST':
        return HttpResponseForbidden()
    data = cartData(request)
    order = data['order']

    response_url = settings.RESPONSE_URL
    payload = {
        "amount": f"{str(order.get_cart_total)}",
        "firstname": request.POST.get("fname"),
        "email": request.POST.get("email"),
        "phone": request.POST.get("phone"),
        "lastname": request.POST.get('lname'),
        "productinfo": f"{order.transaction_id}",
        "txnid": f"{order.transaction_id}",
        "furl": response_url,
        "surl": response_url
    }
    data = payu.transaction(**payload)
    print(data)
    html = payu.make_html(data)
    print(html)
    return HttpResponse(html)

@csrf_exempt
def payment_response_handler(request):
    data = {k: v[0] for k, v in dict(request.POST).items()}
    response = payu.check_transaction(**data)
    breakpoint()
    payu.refund()
    payment_response = response.get('payment_response')
    transaction_id = payment_response.get('transaction_id')
    order = Order.objects.get(transaction_id=transaction_id)
    order.pg_id = payment_response.get('mihpayid')
    order.complete = True
    order.pg_source = payment_response.get('payment_source')
    order.pg_response = response
    order.txn_stts = payment_response.get('status')
    order.transaction_msg = payment_response.get('transaction_msg')
    order.save()

    return render(request, 'store/transaction.html', {'order': order})

def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    print('Action:', action)
    print('Product:', productId)

    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)

    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        orderItem.quantity = (orderItem.quantity + 1)
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)

    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    return JsonResponse('Item was added', safe=False)

def api_test(request):
    # Verify Payment
    # verify_payment_data = {
    #     'transaction_id': ['20_95e00e4941c94ac5a124989b8c5a9dba']
    # }
    # verify_payment_resp = payu.verify_payment(**verify_payment_data)

    #Check Payment
    # check_payment_data = {
    #     'payment_id': "403993715528207372"
    # }
    # check_payment_resp  = payu.check_payment(**check_payment_data)

    # get_wsonline_response
    # get_wsonline_data = {
    #     'transaction_id': '20_95e00e4941c94ac5a124989b8c5a9dba'
    # }
    # get_wsonline_resp = payu.verify_payment(**get_wsonline_data)

    #get_Transaction_Details
    # get_transction_details_payload = {
    #     'date_from': "2023-01-29",
    #     'date_to': "2023-01-30"
    # }
    # transaction_resp = payu.get_transaction_details(**get_transction_details_payload)
    #

    #get_transaction_info
    # get_transaction_info_payload = {
    #     'date_time_from': "2023-01-29 16:00:00",
    #     'date_time_to': "2023-01-29 18:00:00"
    # }
    # get_transaction_info = payu.get_transaction_info(**get_transaction_info_payload)
    #

    #Get Transaction Discount Rate (TDR) Details
    # get_tdr_data = {
    #     'payment_id': "403993715528207372"
    # }
    # get_tdr_resp = payu.get_tdr(**get_tdr_data)
    # {'status': 1, 'msg': 'Transaction Fetched Successfully', 'TDR_details': {'TDR': 25.35}}


    #Refund
    # payload = {
    #     'payment_id': "403993715528207372",
    #     "refund_id": "12334qwe45",
    #     "amount": "100.0"
    # }
    # refund_resp = payu.refund(**payload)
    # {'status': 1, 'msg': 'Refund Request Queued', 'request_id': '135018119', 'bank_ref_num': None,
    #  'mihpayid': 403993715528207372, 'error_code': 102}

    # payload = {
    #     "refund_id": "12334qwe45"
    # }
    # refund_status = payu.refund_status(**payload)
    # {'status': 0, 'msg': '0 out of 1 Transactions Fetched Successfully',
    #  'transaction_details': {'12334qwe45': 'No action status found'}}
    breakpoint()














def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
    else:
        customer, order = guestOrder(request, data)

    total = float(data['form']['total'])
    order.transaction_id = transaction_id

    if total == order.get_cart_total:
        order.complete = True
    order.save()

    if order.shipping == True:
        ShippingAddress.objects.create(
            customer=customer,
            order=order,
            address=data['shipping']['address'],
            city=data['shipping']['city'],
            state=data['shipping']['state'],
            zipcode=data['shipping']['zipcode'],
        )

    return JsonResponse('Payment submitted..', safe=False)


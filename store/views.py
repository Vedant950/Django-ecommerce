from django.shortcuts import render, get_object_or_404, redirect
from .forms import UserRegisterForm, CheckoutForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from .models import *
from .filters import ProductFilter
from django.views.decorators.csrf import csrf_exempt
from . import Checksum
from django.http import HttpResponseRedirect
MERCHANT_KEY = 'g_RV1h#RJyLt#hsp'


class ProfileView(DetailView):
    model = Profile
    template_name = 'profile.html'


class HomeView(ListView):
    context_object_name = 'items'
    template_name = "index.html"
    queryset = Items.objects.filter(featured=True)

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['banners'] = Banner.objects.all()
        context['profile'] = Profile.objects.all()
        return context


class Product(ListView):
    model = Items
    paginate_by = 6
    template_name = 'products.html'
    ordering = ["-id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        filter = ProductFilter(self.request.GET, queryset)
        return filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProductFilter(self.request.GET, queryset)
        context["filter"] = filter
        return context


class ProductDetails(DetailView):
    model = Items
    template_name = 'product-details.html' 
    


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Cart.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'order': order,
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_address': shipping_address_qs[0]})
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect(reverse('store:cart-page'))

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST)
        try:
            order = Cart.objects.get(user=self.request.user, ordered=False)
            amount = order.get_total()
            if form.is_valid():
                use_default = form.cleaned_data.get(
                    'use_default')
                if use_default:
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('store:checkout-page')
                else:
                    address = form.cleaned_data.get(
                        'address')
                    pincode = form.cleaned_data.get('zip')
                    phone = form.cleaned_data.get('phone')
                    city = form.cleaned_data.get('city')
                    state = form.cleaned_data.get('state')
                    if form.is_valid():
                        shipping_address = Address(
                            user=self.request.user,
                            address=address,
                            pincode=pincode,
                            state=state,
                            city=city,
                            phone=phone
                        )
                        shipping_address.save()
                        order.shipping_address = shipping_address
                        order.save()

                        set_default = form.cleaned_data.get(
                            'set_default')
                        if set_default:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")
                    param_dict = {
                        'MID': 'RCTaMb66211132431836',
                        'ORDER_ID': str(order.cart_id),
                        'TXN_AMOUNT': str(amount),
                        'CUST_ID': self.request.user.email,
                        'INDUSTRY_TYPE_ID': 'Retail',
                        'WEBSITE': 'WEBSTAGING',
                        'CHANNEL_ID': 'WEB',
                        'CALLBACK_URL': 'http://127.0.0.1:8000/handlerequest/'
                    }
                    param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)
                    return render(self.request, 'payment.html', {'param_dict': param_dict})
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect(reverse('store:cart-page'))


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect(reverse('store:home-page'))
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})


class CartFunc(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Cart.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'cart.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return render(self.request, 'cart.html')


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Items, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        product=item,
        user=request.user,
        ordered=False
    )
    order_qs = Cart.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(product__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect(reverse('store:cart-page'))
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect(reverse('store:cart-page'))
    else:
        ordered_date = timezone.now()
        order = Cart.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect(reverse('store:cart-page'))


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Items, slug=slug)
    order_qs = Cart.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(product__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                product=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect(reverse('store:cart-page'))
        else:  # change
            messages.info(request, "This item was not in your cart")
            return redirect(reverse('store:cart-page'))
    else:
        messages.info(request, "You do not have an active order")
        return redirect(reverse('store:cart-page'))


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Items, slug=slug)
    order_qs = Cart.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(product__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                product=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect(reverse('store:cart-page'))
        else:
            messages.info(request, "This item was not in your cart")
            return redirect(reverse('store:cart-page'))
    else:
        messages.info(request, "You do not have an active order")
        return redirect(reverse('store:cart-page'))


@login_required
def wishlist(request):
    products = Items.objects.filter(wishlist=request.user)
    return render(request, "wishlist.html", {"wishlist": products})


@login_required
def add_to_wishlist(request, id):
    product = get_object_or_404(Items, id=id)
    if product.wishlist.filter(id=request.user.id).exists():
        product.wishlist.remove(request.user)
        messages.success(request, product.title + " has been removed from your WishList")
    else:
        product.wishlist.add(request.user)
        messages.success(request, "Added " + product.title + " to your wishList")
    return HttpResponseRedirect(request.META["HTTP_REFERER"])


def order_history(request):
    orders = Cart.objects.filter(user=request.user, ordered=True).order_by('-id')
    return render(request, 'order_history.html', {'orders' : orders})


def about_us(request):
    return render(request, 'about-us.html')


def contact_us(request):
    return render(request, 'contact.html')


def terms(request):
    return render(request, 'terms.html')

@csrf_exempt
def handlerequest(request):
    # paytm will send you post request here
    form = request.POST
    response_dict = {}
    for i in form.keys():
        response_dict[i] = form[i]
        if i == 'CHECKSUMHASH':
            checksum = form[i]
    verify = Checksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)
    if verify:
        if response_dict['RESPCODE'] == '01':
            print('Order has been placed successfully!')
        else:
            print('Order was not successful because' + response_dict['RESPMSG'])
    return render(request, 'paymentstatus.html', {'response': response_dict})

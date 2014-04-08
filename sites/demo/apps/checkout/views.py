from django.contrib import messages
from django import http
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from datacash.facade import Facade as DatacashFacade
# TODO invoice, cash and paypal facades import
# from invoice.facade import Facade as InvoiceFacade
# from cash.facade import Facade as CashFacade

from oscar.apps.checkout import views, exceptions 
from oscar.apps.payment.forms import BankcardForm
from oscar.apps.payment.models import SourceType
from oscar.apps.order.models import BillingAddress

from .forms import BillingAddressForm

from apps.checkout.forms import PaymentMethodForm

# Customised core PaymentMethodsView displays 4 ways to pay 
# COD, Paypal, payment backend or bank invoice


# Customise the core PaymentDetailsView to integrate multiple payment methods
class PaymentDetailsView(views.PaymentDetailsView):

    def check_payment_data_is_captured(self, request):
        if request.method != "POST":
            raise exceptions.FailedPreCondition(
                url=reverse('checkout:payment-details'),
                message=_("Please enter your payment details"))

    def get_context_data(self, **kwargs):
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        # Ensure newly instantiated instances of the bankcard and billing
        # address forms are passed to the template context (when they aren't
        # already specified).
        if 'bankcard_form' not in kwargs:
            ctx['bankcard_form'] = BankcardForm()
        if 'billing_address_form' not in kwargs:
            ctx['billing_address_form'] = self.get_billing_address_form(
                ctx['shipping_address']
            )
        elif kwargs['billing_address_form'].is_valid():
            # On the preview view, we extract the billing address into the
            # template context so we can show it to the customer.
            ctx['billing_address'] = kwargs[
                'billing_address_form'].save(commit=False)
        return ctx

    def get_billing_address_form(self, shipping_address):
        """
        Return an instantiated billing address form
        """
        addr = self.get_default_billing_address()
        if not addr:
            return BillingAddressForm(shipping_address=shipping_address)
        billing_addr = BillingAddress()
        addr.populate_alternative_model(billing_addr)
        return BillingAddressForm(shipping_address=shipping_address,
                                  instance=billing_addr)

    def handle_payment_details_submission(self, request):
        # Validate the submitted forms
        bankcard_form = BankcardForm(request.POST)
        shipping_address = self.get_shipping_address(
            self.request.basket)
        address_form = BillingAddressForm(shipping_address, request.POST)

        if address_form.is_valid() and bankcard_form.is_valid():
            # If both forms are valid, we render the preview view with the
            # forms hidden within the page. This seems odd but means we don't
            # have to store sensitive details on the server.
            return self.render_preview(
                request, bankcard_form=bankcard_form,
                billing_address_form=address_form)

        # Forms are invalid - show them to the customer along with the
        # validation errors.
        return self.render_payment_details(
            request, bankcard_form=bankcard_form,
            billing_address_form=address_form)

    def handle_place_order_submission(self, request):
        bankcard_form = BankcardForm(request.POST)
        shipping_address = self.get_shipping_address(
            self.request.basket)
        address_form = BillingAddressForm(shipping_address, request.POST)
        if address_form.is_valid() and bankcard_form.is_valid():
            # Forms still valid, let's submit an order
            submission = self.build_submission(
                order_kwargs={
                    'billing_address': address_form.save(commit=False),
                },
                payment_kwargs={
                    'bankcard_form': bankcard_form,
                    'billing_address_form': address_form
                }
            )
            return self.submit(**submission)

        # Must be DOM tampering as these forms were valid and were rendered in
        # a hidden element.  Hence, we don't need to be that friendly with our
        # error message.
        messages.error(request, _("Invalid submission"))
        return http.HttpResponseRedirect(
            reverse('checkout:payment-details'))

    def get(self, request, *args, **kwargs):
        error_response = self.get_error_response()
        payment_method = self.checkout_session.payment_method()
        self.preview = False
        
        if error_response:
            return error_response
        # Check for payment method selected and redirect to preview 
        # except bankcard and paypal
        if payment_method == 'paypal':
            return http.HttpResponseRedirect(reverse('paypal-redirect'))
        elif payment_method == 'bankcard':
            # Render bankcard form
            return super(PaymentDetailsView, self).get(request, *args, **kwargs)
        self.preview = True
        return self.render_preview(request, payment_method=payment_method)
        
    
    def post(self, request, *args, **kwargs):
        if request.POST.get('action', '') == 'place_order':
            return self.do_place_order(request)

        # Check bankcard form is valid
        bankcard_form = BankcardForm(request.POST)
        payment_method = self.checkout_session.payment_method()
        
        if not bankcard_form.is_valid():
            # Bancard form invalid, re-render the payment details template
            self.preview = False
            ctx = self.get_context_data(**kwargs)
            ctx['bankcard_form'] = bankcard_form
            return self.render_to_response(ctx)

        # Render preview page (with completed bankcard form hidden).
        # Note, we don't write the bankcard details to the session or DB
        # as a security precaution.
        return self.render_preview(request, bankcard_form=bankcard_form, 
                                   payment_method=payment_method)

    def do_place_order(self, request):
        kwargs = {}
        payment_method = self.checkout_session.payment_method()
        #kwargs['payment_method'] = payment_method
        if payment_method == 'bankcard':
            # Double-check the bankcard data is still valid
            bankcard_form = BankcardForm(request.POST)
            if not bankcard_form.is_valid():
                # Must be tampering - we don't need to be that friendly with our
                # error message.
                messages.error(request, _("Invalid submission"))
                return http.HttpResponseRedirect(
                    reverse('checkout:payment-details'))
            kwargs['bankcard_form']=bankcard_form
        submission = self.build_submission(**kwargs)
        return self.submit(**submission)

    def build_submission(self, **kwargs):
        submission = super(PaymentDetailsView, self).build_submission()
        # Add payment method to default submission
        
        #submission['payment_kwargs']['payment_method'] = kwargs['payment_method']
        # Modify the default submission dict with the bankcard instance
        if 'bankcard_form' in kwargs:
            bankcard_form = kwargs['bankcard_form']
            if bankcard_form.is_valid():
                submission['payment_kwargs']['bankcard'] = bankcard_form.bankcard
        return submission

    def handle_payment(self, order_number, total, **kwargs):
        payment_ref = 'no-ref'
        payment_event = 'no-payment'
        payment_method = self.checkout_session.payment_method()
        # Make request to DataCash - if there any problems (eg bankcard
        # not valid / request refused by bank) then an exception would be
        # raised and handled by the parent PaymentDetail view)
        if payment_method == 'bankcard':
            facade = DatacashFacade()
            payment_ref = facade.pre_authorise(
            order_number, total.incl_tax, kwargs['bankcard'])
            payment_event = 'pre-auth-datacash'
        elif payment_method == 'paypal':
            # TODO facade = PaypalFacade
            payment_event = 'pre-auth-paypal'
        elif payment_method == 'invoice':
            # TODO facade = InvoiceFacade
            payment_event = 'pre-invoice'
        elif payment_method == 'cash':
            # TODO facade = CashFacade
            payment_event = 'pre-cash'
        # Request was successful - record the "payment source".  As this
        # request was a 'pre-auth', we set the 'amount_allocated' - if we had
        # performed an 'auth' request, then we would set 'amount_debited'.
        source_type, _ = SourceType.objects.get_or_create(name=payment_method)
        source = source_type.sources.model(
            source_type=source_type,
            currency=total.currency,
            amount_allocated=total.incl_tax,
            reference=payment_ref)
        self.add_payment_source(source)

        # Also record payment event
        self.add_payment_event(payment_event, total.incl_tax, reference=payment_ref)
        
    def get_error_response(self):
        # Check that the user's basket is not empty
        if self.request.basket.is_empty:
            messages.error(self.request, _("You need to add some items to your basket to checkout"))
            return http.HttpResponseRedirect(reverse('basket:summary'))
        if self.request.basket.is_shipping_required():
            shipping_address = self.get_shipping_address(
                self.request.basket)
            shipping_method = self.get_shipping_method(
                self.request.basket, shipping_address)
            # Check that shipping address has been completed
            if not shipping_address:
                messages.error(self.request, _("Please choose a shipping address"))
                return http.HttpResponseRedirect(
                    reverse('checkout:shipping-address'))
            # Check that shipping method has been set
            if not shipping_method:
                messages.error(self.request, _("Please choose a shipping method"))
                return http.HttpResponseRedirect(
                    reverse('checkout:shipping-method'))
            # Check that payment method has been set
            payment_method = self.checkout_session.payment_method()
            if not payment_method:
                messages.error(self.request, _("Please choose a payment method"))
                return http.HttpResponseRedirect(
                    reverse('checkout:payment-method'))    

class PaymentMethodView(views.PaymentMethodView):
    """
    View for a user to choose which payment method(s) they want to use.

    This would include setting allocations if payment is to be split
    between multiple sources.
    """
    template_name = 'checkout/payment_methods.html'
    
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            payment_form = PaymentMethodForm(request.POST)
            if not payment_form.is_valid(): 
                messages.error(request, _("Strange situation. How does it "
                                          "possible to choose wrong value "
                                          "with radio button?"))
                self.get_errord_response(**kwargs)
            else:
                payment_method = request.POST.get('options', 'payment_method_not_set')
                if payment_method == 'payment_method_not_set':
                    messages.error(request, _("More strange situation. "
                                              "Do you really try to hack me?"
                                              " How does it possible to get empty 'options' value?"))
                    self.get_error_response(**kwargs)
                messages.info(request, _("Payment method '%(method)s' selected" % { 'method' : payment_method }) )
                self.checkout_session.pay_by(payment_method)
                return self.get_success_response() 
    
    def get(self, request, *args, **kwargs):
        # Check that the user's basket is not empty
        if request.basket.is_empty:
            messages.error(request, _("You need to add some items to your "
                                      "basket to checkout"))
            return http.HttpResponseRedirect(reverse('basket:summary'))

        shipping_required = request.basket.is_shipping_required()

        # Check that shipping address has been completed
        if shipping_required and not self.checkout_session.is_shipping_address_set():
            messages.error(request, _("Please choose a shipping address"))
            return http.HttpResponseRedirect(reverse('checkout:shipping-address'))

        # Check that shipping method has been set
        if shipping_required and not self.checkout_session.is_shipping_method_set(self.request.basket):
            messages.error(request, _("Please choose a shipping method"))
            return http.HttpResponseRedirect(reverse('checkout:shipping-method'))
        
        
        #return self.get_success_response()
        #return super(PaymentMethodView, self).get(request, *args, **kwargs)
        return self.render_to_response(self.get_context_data(**kwargs))    

    def get_context_data(self, **kwargs):
        
        #Add payment method  form to the template context
        if 'payment_form' not in kwargs:
            kwargs['payment_form'] = PaymentMethodForm()
        ctx = super(PaymentMethodView, self).get_context_data(**kwargs)    
        return ctx
    
    def get_success_response(self):
        return http.HttpResponseRedirect(reverse('checkout:payment-details'))
    
    def get_error_response(self, **kwargs):
        return self.render_to_response(self.get_context_data(**kwargs))
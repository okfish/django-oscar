from django import forms
#from django.db.models import get_model
from django.utils.translation import ugettext_lazy as _

class PaymentMethodForm(forms.Form):
    CASH, BANKCARD, INVOICE, PAYPAL = 'cash', 'bankcard', 'invoice', 'paypal'
    CHOICES = (
        (CASH, _('Pay by cash on delivery')),
        (BANKCARD, _('I have Visa or Mastercard!')),
        (INVOICE, _('Send me bank invoice')),
        (PAYPAL, _('Paypal is my choice')))
    options = forms.ChoiceField(widget=forms.widgets.RadioSelect,
                                choices=CHOICES, initial=CASH)
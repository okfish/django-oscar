from django.test import TestCase
from oscar.apps.customer.forms import ProfileForm
from oscar.core import compat


class TestCustomUserModel(TestCase):

    def setUp(self):
        self.user_klass = compat.get_user_model()

    def test_can_be_created_without_error(self):
        try:
            self.user_klass.objects.create_user('_', 'a@a.com', 'pa55w0rd')
        except Exception, e:
            self.fail("Unable to create user model: %s" % e)

    def test_extra_field_is_picked_up(self):
        self.assertTrue('extra_field' in compat.VALID_USER_FORM_FIELD_NAMES)
        self.assertTrue(hasattr(self.user_klass(), 'extra_field'))

    def test_profile_form_doesnt_expose_extra_field(self):
        form = ProfileForm(self.user_klass())
        expected_fields = set(['first_name', 'last_name', 'email'])
        self.assertTrue(expected_fields == set(form.fields))


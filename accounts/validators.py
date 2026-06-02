import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class UppercaseNumberValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _('Password must contain at least 1 uppercase letter.'),
                code='password_no_upper',
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _('Password must contain at least 1 number.'),
                code='password_no_number',
            )

    def get_help_text(self):
        return _('Password must contain at least 1 uppercase letter and 1 number.')

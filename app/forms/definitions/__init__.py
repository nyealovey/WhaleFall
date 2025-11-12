"""资源表单定义集合。"""

from .base import FieldComponent, FieldOption, ResourceFormDefinition, ResourceFormField
from .instance import INSTANCE_FORM_DEFINITION
from .credential import CREDENTIAL_FORM_DEFINITION
from .tag import TAG_FORM_DEFINITION
from .account_classification import CLASSIFICATION_FORM_DEFINITION
from .account_classification_rule import CLASSIFICATION_RULE_FORM_DEFINITION
from .user import USER_FORM_DEFINITION

__all__ = [
    "FieldComponent",
    "FieldOption",
    "ResourceFormDefinition",
    "ResourceFormField",
    "INSTANCE_FORM_DEFINITION",
    "CREDENTIAL_FORM_DEFINITION",
    "TAG_FORM_DEFINITION",
    "CLASSIFICATION_FORM_DEFINITION",
    "CLASSIFICATION_RULE_FORM_DEFINITION",
    "USER_FORM_DEFINITION",
]

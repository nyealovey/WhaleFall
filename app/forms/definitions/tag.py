"""标签表单定义."""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.forms.handlers.tag_form_handler import TagFormHandler

TAG_FORM_DEFINITION = ResourceFormDefinition(
    name="tag",
    template="tags/form.html",
    service_class=TagFormHandler,
    success_message="标签保存成功",
    redirect_endpoint="tags.index",
    fields=[
        ResourceFormField(
            name="name",
            label="标签代码",
            required=True,
            help_text="建议使用英文、数字、下划线或短横线组成的唯一代码",
        ),
        ResourceFormField(
            name="display_name",
            label="显示名称",
            required=True,
        ),
        ResourceFormField(
            name="category",
            label="分类",
            component=FieldComponent.SELECT,
            required=True,
        ),
        ResourceFormField(
            name="color",
            label="颜色",
            component=FieldComponent.SELECT,
            required=True,
        ),
        ResourceFormField(
            name="is_active",
            label="激活状态",
            component=FieldComponent.SWITCH,
            default=True,
        ),
    ],
)

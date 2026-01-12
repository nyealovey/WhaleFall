"""定时任务表单定义."""

from app.forms.definitions.base import FieldComponent, FieldOption, ResourceFormDefinition, ResourceFormField

SCHEDULER_JOB_FORM_DEFINITION = ResourceFormDefinition(
    name="scheduler_job",
    template="admin/scheduler/index.html",
    success_message="任务更新成功",
    fields=[
        ResourceFormField(
            name="trigger_type",
            label="触发器类型",
            component=FieldComponent.SELECT,
            required=True,
            default="cron",
            options=[FieldOption(value="cron", label="cron")],
        ),
        ResourceFormField(
            name="cron_expression",
            label="Cron 表达式",
            component=FieldComponent.TEXT,
        ),
        ResourceFormField(
            name="cron_second",
            label="秒",
            component=FieldComponent.TEXT,
        ),
        ResourceFormField(
            name="cron_minute",
            label="分",
            component=FieldComponent.TEXT,
        ),
        ResourceFormField(
            name="cron_hour",
            label="时",
            component=FieldComponent.TEXT,
        ),
        ResourceFormField(
            name="cron_day",
            label="日",
            component=FieldComponent.TEXT,
        ),
        ResourceFormField(
            name="cron_month",
            label="月",
            component=FieldComponent.TEXT,
        ),
        ResourceFormField(
            name="cron_weekday",
            label="周",
            component=FieldComponent.TEXT,
        ),
        ResourceFormField(
            name="year",
            label="年",
            component=FieldComponent.TEXT,
        ),
    ],
    extra_config={
        "only_builtin": True,
    },
)

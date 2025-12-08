"""定时任务表单定义."""

from app.forms.definitions.base import FieldComponent, ResourceFormDefinition, ResourceFormField
from app.services.form_service.scheduler_job_service import SchedulerJobFormService

SCHEDULER_JOB_FORM_DEFINITION = ResourceFormDefinition(
    name="scheduler_job",
    template="admin/scheduler/index.html",
    service_class=SchedulerJobFormService,
    success_message="任务更新成功",
    fields=[
        ResourceFormField(
            name="trigger_type",
            label="触发器类型",
            component=FieldComponent.SELECT,
            required=True,
            default="cron",
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
        ResourceFormField(
            name="minutes",
            label="间隔分钟",
            component=FieldComponent.NUMBER,
        ),
        ResourceFormField(
            name="seconds",
            label="间隔秒数",
            component=FieldComponent.NUMBER,
        ),
        ResourceFormField(
            name="run_date",
            label="运行时间",
            component=FieldComponent.TEXT,
            help_text="日期触发器使用，格式为 YYYY-MM-DD HH:MM",
        ),
    ],
    extra_config={
        "only_builtin": True,
    },
)

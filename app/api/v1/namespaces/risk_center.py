"""Risk Center namespace."""

from __future__ import annotations

from typing import ClassVar

from flask_restx import Namespace

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required
from app.api.v1.resources.query_parsers import new_parser
from app.core.constants.system_constants import SuccessMessages
from app.services.risk_center.risk_center_read_service import RiskCenterReadService

ns = Namespace("risk-center", description="风险中心")

ErrorEnvelope = get_error_envelope_model(ns)
RiskCenterSummarySuccessEnvelope = make_success_envelope_model(ns, "RiskCenterSummarySuccessEnvelope", None)
RiskCenterCardsSuccessEnvelope = make_success_envelope_model(ns, "RiskCenterCardsSuccessEnvelope", None)

_cards_query_parser = new_parser()
_cards_query_parser.add_argument("severity", type=str, default="", location="args")
_cards_query_parser.add_argument("db_type", type=str, default="", location="args")
_cards_query_parser.add_argument("status", type=str, default="", location="args")
_cards_query_parser.add_argument("tag", type=str, default="", location="args")
_cards_query_parser.add_argument("search", type=str, default="", location="args")
_cards_query_parser.add_argument("page", type=int, default=1, location="args")
_cards_query_parser.add_argument("limit", type=int, default=0, location="args")


@ns.route("/summary")
class RiskCenterSummaryResource(BaseResource):
    """风险中心汇总资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", RiskCenterSummarySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取风险中心汇总."""

        def _execute():
            return self.success(
                data=RiskCenterReadService().build_summary(),
                message=SuccessMessages.OPERATION_SUCCESS,
            )

        return self.safe_call(
            _execute,
            module="risk_center",
            action="get_risk_center_summary",
            public_error="获取风险中心汇总失败",
        )


@ns.route("/cards")
class RiskCenterCardsResource(BaseResource):
    """风险中心卡片资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", RiskCenterCardsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_cards_query_parser)
    def get(self):
        """获取实例风险卡片."""

        def _execute():
            args = _cards_query_parser.parse_args()
            data = RiskCenterReadService().list_cards(
                severity=str(args.get("severity") or "").strip(),
                db_type=str(args.get("db_type") or "").strip(),
                status=str(args.get("status") or "").strip(),
                tag=str(args.get("tag") or "").strip(),
                search=str(args.get("search") or "").strip(),
                page=int(args.get("page") or 1),
                limit=int(args.get("limit") or 0),
            )
            return self.success(data=data, message=SuccessMessages.OPERATION_SUCCESS)

        return self.safe_call(
            _execute,
            module="risk_center",
            action="list_risk_center_cards",
            public_error="获取风险中心卡片失败",
        )

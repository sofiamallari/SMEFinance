"""Action permissions bounded by business roles, independent of administration."""
from copilot.security import AccessDenied

ROLE_ALIASES={'SYSTEM_ADMIN':'security_admin','SME_OWNER':'owner','SME_STAFF':'staff','BANK':'lender_analyst',
              'owner':'owner','staff':'staff','lender_analyst':'lender_analyst','security_admin':'security_admin'}
AUTHORITATIVE_ROLES={'security_admin':'SYSTEM_ADMIN','owner':'SME_OWNER','staff':'SME_STAFF','lender_analyst':'BANK'}
ROLE_LABELS={'security_admin':'System Admin','owner':'SME Owner','staff':'SME Staff','lender_analyst':'Bank'}
def resolve_role(role):return ROLE_ALIASES.get(role,role)
OPERATIONAL={'view_transactions','create_transactions','bulk_import','view_dashboard','view_forecasts','simulate_payments','use_copilot','view_quality_monitoring'}
FINANCIAL={'view_reports','view_assessment','view_financing','view_financing_data','prepare_application','submit_application','view_applications'}
STAFF_ACTIONS=OPERATIONAL|{'view_reports','view_assessment','view_financing','view_applications','create_financing_draft','edit_financing_draft','acknowledge_quality_alerts','resolve_quality_alerts'}
POLICY={
 'SYSTEM_ADMIN':{'manage_users','manage_staff_accounts','view_account_audit','manage_security','view_security_audit'},
 'SME_OWNER':OPERATIONAL|FINANCIAL|{'manage_transactions','manage_consents','request_staff_access','manage_merchant_staff','view_merchant_audit','create_financing_draft','edit_financing_draft','acknowledge_quality_alerts','resolve_quality_alerts'},
 'SME_STAFF':STAFF_ACTIONS,
 'BANK':{'view_reports','view_assessment','view_forecasts','view_financing','view_financing_data','view_applications','use_copilot','view_bank_review','export_bank_review','view_bank_audit'},
}
BOUNDARIES={alias:POLICY[canonical] for alias,canonical in AUTHORITATIVE_ROLES.items()}
DEFAULTS={role:set(actions) for role,actions in BOUNDARIES.items()}
TOOL_ACTIONS = {
    'financing_journey':'view_financing',
    'data_quality':'view_quality_monitoring','latest_payment':'simulate_payments','application_status':'view_applications',
    'get_dashboard':'view_dashboard','financial_report':'view_reports','assess_business':'view_assessment',
    'cashflow_forecast':'view_forecasts','cashflow_alerts':'view_forecasts','incentive_status':'view_dashboard',
    'match_financing':'view_financing','rbf_quote':'view_financing','mdr_compare':'simulate_payments',
    'payment_create':'simulate_payments','payment_simulate_pay':'simulate_payments','payment_status':'simulate_payments',
    'prepare_financing_application':'submit_application',
}
CATEGORIES = {'view_reports':'reports','view_assessment':'assessment','view_forecasts':'forecasts',
              'view_financing':'financing','view_financing_data':'financing','view_bank_review':None,'export_bank_review':None,'view_bank_audit':None,
              'view_applications':'applications','view_dashboard':'reports'}

def require(principal, action, merchant=None):
    # Non-authenticated Principals retain compatibility for trusted internal/demo tests.
    # All authenticated HTTP/MCP entry points create Principals with a live resolver.
    if principal.role not in BOUNDARIES:raise AccessDenied('Role is not mapped to the four-role policy')
    if principal.authenticated:
        if not principal.authorizer:
            raise AccessDenied('Authenticated principal has no authorization resolver')
        return principal.authorizer(action, merchant)
    if principal.role=='staff' and action not in principal.permissions:
        raise AccessDenied('Explicit delegated permission required for Staff')


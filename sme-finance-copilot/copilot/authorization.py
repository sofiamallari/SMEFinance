"""Action permissions bounded by business roles, independent of administration."""
from copilot.security import AccessDenied

ROLE_LABELS = {'owner':'Business Owner','staff':'Staff','lender_analyst':'Financing Agent',
               'coach':'Progression Coach','user_admin':'User Administrator','security_admin':'Security Administrator'}
OPERATIONAL = {'view_transactions','create_transactions','bulk_import','view_dashboard',
               'view_forecasts','simulate_payments','use_copilot','view_quality_monitoring'}
FINANCIAL = {'view_reports','view_assessment','view_financing','view_financing_data',
             'prepare_application','submit_application','view_applications'}
BOUNDARIES = {
    'owner': OPERATIONAL | FINANCIAL | {'manage_transactions','manage_consents','request_staff_access','acknowledge_quality_alerts','resolve_quality_alerts'},
    'staff': OPERATIONAL | {'acknowledge_quality_alerts','resolve_quality_alerts'},
    'lender_analyst': {'view_reports','view_assessment','view_forecasts','view_financing',
                       'view_financing_data','view_applications','review_application','use_copilot'},
    'coach': {'view_dashboard','view_reports','view_assessment','view_forecasts','view_financing','use_copilot'},
    'user_admin': {'manage_users','manage_staff_accounts','view_account_audit'},
    'security_admin': {'manage_users','manage_staff_accounts','view_account_audit','manage_security','view_security_audit'},
}
DEFAULTS = {role: set(actions) for role, actions in BOUNDARIES.items()}
TOOL_ACTIONS = {
    'get_dashboard':'view_dashboard','financial_report':'view_reports','assess_business':'view_assessment',
    'cashflow_forecast':'view_forecasts','cashflow_alerts':'view_forecasts','incentive_status':'view_dashboard',
    'match_financing':'view_financing','rbf_quote':'view_financing','mdr_compare':'simulate_payments',
    'payment_create':'simulate_payments','payment_simulate_pay':'simulate_payments','payment_status':'simulate_payments',
    'prepare_financing_application':'submit_application',
}
CATEGORIES = {'view_reports':'reports','view_assessment':'assessment','view_forecasts':'forecasts',
              'view_financing':'financing','view_financing_data':'financing','review_application':'applications',
              'view_applications':'applications','view_dashboard':'reports'}

def require(principal, action, merchant=None):
    # Non-authenticated Principals retain compatibility for trusted internal/demo tests.
    # All authenticated HTTP/MCP entry points create Principals with a live resolver.
    if principal.authenticated:
        if not principal.authorizer:
            raise AccessDenied('Authenticated principal has no authorization resolver')
        return principal.authorizer(action, merchant)


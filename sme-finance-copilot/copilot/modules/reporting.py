"""Deterministic aggregate reports available to both rule and AI agents."""
from datetime import timedelta
from copilot.modules import dashboard, cashflow

def report(merchant, as_of):
    d = dashboard.build_dashboard(merchant, as_of)
    recent = dashboard.filter_period(merchant.transactions, as_of-timedelta(days=29), as_of)
    return {'merchant_id':merchant.merchant_id,'currency':merchant.currency,'period':d['period'], 'revenue':d['mix']['gross_revenue'],
            'expenses':d['expenses'], 'net_income':d['net_income'],
            'revenue_projection_30_days':round(sum(t['amount'] for t in recent),2),
            'projection_assumption':'Recent 30-day sales repeat; no seasonality adjustment or guarantee',
            'risk_alerts':cashflow.alerts(merchant,as_of)}

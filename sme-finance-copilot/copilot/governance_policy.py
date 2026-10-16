"""Fixed-path AI upper-bound policy. Never grants application authority."""
import copy
import json
from pathlib import Path
from copilot.security import AccessDenied

ROOT = Path(__file__).resolve().parents[1] / 'config'
ROLES = {'SME_OWNER', 'SME_STAFF', 'BANK', 'SYSTEM_ADMIN'}
CAPABILITIES = {'financial_education','sales_summary_read','transaction_trends_read','payment_channel_mix_read','cash_flow_read','business_highlights_read','financing_status_read','financing_details_read','survival_simulation_run','expansion_assessment','public_research','financial_execution'}
TOOL_CAPABILITIES = dict(get_financial_summary='sales_summary_read',get_transaction_trends='transaction_trends_read',get_payment_channel_mix='payment_channel_mix_read',get_cash_flow='cash_flow_read',get_business_highlights='business_highlights_read',get_financing_status='financing_status_read',get_financing_details='financing_details_read',run_survival_simulation='survival_simulation_run',search_public_financial_information='public_research')
FIELD_CLASSES = {
 'get_financial_summary':dict(period='D1',currency='D1',recorded_net_sales='D2',transaction_count='D1',source_timestamp='D1'),
 'get_transaction_trends':dict(period='D1',granularity='D1',transaction_count='D1',recorded_net_sales='D2',source_timestamp='D1'),
 'get_payment_channel_mix':dict(period='D1',channel='D1',transaction_count='D1',share_percent='D1'),
 'get_cash_flow':dict(period='D2',currency='D2',cash_inflows='D2',cash_outflows='D2',net_cash_flow='D2',available_cash_if_verified='D2'),
 'get_business_highlights':dict(period='D1',highlight_type='D1',summary='D2',source_metric='D2'),
 'get_financing_status':dict(application_reference='D3',status='D3',status_as_of='D3'),
 'get_financing_details':dict(application_reference='D3',requested_amount='D3',approved_amount='D3',repayment_terms='D3',decision='D3',decision_as_of='D3'),
 'run_survival_simulation':dict(scenario='D1',assumptions='D1',baseline_period='D1',simulation_results='D2',limitations='D1'),
 'search_public_financial_information':dict(source_title='D0',source_url='D0',publication_date='D0',retrieved_at='D0',excerpt='D0'),
}


class Policy:
    def __init__(self):
        self._data = None
        self.version = 'unavailable'
        try:
            schema = json.loads((ROOT / 'ai_governance_policy.schema.json').read_text(encoding='utf-8-sig'))
            data = json.loads((ROOT / 'ai_governance_policy.json').read_text(encoding='utf-8-sig'))
            self.validate(data, schema)
            self._data = data
            self.version = data['metadata']['version']
        except Exception:
            # Fail closed if files, dependency, schema or semantic invariants fail.
            pass

    @staticmethod
    def validate(data, schema):
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
        if data['metadata']['version'] != '0.5.0' or data['metadata']['schema_version'] != '1.0.0':
            raise ValueError('Unreviewed policy version')
        if set(data['roles']) != ROLES or set(data['capabilities']) != CAPABILITIES or set(data['tools']) != set(TOOL_CAPABILITIES):
            raise ValueError('Unknown role, capability or tool')
        if data['metadata']['default_effect'] != 'deny' or data['authorization_policy']['default_effect'] != 'deny':
            raise ValueError('Default deny required')
        for name, capability in data['capabilities'].items():
            if set(capability['role_effects']) != ROLES or set(capability['role_effects'].values()) - {'allow','conditional','deny'}:
                raise ValueError('Unknown role or effect')
        if set(data['capabilities']['financial_execution']['role_effects'].values()) != {'deny'}:
            raise ValueError('Financial execution must remain prohibited')
        for name, tool in data['tools'].items():
            if tool['capability'] != TOOL_CAPABILITIES[name] or not tool['read_only'] or not tool['server_authorization_required']:
                raise ValueError('Unsafe tool mapping')
            if tool['timeout_seconds']>10 or tool['result_max_records']>100:
                raise ValueError('Tool resource limits exceed reviewed bounds')
            fields = tool['output_field_allowlist']
            if 'D4' in tool['allowed_data_classes'] or set(fields) - set(FIELD_CLASSES[name]):
                raise ValueError('Unclassified or security-sensitive fields')
            ceiling = data['capabilities'][tool['capability']]['data_classification_ceiling']
            if any(int(level[1]) > int(ceiling[1]) for level in tool['allowed_data_classes']):
                raise ValueError('Tool exceeds capability ceiling')
            if name == 'search_public_financial_information' and tool['approval'] != 'exact_query_single_use':
                raise ValueError('Research approval required')
            if name != 'search_public_financial_information' and tool['approval'] != 'none':
                raise ValueError('Unsupported approval configuration')
        # All boolean safeguards must retain their approved meaning, not only shape.
        required_true = {
          'authorization_policy':['server_derived_identity','server_derived_merchant_scope','authorize_each_tool_call','filter_before_model','deny_if_policy_missing_or_invalid','deny_on_unknown_role_or_tool','deny_indirect_disclosure','invalidate_context_on_role_or_merchant_change','conditional_requires_explicit_permission','do_not_treat_data_classification_as_permission'],
          'conversation_policy':['clear_on_refresh','clear_on_logout','clear_on_session_expiry','clear_on_merchant_switch','clear_on_new_conversation','revalidate_permissions_per_tool_call'],
          'web_research_policy':['ask_before_every_search','show_exact_query_terms','show_purpose','reject_query_changes','reject_approval_replay','require_source_citations','treat_results_as_untrusted'],
          'simulation_policy':['require_explicit_user_request','clarify_material_assumptions','use_existing_deterministic_calculations','non_persistent','use_only_authorized_inputs','label_assumptions_and_uncertainty','disclose_unsupported_scenarios','compare_base_and_downside_for_material_decisions'],
          'financial_response_policy':['distinguish_verified_data_from_assumptions','do_not_confuse_revenue_with_profit','do_not_treat_transaction_volume_as_cash','do_not_guarantee_loan_approval','do_not_fabricate_financial_figures','do_not_invent_citations','disclose_data_gaps'],
          'security_controls':['tool_allowlist_enforced','least_privilege','field_level_filtering','prompt_injection_content_untrusted','no_secrets_in_llm_context','no_private_data_in_public_search','provider_retention_requires_review'],
        }
        for section, keys in required_true.items():
            if any(data[section][key] is not True for key in keys):
                raise ValueError('Required safeguard disabled')
        for section, keys in {'conversation_policy':['persist_transcripts','persist_in_browser_storage','log_full_transcripts'],'web_research_policy':['enabled_by_default','private_merchant_data_in_queries','allow_unapproved_retry'],'simulation_policy':['modify_financial_records'],'execution_policy':['financial_write_tools_registered','conversational_consent_is_transaction_approval'],'security_controls':['audit_full_prompt_or_response','audit_secrets']}.items():
            if any(data[section][key] is not False for key in keys):
                raise ValueError('Unsafe policy setting')
        if set(data['web_research_policy']['bind_approval_to']) != {'user','merchant','session','query_digest','tool'} or data['web_research_policy']['max_queries_per_approval'] != 1:
            raise ValueError('Approval binding unsafe')
        if data['conversation_policy']['mode'] != 'session_only' or data['conversation_policy']['storage'] != 'ephemeral_memory':
            raise ValueError('Conversation persistence prohibited')
        if not 1 <= data['conversation_policy']['max_messages'] <= 30 or not 1 <= data['conversation_policy']['session_idle_timeout_minutes'] <= 30:
            raise ValueError('Conversation bounds unsafe')

    @property
    def available(self):
        return self._data is not None

    def section(self, name):
        if not self.available:
            raise AccessDenied('Governed AI is unavailable because its policy is missing or invalid')
        return copy.deepcopy(self._data[name])

    def capability(self, principal, capability):
        from copilot.authorization import AUTHORITATIVE_ROLES
        if not principal.authenticated or not principal.authorizer:
            raise AccessDenied('Authenticated application identity required')
        item = self.section('capabilities').get(capability)
        role = AUTHORITATIVE_ROLES.get(principal.role)
        effect = item['role_effects'].get(role, 'deny') if item else 'deny'
        if effect == 'deny':
            raise AccessDenied('This AI capability is restricted for your account')
        if effect == 'conditional':
            # These granular permissions do not currently exist. Do not translate
            # broad role/Staff grants into invented finance.* permissions.
            required = item.get('required_application_permission')
            if not required or required not in principal.permissions:
                raise AccessDenied('An explicit granular application permission is required')
        return item

    def tool(self, principal, name):
        item = self.section('tools').get(name)
        if not item:
            raise AccessDenied('Unknown governed AI tool')
        self.capability(principal, item['capability'])
        return item

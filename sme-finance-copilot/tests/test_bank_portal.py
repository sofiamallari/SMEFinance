"""Focused read metadata and Bank portal authorization regression tests."""
import unittest
from tests import test_four_role_workflow as existing
from copilot.security import AccessDenied
from copilot.auth import AuthError

class BankPortalMetadata(unittest.TestCase):
    setUp=existing.FourRoleWorkflow.setUp
    consent=existing.FourRoleWorkflow.consent
    submit=existing.FourRoleWorkflow.submit
    def test_authorized_directory_requires_bank_and_current_owner_grant(self):
        token=self.tokens['lender_analyst']
        self.assertEqual(self.w.merchants(token),[])
        cid=self.consent(['reports'])
        rows=self.w.merchants(token)
        self.assertEqual([x['id'] for x in rows],['M002'])
        self.assertEqual(rows[0]['authorizations'][0]['categories'],['reports'])
        self.assertNotIn('owner_id',rows[0]['authorizations'][0])
        self.assertIsNone(rows[0]['last_review_at'])
        self.w.review(token,'M002')
        self.assertIsNotNone(self.w.merchants(token)[0]['last_review_at'])
        for role in ('owner','staff','security_admin'):
            with self.assertRaises(AccessDenied):self.w.merchants(self.tokens[role])
        self.auth.revoke_consent(self.tokens['owner'],cid['consent_id'])
        self.assertEqual(self.w.merchants(token),[])

    def test_directory_excludes_expired_foreign_and_inactive_owner_grants(self):
        self.consent()
        with self.auth.db() as db:db.execute('UPDATE consents SET expires_at=?',(self.auth.clock()-1,))
        self.assertEqual(self.w.merchants(self.tokens['lender_analyst']),[])
        self.consent()
        with self.auth.db() as db:db.execute("UPDATE users SET account_status='inactive' WHERE user_id=?",(self.ids['owner'],))
        self.assertEqual(self.w.merchants(self.tokens['lender_analyst']),[])

    def test_submitted_date_is_stored_timestamp_and_packet_is_routed(self):
        packet=self.submit()
        result=self.w.review(self.tokens['lender_analyst'],'M002',packet['application_id'])['application']
        with self.auth.db() as db:stamp=db.execute('SELECT created_at FROM applications WHERE application_id=?',(packet['application_id'],)).fetchone()[0]
        self.assertEqual(result['submitted_at'],stamp)

    def test_inactive_bank_cannot_read_directory(self):
        self.consent()
        with self.auth.db() as db:db.execute("UPDATE users SET account_status='inactive' WHERE user_id=?",(self.ids['lender_analyst'],))
        with self.assertRaises((AccessDenied,AuthError)):self.w.merchants(self.tokens['lender_analyst'])

    def test_directory_withholds_review_history_without_audit_permission(self):
        self.consent(['reports']);token=self.tokens['lender_analyst']
        self.w.review(token,'M002')
        with self.auth.db() as db:db.execute("DELETE FROM role_permissions WHERE role='lender_analyst' AND permission='view_bank_audit'")
        self.assertIsNone(self.w.merchants(token)[0]['last_review_at'])
        self.assertIn('recorded_metrics',self.w.review(token,'M002')['sections'])
        with self.assertRaises(AccessDenied):self.w.audit(token,'M002')

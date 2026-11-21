import unittest
from services.social_ai.policy import Principal, authorize, preview_plan

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.person = Principal("utimoshi", "analyst")

    def test_read_only_preview(self):
        draft = preview_plan(self.person, "utimoshi", "Мороженое")
        self.assertEqual(draft["status"], "DRAFT_ONLY")
        self.assertFalse(draft["external_action"])
        self.assertTrue(draft["requires_approval"])

    def test_cross_tenant_denied(self):
        with self.assertRaises(PermissionError):
            authorize(self.person, "social.health", "practicai")

    def test_write_action_denied(self):
        with self.assertRaises(PermissionError):
            authorize(self.person, "vk.posts.publish", "utimoshi")

    def test_unprivileged_role_denied(self):
        with self.assertRaises(PermissionError):
            authorize(Principal("utimoshi", "viewer"), "social.health", "utimoshi")

    def test_invalid_topic_rejected(self):
        with self.assertRaises(ValueError):
            preview_plan(self.person, "utimoshi", "")

if __name__ == "__main__":
    unittest.main()

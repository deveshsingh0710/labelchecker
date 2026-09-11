import unittest
import uuid
from database import (
    SessionLocal,
    Organization,
    User,
    DemoRequest,
    Verification,
    hash_password,
    DEMO_ORG_BRAND_ID,
    DEMO_ORG_GOVT_ID,
)


class TestBusinessModels(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_demo_organizations_seeded(self):
        brand_org = self.db.query(Organization).filter(Organization.id == DEMO_ORG_BRAND_ID).first()
        govt_org = self.db.query(Organization).filter(Organization.id == DEMO_ORG_GOVT_ID).first()
        self.assertIsNotNone(brand_org)
        self.assertIsNotNone(govt_org)
        self.assertEqual(brand_org.type, "brand")
        self.assertEqual(govt_org.type, "government")

    def test_organization_and_user_creation(self):
        org_id = str(uuid.uuid4())
        org = Organization(id=org_id, name="Test FMCG Brand", type="brand")
        self.db.add(org)
        self.db.flush()

        user = User(
            id=str(uuid.uuid4()),
            email=f"test_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password("secretpass"),
            name="Test User",
            organization_id=org_id,
            role="admin",
        )
        self.db.add(user)
        self.db.commit()

        queried_user = self.db.query(User).filter(User.organization_id == org_id).first()
        self.assertIsNotNone(queried_user)
        self.assertEqual(queried_user.organization.name, "Test FMCG Brand")

    def test_demo_request_creation(self):
        demo = DemoRequest(
            id=str(uuid.uuid4()),
            name="Rohan Mehra",
            email="rohan@marketplace.in",
            organization_name="Marketplace Co",
            organization_type="marketplace",
            message="Looking for automated seller label screening",
            status="pending",
        )
        self.db.add(demo)
        self.db.commit()

        queried = self.db.query(DemoRequest).filter(DemoRequest.id == demo.id).first()
        self.assertIsNotNone(queried)
        self.assertEqual(queried.organization_name, "Marketplace Co")
        self.assertEqual(queried.status, "pending")

    def test_verification_scoping(self):
        verif = self.db.query(Verification).first()
        self.assertIsNotNone(verif)
        # Verify that organization_id is set
        self.assertIsNotNone(verif.organization_id)
        as_dict = verif.to_dict()
        self.assertIn("organization_id", as_dict)


if __name__ == "__main__":
    unittest.main()
